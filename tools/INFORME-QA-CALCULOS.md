# Zepo · Informe de la campaña de QA de cálculos — 16-jul-2026

**Origen:** una usuaria dividió un ingreso con proporciones propias y "Cuentas" se lo mostró en partes
iguales. Alvaro pidió una campaña que probara *todos* los cálculos y certificara que no hay más de esa
familia. Este es el resultado.

**Método:** 4 agentes en paralelo (2 leyendo código, 2 probando en vivo contra Supabase con cuentas de
prueba aisladas por TAG). **Ningún hallazgo entra aquí sin estar confirmado**: los de código los verifiqué
yo línea por línea; los de comportamiento tienen prueba numérica contra la BD real. Los scripts nuevos
(`qa-e2e-invariantes-dash.py`, `qa-e2e-invariantes-presup.py`) **NO están en el gate todavía**: hoy fallan
a propósito porque documentan estos bugs. Entran al gate junto con cada arreglo aprobado.

**Un falso positivo descartado:** `parseFloat(onboardingFirstAmount) || 12.50` parecía el mismo patrón que
el bug del `|| 50`, pero la variable no tiene `x-model` y nunca cambia de `''` → el fallback nunca se
dispara con un 0 real. No es bug.

**Cobertura:** 2 scripts en vivo con **79/87 checks** (32/37 dashboard + 47/50 presupuestos), cada uno con
sus controles negativos. Las 8 "fallas" son los bugs de abajo.

## Recomendación en una línea

Arreglar ya: **D1, D2, D3, D5, D6 y D15** (baratos y duelen). Elegir umbral en D12. Dejar D13 como está.

---

## YA ARREGLADO Y EN DEV (v180) — no requiere decisión

| # | Bug | Estado |
|---|-----|--------|
| **F1** | **El bug reportado**: las proporciones de un split no se guardaban; Cuentas las recalculaba en partes iguales. En ingresos era el 100% del número mostrado. | Arreglado + E2E (30/30). Los datos viejos se recuperan del cobro emitido. |
| F2 | Editar un split desigual sin tocar la división lo reescribía 50/50 | Arreglado |
| F3 | `parseFloat(split_pct) \|\| 50` convertía un 0% legítimo en 50% al editar, y lo guardaba corrupto | Arreglado |
| F4 | Los splits multi-ítem y de lote creaban los cobros con `(100−pct)/n` igualado | Arreglado |
| F5 | `saveMultiItems` leía `validItems[i]` con ids de `insertedRows[i]`: el anti-duplicados desalinea índices → el cobro salía con la descripción/monto de OTRO ítem | Arreglado |
| F6 | Guardar con las partes en 40/40 pasaba: el 20% se esfumaba (nadie lo pagaba ni se cobraba) | Bloqueado con aviso |

---

## S1 — DINERO INCORRECTO VISIBLE (decisión de Alvaro)

### D1 · "Disponible para gastar" resta el total de un recurrente dividido, no tu parte
- **Dónde:** `pendingRecurringThisMonth` (~10394) suma `Number(t.amount)`, que en `recurring_templates`
  es el TOTAL (`row.amount = data.amount` y `row.split_total = data.amount`, ~12200/12216). No aplica
  `t.split_pct`. El cron de la BD **sí** lo aplica (`v_mypart := t.amount * split_pct/100`) → la app y la
  BD no coinciden.
- **Escenario:** renta compartida $600 al 50%, aún no generada este mes. Ingresos $1000, gastado $200.
  `safeToSpend` muestra **$200** cuando debería mostrar **$500**. Error de $300 en el número grande del Home.
- **Arreglo:** aplicar `split_pct` igual que el cron. ~2 líneas.
- **Confianza:** alta (código verificado).

### D2 · Los exportes se cortan en 1000 filas, en silencio
- **Dónde:** `exportCSV` (~13897), `exportExcel` (~12556) y `exportPDF` (~14146) hacen
  `.select('*').eq('user_id', …)` **sin `.limit()`**. PostgREST corta en 1000 por defecto. El propio código
  ya conoce el problema: `loadLifetimeSavings` lleva `.limit(100000)` (~11947) tras un bug real de truncado.
  A los exportes nunca les llegó ese arreglo.
- **Escenario:** usuario con 1.300 gastos (2 años de uso normal). El CSV/Excel trae solo los 1.000 más
  recientes y **omite 300 sin avisar**. El "Total gastos" del PDF también sale calculado sobre 1.000.
- **Nota mía (misma familia):** `loadSplits` (~13338 y ~13348) tampoco tiene `.limit()` → con más de 1.000
  splits, "Me deben" quedaría incompleto.
- **Arreglo:** añadir `.limit(100000)` a los 3 exportes + los 2 de `loadSplits`. 5 líneas.
- **Confianza:** alta.

### D3 · El % al abrir una categoría usa el denominador equivocado
- **Dónde:** `catDrillPct` (~15725) siempre divide por `monthTotal` (gastos del mes), ignore el período y
  el modo activos. El texto dice fijo "% del gasto del mes" (~7402).
- **Prueba en vivo:** categoría "salary", período semana, modo ingresos → `catDrillTotal=100.50`.
  Debería decir **100%** (100.50/100.50). Dice **164%** (100.50 dividido por los $61.34 de gastos del mes).
- **Arreglo:** dividir por el total del período/modo activos y ajustar el texto.
- **Confianza:** alta (confirmado con números).

### D4 · El Dashboard en "Año" muestra un número y su mapa de calor muestra otro
- **Dónde:** `periodTotal` (~10495) lee `this.expenses`, que `loadExpenses` (~10219) solo carga de
  mes-anterior a mes-siguiente. `yearlyChart` (~15623) mezcla `[...this.expenses, ...this.historyData]`
  y sí ve el año completo.
- **Prueba en vivo:** con un gasto de hace 5 meses → titular **$86.34** vs suma del mapa **$163.34**.
  Diferencia **$77.00** = exactamente ese gasto.
- **Arreglo:** que el titular del período "año" lea la misma fuente que el mapa (o cargar el año).
- **Confianza:** alta (confirmado con números).

### D5 · Modo "Balance": el desglose (y las barras) suman en vez de restar
- **Dónde:** `categoryBreakdown` en modo balance (~15690) suma todas las filas sin signo;
  `dashMonthData` (~10368) devuelve `all` en balance y `monthlyChart` (~15563) hace `b.total += e.amount`
  → ingresos y gastos sumados en positivo. El titular (`dashPeriodData`, ~15667) **sí** resta.
- **Prueba en vivo:** desglose **$161.84** (100.50+61.34) vs titular **$39.16** (100.50−61.34).
- **Escenario:** sueldo $800 y almuerzo $50 el mismo día → arriba $750, la barra del día $850.
- **Arreglo:** netear en modo balance (o quitar el modo balance de esas superficies).
- **Confianza:** alta (confirmado con números).

---

### D15 · Un gasto se "cuela" de un espacio a otro durante 2 minutos
- **Dónde:** el bloque `pendingLocal` de `loadExpenses` (~10270-10275). Existe para no perder un gasto
  recién insertado por lag de réplica: conserva toda fila de `this.expenses` con menos de 120s que la query
  fresca no devuelva. **Pero no comprueba que la fila pertenezca al espacio activo** — y la query fresca no
  la devuelve *precisamente porque* es de otro espacio.
- **Prueba en vivo:** gasto $30 en espacio A → gasto $70 en espacio B → seleccionar A: correcto ($30) →
  seleccionar B: **$100** en vez de $70. Y `Σ(espacios) = 300` vs `vista todos = 100`. Un gasto con
  `space_id=NULL` también aparece en espacios no-default.
- **Alcance:** ventana de 120s tras crear el gasto; afecta Home, `monthTotal` y las barras de presupuesto
  (todo lo que sale de `this.expenses`). El Historial no se ve afectado (usa `historyData`).
- **Arreglo:** exigir pertenencia al espacio en el filtro de `pendingLocal`. 1 condición.
- **Confianza:** alta (confirmado con números; el agente lo reprodujo 3 veces sin borrados de por medio).

---

## S2 — DOS PANTALLAS NO CUADRAN (decisión de Alvaro)

### D6 · "Esta semana" son 8 días arriba y 7 días abajo
- **Dónde:** `periodStart('semana')` = `now − 7 días` (~10488) vs `weeklyChart` = `getDate() − 6` (~15534).
- **Prueba en vivo:** titular **$61.34** vs suma de barras **$28.01** → diferencia **$33.33**, exactamente
  el gasto del día frontera.
- **Arreglo:** una sola definición de semana. 1 línea.
- **Confianza:** alta (confirmado con números).

### D7 · Un split pendiente del mes pasado desaparece del cálculo al cambiar de mes
- **Dónde:** `unsettledAdvances` (~10381) filtra `monthExpenses` (solo mes actual).
- **Escenario:** cena del 28-jun dividida, el amigo no paga. Llega julio: el adelanto de $40 sigue
  `pendiente` en la BD pero deja de contar → `monthBalanceReal` y `safeToSpend` quedan $40 altos y
  desaparece la línea "Balance saldado" del Home.
- **Confianza:** media-alta (código verificado; falta prueba numérica cruzando el mes).

### D8 · Cambiar de espacio no refresca el Historial
- **Dónde:** `refreshForSpace` (~11767) recarga expenses/splits/budgets/recurrentes pero **no** `loadHistory()`.
- **Escenario:** en Historial con "Personal" ($340 en junio) → cambias a "Negocio" → Home ya muestra
  Negocio, pero el Historial sigue mostrando los ítems y el total de Personal.
- **Confianza:** alta (código verificado).

### D9 · El selector de espacios no cuenta los gastos huérfanos que el espacio Personal sí muestra
- **Dónde:** `_applySpaceFilter` (~11682) hace que Personal actúe de catch-all e incluya `space_id IS NULL`,
  pero `loadSpaceStats` (~11754) manda esos gastos a un bucket `'_none'` que nadie lee.
- **Escenario:** $50 en Personal + $30 huérfano → el selector dice "Personal: $50" y al entrar el Home
  dice **$80**.
- **Confianza:** alta (código verificado).

### D10 · El PDF se contradice a sí mismo
- **Dónde:** el total del encabezado usa todas las filas; la tabla de detalle usa `data.slice(0, 500)` (~14190).
- **Escenario:** 600 gastos → encabezado "Total: $4.200", tabla lista solo 500 → sumando lo que se ve nunca
  se llega al total.
- **Confianza:** alta.

---

## S3 — DIVERGENCIAS DE DISEÑO (decisión de producto, no bug)

### D11 · Los exportes ignoran el espacio activo
- `exportCSV`/`exportExcel` no aplican `_applySpaceFilter` → con "Personal" activo, el export trae
  **todos** los espacios mientras el Historial solo muestra Personal. ¿Es lo que quieres (respaldo completo)
  o debería respetar el espacio?

### D12 · Semáforo del presupuesto con dos umbrales distintos
- Pestaña Presupuestos: naranja ≥80%, rojo ≥100% (~5240). Ajustes: naranja ≥70%, rojo ≥90% (~5706).
  Mismo dato, dos colores. Elegir uno.

### D13 · "Patrimonio total" cambia según el espacio activo — **ya lo aceptaste**
- `patNetWorth` es global (los bienes no tienen espacio) pero `lifetimeSavings` sí filtra por espacio →
  el total cambia solo con cambiar de pestaña. **Esto te lo expliqué y lo aceptaste el 1-jul** (está en el
  handoff como "Nota diseño ... aceptable"). Lo traigo con números medidos en vivo por si ahora molesta:
  con los MISMOS bienes, `patNetWorth` = $650.00 en ambos espacios, pero el "Patrimonio total" mide
  **$720.00 en el espacio A** y **$580.00 en el B** ($140 de diferencia, 100% atribuible al ahorro).
  Arreglarlo = hacer el patrimonio por espacio (cambio grande).
- **Aparte, gratis:** el comentario del código (~11919) dice que el ahorro es "global", pero el código
  (~11944) filtra por espacio. Comentario desactualizado que induce a error a quien lo lea.

### D16 · La alerta de presupuesto salta antes del 80% real
- `budgetBars` compara `Math.round(spent/budget*100) >= 80` → redondea ANTES de comparar, así que con un
  presupuesto de $100 la alerta salta desde **$79.50** (medido: $79.49 no, $79.51 sí). El color de la barra
  usa el mismo criterio, así que es coherente consigo mismo; simplemente el "80%" empieza medio dólar antes.
- Decisión: dejarlo (es coherente) o comparar sin redondear.

---

## S4 — RIESGO, NO BUG CONFIRMADO

### D14 · Eliminar un espacio puede fallar a medias
- `removeSpace` (~11806) mueve expenses → budgets → recurrentes → borra el espacio, en cadena `await` sin
  transacción. Si dos espacios tienen presupuesto de la misma categoría/mes y existe una constraint UNIQUE,
  el paso de budgets lanza y **los gastos ya se movieron**: queda un espacio fantasma. Si no hay constraint,
  quedan dos filas de la misma categoría.
- **Confianza:** media — depende de una constraint que no verifiqué en la BD.

---

## Lo que se probó y está CORRECTO

- **Splits en los agregados**: un gasto dividido cuenta tu parte ($18) y no el total ($90) en Home,
  dashboard y desglose por categoría. (Control negativo: el test falla si se espera $90.)
- **Redondeo**: con $33.33 y $0.01 sembrados, ningún total se desvía más de $0.01.
- **Home ↔ Historial**: `monthBalance` == `historyTotal`; el footer == la suma de los grupos diarios.
- **Dashboard mes/gastos**: titular == suma de barras == mapa de calor del mes.
- **Titular en modo balance**: sí resta (el problema está en las barras y el desglose de abajo, D5).
- **Presupuestos**: `spent` (tu parte) y `advance` (adelanto del split) se calculan aparte y **no** se
  suman en el %: no hay doble conteo. La herencia mes a mes respeta el cero explícito.
- **Batches mixtos**: se renderiza el campo neto, con el signo correcto.
- **`monthDelta`**: la ventana de 2 meses le alcanza; funciona incluso en el cruce de año.
- **`ensurePatSnapshot`/`patHistory`**: internamente consistentes.
- **Los 3 exportes** coinciden entre sí en la definición de "monto" (tu parte) cuando no hay truncado.

## Getters muertos (no son bugs hoy, pero son trampas)

- `weekTotal`, `weekExpenseCount`, `topCategory*` filtran sobre `monthExpenses` y tienen el bug que
  `weeklyChart` ya arregló (a principio de mes pierden los días del mes anterior), **pero no están
  conectados a ninguna pantalla** (0 referencias en templates). Si alguien los usa, el bug aparece de
  inmediato.
- Hay **dos pares casi idénticos** de getters de presupuesto total: `budgetTotalAmount`/`budgetTotalPct`
  (~10581/10587, **muertos**, calculan bien) y `totalBudgetObj`/`totalBudgetPct` (~14387/14391, **los que
  la pantalla realmente renderiza**). Quien "arregle" el primero no cambiará nada en pantalla.

Recomendación: borrarlos o arreglarlos ahora, antes de que alguien los conecte.

---

## Infraestructura (no es cálculo, pero muerde)

### D17 · 3 tablas sin GRANT a `service_role` → 403 en silencio
Verificado en la BD viva: `spaces`, `patrimony_items` y `recurring_templates` solo tienen
`REFERENCES/TRIGGER/TRUNCATE` para `service_role` — **sin SELECT/INSERT/UPDATE/DELETE**. `expenses` sí los
tiene. Cualquier script o Edge Function que use la `secret_key` contra esas 3 tablas recibe **403 sin
error visible** si no se mira el status code (así se descubrió: un cleanup de QA falló en silencio y dejó
6 espacios huérfanos). Ojo con la regla del CLAUDE.md ("service_role bypassa"): eso vale para **RLS**, no
para los **GRANT** — desde el default-deny hay que concederlos explícitamente, como ya se hizo en
`zepo_journey`.
