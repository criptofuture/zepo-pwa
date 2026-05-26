# Zepo PWA · Instrucciones para Claude

## Proyecto
Zepo — expense tracker LATAM, mobile-first PWA, single `index.html` con Alpine.js + Supabase.

## Cuando Alvaro diga "pantalla X" o "haz la pantalla de Y"

**Tu flujo automático (sin pedir confirmación):**

1. Lee `design-system/tokens.json` + `design-system/components.md`
2. Si existe `design-system/examples/pages/X.jsx`, léelo como referencia visual
3. Implementa en `index.html` como un nuevo `tab` de Alpine.js
4. Reutiliza componentes existentes en lugar de inventar
5. Incluye los 3 estados: loading, empty, error
6. Verifica con `preview_screenshot` al terminar

**Si la pantalla ya existe en index.html, "haz pantalla X" = rediseñarla** (no crear duplicado).

## Reglas no negociables

- **Sin frameworks nuevos**: Alpine.js + CSS puro. Nada de Tailwind, React, Vue.
- **Solo tokens del DS**: no inventes hex codes ni spacings. Si necesitas algo nuevo, propónlo en `tokens.json` primero.
- **Mobile-first 480px**: nada de desktop layouts.
- **Sin comentarios obvios**: el código se explica solo.
- **Verifica antes de cerrar**: screenshot obligatorio.

## Plan gating (importante)

Variable `userPlan` puede ser `'free' | 'pro' | 'elite'`.
Flag `devUnlockAll: true` (línea ~2419) fuerza `elite` para QA — déjalo así durante desarrollo.

Gates correctos:
- **Voz / Presupuesto mensual / Alertas / Multi-moneda**: Pro+
- **Foto OCR / Archivo / Presupuesto por categoría / Exportar / Dashboard analytics / Resumen email**: Elite

## OBLIGATORIO antes de commitear index.html

**Git commit-msg hook activo**: si el commit incluye `index.html`, el mensaje DEBE contener `VERIFIED: <lo que verificaste>`. Sin esto, el commit se bloquea.

**Deploy bloqueado por Regression Guard**: si alguno de los 6 CSS values del watchlist tiene un valor incorrecto, el deploy NO se ejecuta.

### Checklist pre-commit (index.html):
1. Grep regression watchlist (tab-bar 52px, FAB 24px, content 80px, approve-header safe-top, toggle static style, padding-top 6px)
2. Abrir la app como usuario real (preview_screenshot o Chrome) — NO simular datos
3. Incluir `VERIFIED: <descripcion>` en el commit message
4. Si NO pudiste verificar: decir `VERIFIED: no pude verificar X, necesito screenshot de Alvaro`

### Regression watchlist — valores correctos (v46+):
| CSS | Valor correcto |
|-----|---------------|
| `.tab-bar height` | `var(--tab-total)` |
| `.main-content padding-bottom` | `var(--content-pad-bottom)` |
| `.fab bottom` | `var(--fab-bottom)` |
| `.approve-header padding-top` | `var(--overlay-pad-top)` |
| Toggle gasto/ingreso | `style="display:flex;..."` (estático, NO `:style`) |
| `.tab-bar padding-top` | `10px` |
| `.cd-split-picker background` | `var(--surface)` (NUNCA `var(--card)`) |
| `.cd-split-picker-avatar color` | `var(--bg)` (NUNCA `#000`) |

## Component Catalog (OBLIGATORIO leer antes de crear cualquier elemento UI)

### Design Tokens (`:root`)
| Token | Valor | Usar para |
|-------|-------|-----------|
| `--bg` | `#0A0A0F` | Fondo principal, texto sobre gradient |
| `--surface` | `#13131A` | Cards, inputs, containers |
| `--surface2` | `#191923` | Surface anidada |
| `--border` | `#1E1E2E` | Bordes de cards |
| `--border2` | `#2A2A3D` | Bordes secundarios |
| `--cyan` | `#00F0FF` | Accent principal |
| `--purple` | `#7000FF` | Accent secundario |
| `--gradient` | `linear-gradient(135deg, #00F0FF, #7000FF)` | Botones CTA, badges, highlights |
| `--text` | `#FFFFFF` | Texto principal |
| `--muted` | `#8888AA` | Labels, hints |
| `--dim` | `#5A5A75` | Placeholders |
| `--success` | `#00E5A0` | Ingresos, positivos |
| `--warning` | `#FFB800` | Alertas |
| `--danger` | `#FF6B6B` | Errores, gastos altos |
| `--radius` | `16px` | Cards estándar |
| `--radius-sm` | `10px` | Chips, inputs |
| `--radius-pill` | `50px` | Botones CTA |
| `--tab-total` | `calc(84px + safe-bottom)` | Altura tab bar |
| `--content-pad-bottom` | `calc(100px + safe-bottom)` | Padding inferior main-content |
| `--fab-bottom` | `calc(38px + safe-bottom)` | Posicion FAB |
| `--overlay-pad-top` | `calc(safe-top + 16px)` | Top de overlays |

### Clases de botones
| Clase | Uso | Forma |
|-------|-----|-------|
| `.save-btn` | CTA principal en sheets/modals | Full-width, 52px, pill, gradient, font-700 |
| `.btn-primary` | CTA secundarios, inline actions | Auto-width, 48px, pill, gradient, font-700 |
| `.pay-btn` | Solo para pagos | Full-width, 56px, pill, gradient + shadow |
| `.btn-accept` | Aceptar (verde) | Inline, 10px radius, success bg |
| `.btn-decline` | Rechazar (rojo) | Inline, 10px radius, danger bg |

### Reglas de estilo para adiciones
1. **NUNCA usar inline `style=""` para botones** — usar `.save-btn`, `.btn-primary` o `.pay-btn`
2. **NUNCA inventar hex codes** — solo tokens CSS (`var(--surface)`, `var(--cyan)`, etc.)
3. **NUNCA usar border-radius hardcoded** — solo `var(--radius)`, `var(--radius-sm)`, `var(--radius-pill)`
4. **NUNCA `var(--card)`** — NO EXISTE. Usar `var(--surface)` o `var(--surface2)`
5. **NUNCA `color: #000`** en texto — usar `var(--bg)` (se adapta a themes)
6. **NUNCA `:style` binding en containers con `x-show`** — rompe `display:flex`. Usar `style=""` estático
7. **Cards**: `background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius)`
8. **Inputs**: usar clases `.field-box` + `.field-box-inner` existentes
9. **Section labels**: usar clase `.cd-section-label`
10. **Overlays**: usar clase `.safe-overlay` + `padding-top: var(--overlay-pad-top)`

### Variables que NO existen (errores comunes)
`--card`, `--bg-dark`, `--primary`, `--secondary`, `--accent` — NINGUNA existe. No inventar tokens.

## Anti-patterns que ya cometimos (no repetir)

- ❌ Usar `eval()` para manipular Alpine en vez de hacer clic real en QA
- ❌ Decir "pantalla OK" despues de ver snapshot sin haber tocado botones
- ❌ Asumir que un boton funciona porque existe en el DOM
- ❌ Simular datos JSON y declarar "verificado" sin abrir la app
- ❌ Commitear sin VERIFIED: tag
- ✅ Hacer clic real con `preview_click` y verificar el resultado
- ✅ Si no puedes verificar, decirlo ANTES del commit
