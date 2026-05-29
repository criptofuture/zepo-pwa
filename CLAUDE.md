# Zepo PWA · Instrucciones para Claude

## Proyecto
Zepo — expense tracker LATAM, mobile-first PWA, single `index.html` con Alpine.js + Supabase.

**Marca V2.0 "Bricolage" (editorial cálida, mayo 2026)**: fondo crema, acento sage/verde, tipografía display Bricolage Grotesque. NO es dark/neón. Si ves cyan #00F0FF o purple #7000FF en código nuevo → es un error (solo viven en la dev toolbar gated).

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

### Design Tokens (`:root`) — V2.0 editorial

**Arquitectura de 2 capas**: tokens semánticos `--c-*` (fuente de verdad) + aliases viejos (`--bg`, `--cyan`, etc.) que apuntan a los semánticos. Las 1.429 referencias `var(--cyan)`, `var(--success)`... siguen funcionando porque su VALOR ahora es editorial. **No reintroduzcas los hex viejos.**

**Capa semántica (el flip cambia SOLO estos):**
| Token | Valor | Usar para |
|-------|-------|-----------|
| `--c-bg` | `#EFEADB` | Fondo principal crema |
| `--c-surface` | `#FFFFFF` | Cards, inputs |
| `--c-surface-2` | `#F4EFE2` | Surface anidada |
| `--c-ink` | `#1A2418` | Texto principal (verde casi-negro) |
| `--c-ink-soft` | `rgba(26,36,24,.62)` | Labels, muted |
| `--c-ink-faint` | `rgba(26,36,24,.40)` | Placeholders, dim |
| `--c-border` | `rgba(26,36,24,.14)` | Bordes |
| `--c-border-strong` | `rgba(26,36,24,.30)` | Bordes secundarios |
| `--c-brand` | `#507D5A` | Accent sage principal |
| `--c-brand-rgb` | `80,125,90` | Para `rgba(var(--c-brand-rgb),α)` |
| `--c-accent` | `#D6D864` | Accent lima (highlights) |
| `--c-accent-rgb` | `214,216,100` | Para `rgba(var(--c-accent-rgb),α)` |
| `--c-accent-soft` | `#BF8A2A` | Gold legible para texto de acento sobre crema |
| `--c-income` | `#84AF72` | Ingresos / positivos |
| `--c-expense` | `#B8483A` | Gastos / negativos |
| `--c-warning` | `#BF8A2A` | Alertas |
| `--c-brand-contrast` | `#FFFFFF` | Texto sobre botón sage |
| `--c-ink-rgb` | `26,36,24` | Sombras: `rgba(26,36,24,.16)` |
| `--grad-brand` | `linear-gradient(135deg,#507D5A,#84AF72)` | CTAs, badges |

**Aliases (apuntan a semánticos — usar libremente):**
`--bg`→`--c-bg` · `--surface`→`--c-surface` · `--surface2`→`--c-surface-2` · `--border`→`--c-border` · `--border2`→`--c-border-strong` · `--cyan`→`--c-brand` · `--purple`→`--c-accent` · `--gradient`→`--grad-brand` · `--text`→`--c-ink` · `--muted`→`--c-ink-soft` · `--dim`→`--c-ink-faint` · `--success`→`--c-income` · `--warning`→`--c-warning` · `--danger`→`--c-expense`

**Tipografía:**
| Token | Valor | Usar para |
|-------|-------|-----------|
| `--font-display` | `'Bricolage Grotesque'` | Headers, montos, `.mono` |
| `--font-body` | `'Geist'` | Texto cuerpo (body default) |

**Layout / radius (sin cambios):**
| Token | Valor |
|-------|-------|
| `--radius` / `--radius-sm` / `--radius-pill` | `16px` / `10px` / `50px` |
| `--tab-total` | `calc(84px + safe-bottom)` |
| `--content-pad-bottom` | `calc(84px + 16px + safe-bottom)` |
| `--fab-bottom` | `calc(38px + safe-bottom)` |
| `--overlay-pad-top` | `calc(safe-top + 16px)` |

`meta theme-color` = `#EFEADB`. `html { color-scheme: light }`.

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
5. **NUNCA neón** — `#00F0FF`, `#7000FF`, `#00E5A0`, `#FF6B6B`, `#FFB800`, `#B794F6` están PROHIBIDOS (marca vieja). El linter `tools/lint-design.py` bloquea el commit/deploy si aparecen fuera de la dev toolbar.
6. **Texto de contraste sobre botón sage** — usar `var(--c-brand-contrast)` (#FFF), NO `#000` ni `var(--bg)` (el tema es claro ahora, `--bg` es crema).
7. **NUNCA `:style` binding en containers con `x-show`** — rompe `display:flex`. Usar `style=""` estático
8. **Cards**: `background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius)`
9. **Inputs**: usar clases `.field-box` + `.field-box-inner` existentes
10. **Section labels**: usar clase `.cd-section-label`
11. **Overlays**: usar clase `.safe-overlay` + `padding-top: var(--overlay-pad-top)`
12. **Tints de color**: usar `rgba(var(--c-brand-rgb),α)` / `rgba(var(--c-accent-rgb),α)`, NO literales rgba de la paleta vieja.

### Variables que NO existen (errores comunes)
`--card`, `--bg-dark`, `--primary`, `--secondary`, `--accent` — NINGUNA existe. No inventar tokens. (`--c-accent` SÍ existe; `--accent` NO.)

### Guardrail automático
`tools/lint-design.py index.html` corre en pre-commit (local) y en el job `regression-check` de CI. **FAIL** = neón/tokens inexistentes/bug toggle. **WARN** = residuo rgba de paleta vieja (no bloquea). La dev toolbar (`DEV TOOLBAR — solo zepo-staging` → EOF) está en allowlist.

## Anti-patterns que ya cometimos (no repetir)

- ❌ Usar `eval()` para manipular Alpine en vez de hacer clic real en QA
- ❌ Decir "pantalla OK" despues de ver snapshot sin haber tocado botones
- ❌ Asumir que un boton funciona porque existe en el DOM
- ❌ Simular datos JSON y declarar "verificado" sin abrir la app
- ❌ Commitear sin VERIFIED: tag
- ✅ Hacer clic real con `preview_click` y verificar el resultado
- ✅ Si no puedes verificar, decirlo ANTES del commit
