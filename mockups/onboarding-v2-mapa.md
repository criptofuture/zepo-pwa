# Zepo · Onboarding v2 — Mapa de contenido

> **Estado:** propuesta para aprobar (Fase 0.5). Cuando Alvaro apruebe este mapa, actualizo el mockup visual y luego construyo.
> **Decisiones ya tomadas:** objetivo = activación + sentirse premium · rehacer desde cero · **modelo contextual (just-in-time)** · primer gasto = básico + momento "aprende" · técnica híbrida (Alpine puro + driver.js solo para los recorridos contextuales).
> **Base real:** tu app ya tiene el patrón (`showCoachPhoto`, flag `zepo_coach_photo_v1`, componente `.coach-overlay`). Lo convertimos en sistema reutilizable.

---

## Modelo de 3 capas

| Capa | Qué es | Cuándo |
|------|--------|--------|
| **A · Onboarding inicial** | Cuestionario + primer gasto guiado básico. Corto (60-90s). | Una vez, al registrarse |
| **B · Coach contextual** | Una burbuja la **1ª vez** que tocas cada función. | Repartido, en contexto |
| **C · Checklist de inicio** | Lista en home que empuja a descubrir funciones. | Primeros días |

Las tres se conectan: la **checklist (C)** manda al usuario a una función → al llegar, la **burbuja contextual (B)** la explica.

---

## CAPA A — Onboarding inicial (una vez, lineal)

| # | Pantalla | Copy (título / apoyo) | Notas |
|---|----------|----------------------|-------|
| A1 | Bienvenida | **"Bienvenido a Zepo"** / "Tu dinero, claro y bajo control. Lo configuramos en menos de un minuto." | Logo + botón "Empezar" |
| A2 | Nombre | **"¿Cómo te llamas?"** / "Para que Zepo te hable de tú a tú." | Guarda `nombre` |
| A3 | Moneda | **"¿Tu moneda?"** / "Verás tus montos en la divisa correcta." | Guarda `moneda` |
| A4 | **¿Para qué?** | **"¿Para qué usarás Zepo?"** / "Adaptamos la app a tu objetivo." | Personalización ↓ |
| A5 | Presupuesto | **"¿Tu presupuesto mensual?"** / "Te avisamos antes de pasarte. Puedes cambiarlo luego." | Guarda budget total |
| A6 | Armando | **"Armando tu Zepo…"** / checklist animada (moneda ✓, objetivo ✓, presupuesto ✓) | Micro-pausa "premium" |
| A7 | **Primer gasto** | (ver abajo) | Activación real |

### A4 · "¿Para qué?" — cómo personaliza (sutil, no invasivo)

| Elección | Qué cambia |
|----------|------------|
| 🎯 Controlar mis gastos | Default. Home enfocado en presupuesto vs gastado. |
| 🐷 Ahorrar para una meta | La checklist sugiere fijar una meta de ahorro; resalta "cuánto te queda". |
| 🏠 Gastos de pareja o casa | La checklist sugiere **crear un Espacio compartido** (gated Max → ver decisiones). |
| 💼 Mi negocio | La checklist sugiere un **Espacio "Negocio"** para separar lo personal. |

### A7 · Primer gasto guiado (BÁSICO + momento "aprende")

Secuencia sobre el **sheet de gasto REAL** (no una maqueta):

| Paso | Acción del usuario | Burbuja / feedback |
|------|--------------------|--------------------|
| 1 | Spotlight sobre el botón ➕ | "Registremos tu primer gasto 👆" |
| 2 | Se abre el sheet, foco en el texto | "Escribe natural y dale **Enter ↵**: *almuerzo 12.50*" |
| 3 | Escribe + Enter → la app saca monto y categoría | "✨ Zepo entendió el monto y la categoría solos" |
| 4 | (opcional) cambia la categoría | **Momento aprende:** "Si la ajustas, Zepo la **recordará** la próxima vez 🧠" |
| 5 | Guardar | "🎉 ¡Tu primer gasto! Ya estás usando Zepo." (su gasto REAL queda guardado) |

> Lo que NO se enseña aquí (va a Capa B contextual): dividir, método de pago, multi-ítem, voz, foto, recurrentes.

---

## CAPA B — Coach contextual (just-in-time)

Cada fila = **una burbuja, una vez**, con su flag en localStorage. Respeta el plan.

| # | Función | Se dispara cuando… | Resalta | Copy (título / texto) | Flag | Plan |
|---|---------|--------------------|---------|----------------------|------|------|
| B1 | Texto + Enter | (ya en A7) refuerzo si entra al sheet sin pasar por A7 | Campo de texto | "Escribe natural: *café 3 · taxi 8* y Enter ↵" | `coach_text` | Free |
| B2 | Categoría aprende 🧠 | Cambia una categoría por 1ª vez | Grid de categorías | "Listo. Zepo recordará este producto la próxima vez." | `coach_learn` | Free |
| B3 | Varios a la vez | Escribe algo con `·` o coma | Resultado multi-ítem | "Anotaste varias compras de una. Cada una con su categoría." | `coach_multi` | Free |
| B4 | Ingreso vs gasto | Toca el toggle ingreso por 1ª vez | Toggle gasto/ingreso | "También registras lo que entra, no solo lo que gastas." | `coach_income` | Free |
| B5 | Editar/borrar | Abre el detalle de un gasto por 1ª vez | Acciones del detalle | "Toca cualquier gasto para editarlo o borrarlo." | `coach_edit` | Free |
| B6 | Resumen del mes | 1ª visita al home con ≥1 gasto | Hero de balance | "Tu disponible, lo gastado y los días que quedan." | `coach_home` | Free |
| B7 | Método de pago | Abre el selector de método por 1ª vez | Selector método | "Marca con qué pagaste: efectivo, tarjeta, transferencia." | `coach_paym` | Pro |
| B8 | Dividir gasto | Toca "Dividir" por 1ª vez (con acceso) | Toggle dividir | "Reparte un gasto y lleva quién te debe." | `coach_split` | Pro |
| B9 | Voz | Usa el micrófono por 1ª vez | Botón voz | "Dicta tu gasto: *cinco de pollo y un taxi de ocho*." | `coach_voice` | Pro |
| B10 | Foto / OCR | (ya existe: `coach_photo`) | Botón cámara | "Toma foto del recibo y Zepo lo lee por ti." | `coach_photo` | Elite |
| B11 | Recurrentes | Marca "Repetir cada mes" por 1ª vez | Toggle repetir | "Se creará solo cada mes. Lo gestionas en Ajustes." | `coach_recur` | Elite |
| B12 | Presupuesto | 1ª visita a la pestaña Presupuesto | Pantalla presupuesto | "Pon topes por mes o por categoría y te avisamos." | `coach_budget` | Pro/Elite |
| B13 | Espacios | 1ª vez que abre el switcher de espacios | Chip de espacio | "Separa tus gastos: Personal, Negocio, Casa…" | `coach_spaces` | Max |

### Versión **teaser de upgrade** (cuando NO tiene el plan) — DECIDIDO

Las burbujas de pago (B7-B13) **sí aparecen** a quien no tiene el plan, pero con copy que vende y un botón **"Ver planes →"** (el "Más tarde" cierra). Se disparan cuando el usuario **intenta** usar la función (toca el botón gated). Cada teaser se ve una vez (mismo flag) para no fastidiar.

| # | Función | Copy teaser (sin el plan) | CTA |
|---|---------|---------------------------|-----|
| B7 | Método de pago | "Lleva con qué pagas cada gasto (efectivo, tarjeta…). Disponible en **Pro**." | Ver planes → |
| B8 | Dividir gasto | "Reparte un gasto y lleva quién te debe. Disponible en **Pro**." | Ver planes → |
| B9 | Voz | "Registra hablando: *cinco de pollo y un taxi*. Disponible en **Pro**." | Ver planes → |
| B10 | Foto / OCR | "Toma foto del recibo y Zepo lo lee solo. Disponible en **Elite**." | Ver planes → |
| B11 | Recurrentes | "Tus gastos fijos se crean solos cada mes. Disponible en **Elite**." | Ver planes → |
| B12 | Presupuesto categoría | "Pon topes por categoría, no solo el total. Disponible en **Elite**." | Ver planes → |
| B13 | Espacios | "Separa Personal / Negocio / Casa en cuentas aparte. Disponible en **Max**." | Ver planes → |

> Con acceso → copy normal (tabla de arriba). Sin acceso → copy teaser (esta tabla). Mismo disparador, contenido que se bifurca por plan.

---

## CAPA C — Checklist de inicio

Vive en el home, descartable, con barra de progreso. Cada ítem lleva a una función; al llegar salta su coach (Capa B).

| Ítem | Estado inicial | Lleva a | Se marca al… |
|------|----------------|---------|--------------|
| Registra tu primer gasto | ✓ (hecho en A7) | — | completar A7 |
| Crea un presupuesto | ☐ | Pestaña presupuesto (→ B12) | crear 1 presupuesto |
| Prueba registrar varios juntos | ☐ | Sheet de gasto (→ B3) | guardar un multi-ítem |
| *(según objetivo A4)* crea un Espacio | ☐ | Switcher de espacios (→ B13) | crear 1 espacio |
| **Divide un gasto con alguien** (Pro) ⭐ | ☐ | Dividir (→ B8, teaser si es free) | hacer 1 split | soft upsell |

- Desaparece sola al completar todo **o** si el usuario la descarta (✕).
- Los ítems se adaptan al objetivo elegido en A4 (ej.: "pareja/casa" prioriza el de Espacio).

---

## Reglas del sistema de coach (transversales)

1. **Una burbuja a la vez.** Nunca dos en pantalla.
2. **Siempre descartable** ("Entendido" / "Más tarde" / tocar fuera).
3. **Flag por función** (`zepo_coach_<x>_v1`) → cada una se ve **una sola vez**.
4. **Plan-aware con teaser.** Si tiene acceso → explica cómo usar. Si no → teaser de upgrade con "Ver planes →". Mismo flag (una vez).
5. **No molestar:** límite de 1 burbuja contextual por sesión los primeros días (evita avalancha).
6. **"Reiniciar tutorial" en Ajustes** (ya existe a medias) → borra todos los flags y reactiva el onboarding.
7. **Técnica:** B1-B6 (simples, sobre 1 elemento) con Alpine puro reusando `.coach-overlay`; recorridos de varios pasos (A7) con **driver.js**.

---

## Decisiones tomadas (2026-06-09)

1. **Funciones de pago en el coach:** ✅ **Teaser de upgrade** — aparecen a free con copy que vende + "Ver planes →" (ver tabla teaser).
2. **Checklist y upsell:** ✅ **Incluye 1 ítem de pago** (soft upsell): "Divide un gasto con alguien (Pro)".
3. **Dónde guardar el cuestionario:** ✅ **Supabase** — tabla nueva (p.ej. `onboarding_profile`: user_id, nombre, objetivo, moneda, presupuesto) con **RLS + GRANT** (regla del proyecto). Sirve para personalizar entre dispositivos.
4. **Tono:** ✅ **Cercano con emojis** (como en este doc).
5. **¿Falta/sobra alguna función en Capa B?** ⏳ pendiente de tu revisión de la tabla B.

> **Implicación de construcción (Supabase):** se crea `onboarding_profile` con `ENABLE ROW LEVEL SECURITY` + policies `auth.uid() = user_id` + `GRANT SELECT,INSERT,UPDATE ON public.onboarding_profile TO authenticated` + `REVOKE ALL ... FROM anon`. Pasa por `lint-rls.py`.
