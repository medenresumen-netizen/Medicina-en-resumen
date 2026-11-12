"""Descarga fichas técnicas FDA (openFDA /drug/label) para cada fármaco de lista.tsv.
Incremental: no vuelve a bajar lo que ya está en labels/. Se detiene limpio si openFDA limita la tasa.
pedir.tsv (opcional): id_es<TAB>set_id para forzar una ficha concreta.
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error, datetime

API = "https://api.fda.gov/drug/label.json"
OUT = "labels"
os.makedirs(OUT, exist_ok=True)
SKIP_KEYS = {"spl_product_data_elements", "package_label_principal_display_panel", "spl_unclassified_section",
             "package_label_principal_display_panel_table", "spl_indexing_data_elements"}
calls = 0

class RateLimited(Exception):
    pass

def get(search, limit=100):
    global calls
    q = urllib.parse.urlencode({"search": search, "limit": limit})
    url = f"{API}?{q}"
    key = os.environ.get("OPENFDA_KEY")
    if key:
        url += "&api_key=" + key
    for attempt in range(3):
        calls += 1
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r).get("results", [])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            if e.code == 429:
                raise RateLimited()
            time.sleep(3 * (attempt + 1))
        except Exception:
            time.sleep(3 * (attempt + 1))
        finally:
            time.sleep(0.35)
    return []

def meta(r):
    o = r.get("openfda", {})
    return {"set_id": r.get("set_id"), "id": r.get("id"), "effective_time": r.get("effective_time"),
            "version": r.get("version"), "brand_name": o.get("brand_name", []), "generic_name": o.get("generic_name", []),
            "manufacturer_name": o.get("manufacturer_name", []), "route": o.get("route", []),
            "product_type": o.get("product_type", []), "application_number": o.get("application_number", []),
            "n_sections": len([k for k in r if k not in SKIP_KEYS])}

def is_er(r):
    o = r.get("openfda", {})
    txt = " ".join(r.get("description", []) + r.get("indications_and_usage", [])[:1] + o.get("brand_name", []) + o.get("generic_name", [])).lower()
    return any(k in txt for k in ("extended-release", "extended release", "transdermal", " er ")) or any(b.upper().endswith((" ER", " XR", " LA", "TTS")) for b in o.get("brand_name", []))

def score(r, gen, route="", brand_pref=""):
    ir = route.endswith("-IR")
    route = route[:-3] if ir else route
    o = r.get("openfda", {})
    brand = [b.lower() for b in o.get("brand_name", [])]
    want_brand = bool(brand_pref) and any(brand_pref.lower() in b for b in brand)
    want_route = bool(route) and route in o.get("route", [])
    is_brand = bool(brand) and all(b != gen.lower() for b in brand)
    is_nda = any(a.startswith(("NDA", "BLA")) for a in o.get("application_number", []))
    rx = "HUMAN PRESCRIPTION DRUG" in o.get("product_type", [])
    has_dose = "dosage_and_administration" in r
    return (want_brand, want_route, (not is_er(r)) if ir else True, has_dose, rx, is_nda, is_brand, len(r), r.get("effective_time", ""))

def find(gen, brand=""):
    G = gen.upper()
    if brand:
        res = get(f'openfda.brand_name:"{brand}"')
        if res:
            return f'brand:{brand}', res
    for s in (f'openfda.generic_name.exact:"{G}"', f'openfda.generic_name:"{gen}"', f'openfda.substance_name:"{gen}"'):
        res = get(s)
        if res:
            return s, res
    return None, []

def save(es, gen, search, results, chosen, pref=""):
    data = {"id_es": es, "generic_en": gen, "search": search, "pref": pref,
            "downloaded": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
            "chosen": meta(chosen),
            "candidates": sorted([meta(r) for r in results], key=lambda m: m["effective_time"] or "", reverse=True)[:25],
            "label": {k: v for k, v in chosen.items() if k not in SKIP_KEYS and k != "openfda"}}
    with open(f"{OUT}/{es}.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

def main():
    rows = []
    for l in open("lista.tsv"):
        if l.strip() and not l.startswith("#"):
            c = l.rstrip("\n").split("\t") + ["", ""]
            rows.append((c[0], c[1], c[2], c[3]))
    forced = {}
    if os.path.exists("pedir.tsv"):
        for l in open("pedir.tsv"):
            if l.strip() and not l.startswith("#"):
                es, sid = l.rstrip("\n").split("\t")[:2]
                forced[es] = sid
    done, missing = 0, []
    try:
        for es, gen, route, brand in rows:
            pref = f"{gen}|{route}|{brand}"
            path = f"{OUT}/{es}.json"
            if es in forced:
                if os.path.exists(path) and json.load(open(path))["chosen"]["set_id"] == forced[es]:
                    continue
                res = get(f'set_id:"{forced[es]}"', 1)
                if res:
                    save(es, gen, f"set_id:{forced[es]}", res, res[0]); done += 1
                continue
            if os.path.exists(path) and json.load(open(path)).get("pref", f"{gen}||") == pref:
                continue
            search, res = find(gen, brand)
            if not res:
                missing.append(es); continue
            if brand and search.startswith("brand:"):
                _, more = find(gen)
                seen = {r.get("id") for r in res}
                res = res + [r for r in more if r.get("id") not in seen]
            best = max(res, key=lambda r: score(r, gen, route, brand))
            save(es, gen, search, res, best, pref); done += 1
    except RateLimited:
        print("openFDA limitó la tasa; se guarda lo descargado y se sigue en la próxima corrida.")
    valid = {r[0] for r in rows}
    for fn in os.listdir(OUT):
        if fn[:-5] not in valid:
            os.remove(f"{OUT}/{fn}")
    idx = []
    for fn in sorted(os.listdir(OUT)):
        d = json.load(open(f"{OUT}/{fn}"))
        c = d["chosen"]
        idx.append({"id_es": d["id_es"], "generic_en": d["generic_en"], "brand": c["brand_name"][:1],
                    "manufacturer": c["manufacturer_name"][:1], "effective_time": c["effective_time"],
                    "set_id": c["set_id"], "application": c["application_number"][:1], "n_candidates": len(d["candidates"])})
    json.dump({"updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "n": len(idx), "missing": missing, "labels": idx},
              open("index.json", "w"), ensure_ascii=False, indent=1)
    print(f"nuevos: {done} · total: {len(idx)} · sin resultado: {len(missing)} · llamadas: {calls}")

if __name__ == "__main__":
    main()
