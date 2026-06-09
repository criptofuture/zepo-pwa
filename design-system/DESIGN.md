# Zepo · Design System

> **Lee este archivo primero** antes de crear o editar cualquier pantalla.
> Es la fuente de verdad para mantener coherencia visual entre todas las pantallas.

## 1. Identidad de marca

**Zepo** = "Tu dinero, claro."

- No es un banco — es la **memoria financiera** del usuario.
- Estética: **Linear meets Revolut**, hablado en LATAM, gen-Z friendly.
- Tono: minimal, inteligente, honesto. Cero jerga corporativa.

## 2. Pilares visuales (no negociables)

| Pilar | Regla |
|---|---|
| **Fondo** | Siempre near-black `#0A0A0F`. Nunca blanco. |
| **Gradiente** | `linear-gradient(135deg, #00F0FF, #7000FF)` reservado para: heroes, CTAs primarios, montos hero, plan-card.elite. **No abusar.** |
| **Glass morphism** | Sheets y modals usan `backdrop-filter: blur(24px) saturate(140%)`. Cards comunes son sólidas `#13131A`. |
| **Numerales** | Toda cantidad monetaria en `JetBrains Mono` con `font-feature-settings: "tnum"` (tabular nums obligatorio para alinear columnas). |
| **Spacing** | Múltiplos de 4px. Padding horizontal de pantalla: 24px. |
| **Bordes** | 1px sólido `#1E1E2E` para cards. Nunca 2px. |
| **Radius** | Cards 16-20px. Botones 14px o pill. Chips 8px. |

## 3. Lenguaje tipográfico

- **Font sans**: Inter (400, 500, 600, 700, 800).
- **Font mono**: JetBrains Mono — **solo** para números/montos.
- **Hero**: 48-56px, weight 800, tracking -1.5px, gradient fill.
- **Header pantalla**: 24px, weight 800, tracking -0.8px.
- **Body**: 15px, weight 400, line-height 1.5.
- **Caption uppercase**: 11px, weight 700, tracking 1.2px, color `--muted`.

## 4. Microinteracciones obligatorias

| Acción | Comportamiento |
|---|---|
| Tap en botón | `transform: scale(0.97)` durante 120ms ease-out |
| Entrada de sheet | `translateY(100%) → 0` en 320ms con curva iOS `cubic-bezier(0.32, 0.72, 0, 1)` |
| Loading | **Skeleton shimmer**, NUNCA spinner genérico |
| Focus input | `box-shadow: 0 0 0 3px rgba(0,240,255,0.2)` |
| Toast | Slide-up desde abajo + fade out 3s |
| Long-press | Vibrar (`navigator.vibrate(10)`) si disponible |

## 5. Hierarquía de pantallas

Ver `components.md` para catálogo de componentes y `patterns.md` para flujos.

```
01 · Onboarding (splash, auth, welcome, currency, plan, first expense)
02 · Home (free / pro / elite + variantes sunset)
03 · Input sheet (texto, voz, foto, archivo)
04 · Aprobar registro (review intermedia universal)
05 · Cobros (lista de splits pendientes)
06 · Historial
07 · Presupuestos
08 · Dashboard (analytics)
09 · Configuración
10 · Planes & Checkout
11 · Cuenta (perfil, cambiar pw, eliminar)
12 · Estados vacíos
```

## 6. Reglas para el agente AI (Claude Code / CD)

Cuando se te pida crear o editar una pantalla:

1. **Lee `tokens.json`** y usa SOLO tokens semánticos. Nunca inventes hex codes.
2. **Lee `components.md`** y reutiliza componentes. Si necesitas uno nuevo, propónlo antes de crearlo.
3. **Lee el `patterns.md`** de la sección correspondiente.
4. **Incluye los 3 estados base**: loading, empty, error. No solo el happy path.
5. **Verifica visualmente** con `preview_screenshot` antes de cerrar la tarea.
6. **No agregues comentarios** que digan lo que el código hace — los nombres deben ser autoexplicativos.

## 7. Do / Don't

| ✅ Do | ❌ Don't |
|---|---|
| Usar gradient solo para acentuar 1 elemento por pantalla | Aplicar gradient a múltiples elementos en la misma vista |
| Tabular nums en todos los montos | Números con tipografía proporcional |
| Glass solo en sheets/modals | Glass en cards normales (rompe contraste) |
| Empty states con ícono + CTA | Empty states con texto plano |
| Confirmar acciones destructivas (`confirm()` o modal) | Eliminar sin confirmación |
| Botones pill para CTAs principales | Botones cuadrados con border-radius pequeño |
| Mobile-first 480px | Layouts desktop |

## 8. Plan gating (visual)

Cada feature con gate de plan debe seguir este patrón:

- **Free intenta acción Pro**: abrir modal upsell con ícono, copy claro, botón "Ver planes" + "Cancelar".
- **No deshabilitar** botones sin razón visible. Mostrar el feature con `lock-icon` y al tap → upsell.

## 9. Stack técnico (compatible con el design)

- HTML + Alpine.js + Supabase (sin build step).
- Tailwind NO — usar CSS variables con tokens de `tokens.json`.
- React/Vue NO — Alpine.js suficiente.
- Framer Motion NO — usar CSS animations + `x-transition` de Alpine.

## 10. Referencias externas (inspiración)

- **Linear** — claridad, jerarquía tipográfica
- **Revolut** — montos hero, charts limpios
- **Splitwise** — UX de splits
- **Cash App** — gen-Z energy
- **Mobbin** (fintech category) — patrones reales actualizados

## 11. Cómo extender este sistema

Cuando aparezca un patrón nuevo en 2+ pantallas:
1. Documéntalo en `components.md` con código de ejemplo.
2. Si requiere tokens nuevos, agrégalos a `tokens.json` con descripción.
3. Si es un flujo, documéntalo en `patterns.md`.
4. Actualiza este archivo si cambia algo fundamental.
