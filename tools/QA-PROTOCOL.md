# Protocolo de QA de Zepo — "probar al crear y al modificar"

> Nació de una sesión (2026-06-04) donde 3 bugs graves se colaron por probar con datos
> falsos o cubriendo solo UNA variante. Regla de oro: **un cambio no está "listo" hasta
> que `python tools/qa-all.py` está en verde Y existe una prueba que ejerce la variante
> que tocaste — incluido el camino inverso.**

## 1. Cuándo probar (no negociable)

- **Al CREAR una función/pantalla:** escribe un E2E que ejerza **cada botón y cada variable**
  de esa pantalla, en sus combinaciones reales.
- **Al MODIFICAR / corregir:** vuelve a probar **toda la pantalla**, no solo la línea tocada.
  "Arreglé X" sin re-probar los botones vecinos = cómo se rompió "Debo" justo después de
  arreglar "Me deben".
- **Antes de commit y antes de promover a producción:** `python tools/qa-all.py` verde.

## 2. La regla del CAMINO INVERSO (la que más fallba)

Por cada acción, prueba su opuesto y sus cardinalidades:

| Acción | Variantes obligatorias a probar |
|--------|--------------------------------|
| Crear  | crear **y borrar** (el dato desaparece de TODAS las pantallas) |
| Activar split | activar **y quitar** la división (desaparece de Me deben/Debo) |
| Agregar persona | agregar **y quitar** persona; con **1** y con **N** (≥2) personas |
| Editar | editar gasto **y** ingreso; normal **y** dividido; single **y** batch |
| Importar/foto | 1 ítem **y** varios; con fecha **y** sin fecha |

> Un split con **2+ personas** y el camino de **quitar** algo son los que más rompen.

## 3. Verificar en TODAS las pantallas afectadas

Un registro tocado debe quedar coherente en: **Home, Historial, Cuentas>Me deben,
Cuentas>Debo, Dashboard, Presupuestos**. Verifica **backend** (lo que se guardó en
Supabase) **y frontend** (lo que se ve y los totales/contadores), no solo uno.

## 4. Principios visuales/técnicos ya descubiertos (revisar siempre)

- **Teclado/overflow:** la pantalla no debe comprimir/recortar con `--vvh` (teclado) ni con
  un panel expandido. → `qa-keyboard.py`. (No se puede abrir teclado headless; se simula --vvh.)
- **Keys de `x-for`:** listas DERIVADAS por-persona (una fila por nombre del mismo gasto)
  DEBEN llavear por `id + '|' + persona`, NUNCA solo por `id` → keys duplicadas hacen que
  Alpine descarte filas (parpadeo). → `qa-cuentas-flicker.py`.
- **Recálculo tras guardar:** `saveExpense` debe `loadSplits()` **siempre** (también al quitar
  split) y limpiar `editingExpense`. El "freno" `_busyEditing` debe soltarse al cerrar
  (depende de `sheetOpen`, no de `editingExpense`). → `qa-e2e-edit-split.py`, `qa-e2e-remove-split.py`.
- **Datos REALES, no falsos:** los E2E inician sesión real (cuenta demo) y golpean Supabase
  real. Probar con objetos JSON inventados NO ejerce guardar→recargar→recalcular y por eso
  los bugs pasaban.
- **Control negativo:** toda prueba nueva debe FALLAR si se reintroduce el bug (verificarlo
  una vez). Si no falla nunca, es una prueba hueca.

## 5. Cómo correr / extender

```
python tools/qa-all.py          # gate completo (sintaxis, marca, layout, E2E)
python tools/qa-e2e-edit-split.py     # editar cobro + agregar persona
python tools/qa-e2e-remove-split.py   # editar 'Debo' quitando la division
python tools/qa-cuentas-flicker.py    # keys duplicadas / parpadeo
python tools/qa-keyboard.py           # layout con teclado simulado
```

**Para agregar un caso:** copia el E2E más parecido, cámbiale el flujo (los pasos se hacen
llamando a los métodos reales del componente Alpine: `c.openEdit`, `c.saveExpense`,
`c.deleteExpense`…), agrega el assert de las pantallas afectadas, **limpia el dato sembrado**
al final, y súmalo a la lista `CHECKS` de `qa-all.py`.

Cuenta demo: `demo@zepo.test` / `ZepoDemo2026!` (recrear con `secret_key` admin si falla;
las llaves legacy están deshabilitadas).
