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

### Regression watchlist — valores correctos:
| CSS | Valor correcto |
|-----|---------------|
| `.tab-bar height` | `calc(52px + var(--safe-bottom))` |
| `.main-content padding-bottom` | `calc(80px + var(--safe-bottom))` |
| `.fab bottom` | `calc(24px + var(--safe-bottom))` |
| `.approve-header padding` | `calc(var(--safe-top) + 14px) 20px 12px` |
| Toggle gasto/ingreso | `style="display:flex;..."` (estatico, NO `:style`) |
| `.tab-bar padding-top` | `6px` |

## Anti-patterns que ya cometimos (no repetir)

- ❌ Usar `eval()` para manipular Alpine en vez de hacer clic real en QA
- ❌ Decir "pantalla OK" despues de ver snapshot sin haber tocado botones
- ❌ Asumir que un boton funciona porque existe en el DOM
- ❌ Simular datos JSON y declarar "verificado" sin abrir la app
- ❌ Commitear sin VERIFIED: tag
- ✅ Hacer clic real con `preview_click` y verificar el resultado
- ✅ Si no puedes verificar, decirlo ANTES del commit
