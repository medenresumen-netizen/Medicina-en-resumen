# Rama datos-fda (no es parte del sitio)
Rama aislada para el proyecto «Dosis en resumen». No toca `main` ni el sitio publicado.

- `lista.tsv`: fármacos (id en español → nombre genérico en inglés para openFDA).
- `pedir.tsv` (opcional): `id_es<TAB>set_id` para forzar una ficha concreta.
- `scripts/bajar_fichas.py`: baja las fichas de openFDA (dominio público) a `labels/` y arma `index.json`. Es incremental y respeta el límite de tasa.
- `.github/workflows/fichas-fda.yml`: corre al subir cambios a esta rama (para repetir una corrida basta cambiar `disparo.txt`).

Las fichas son materia prima: cada dato que pase a la app se resume en español, se cita y lo revisa un verificador.
