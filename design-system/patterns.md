# Zepo · Patrones de flujo

> Patrones canónicos para flujos multi-pantalla.
> Lee `DESIGN.md` y `components.md` primero.

## 1. Agregar gasto (flujo principal)

```
[Home] → tap FAB → [Bottom sheet: Aprobar registro]
   ↓
   Modo: Texto / Voz / Foto / Archivo
   ↓
   Usuario ingresa input (texto libre, audio, imagen, archivo)
   ↓
   ✨ Tap "Analizar" → IA parsea
   ↓
   Lista de items detectados (cada uno con descripción, monto, dropdown categoría)
   ↓
   Usuario revisa / corrige
   ↓
   Tap "Aprobar todo" → guarda en Supabase → sheet cierra → Home actualiza
```

**Reglas**:
- En modo Texto, el botón "Analizar" es OBLIGATORIO antes de aprobar.
- Si IA detecta un solo gasto, va directo a la edición simple sin lista.
- Cada item de la lista tiene su propia categoría (dropdown), no una grid global.
- Modo Voz transcribe → auto-llama "Analizar" sin botón intermedio.

## 2. Dividir gasto (split)

Dentro del sheet de agregar:
```
Toggle "Dividir gasto" ON
   ↓
Expande sección:
   - Input "Nombre persona" (autocomplete con historial)
   - Slider de % (0-100)
   - Preview: "Tú pagas $X · Persona debe $Y"
   ↓
Al aprobar:
   - Se guarda el gasto con mi parte como amount
   - Se crea un split_pending para "Persona" con la otra parte
   - Aparece en pantalla Cobros automáticamente
```

## 3. Marcar cobro como pagado

```
[Cobros] → tap chip "Cobrado" en un split
   ↓
Animación: fade-out del item + toast "Marcado como cobrado"
   ↓
Supabase: split_status = 'cobrado'
   ↓
Lista filtra solo pendientes
```

## 4. Onboarding (primer uso)

```
1. SPLASH (logo + carga inicial, 800ms)
2. AUTH (sign up o login)
3. WELCOME (1/3) — "Bienvenido a Zepo. Tu memoria financiera."
4. CURRENCY (2/3) — Selección de moneda principal (default USD)
5. PLAN (3/3) — Selección de plan (default Free)
6. FIRST EXPENSE — Tutorial: agrega tu primer gasto
   - Si lo agrega → Home con confeti sutil
   - Si lo skip → Home empty state
```

**Reglas**:
- No se puede saltar Welcome ni Currency.
- Plan SÍ se puede skip (default Free).
- First expense SÍ se puede skip ("Más tarde").
- Estado persiste en localStorage: `zepo:onboarding-step`.

## 5. Cambiar plan

```
[Settings] → tap "Cambiar plan"
   ↓
[Planes] → tap "Mejorar a PRO/ELITE"
   ↓
[Checkout] → revisar resumen → tap "Pagar con PayPhone"
   ↓
[Procesando] → loading state animado
   ↓
   ├── Éxito → [Éxito] → "Tu plan ahora es X" → vuelve a Home
   └── Fallo  → [Fallo]  → opción reintentar
```

## 6. Recuperar contraseña

```
[Login] → tap "¿Olvidé contraseña?"
   ↓
[Forgot password] → ingresar email → tap "Enviar"
   ↓
[Forgot sent] → "Revisa tu email" + botón "Volver al login"
```

## 7. Gate de plan (upsell)

Cuando Free intenta acción Pro/Elite:
```
Tap acción → modal/sheet de upsell
   ↓
Contenido:
   - Ícono grande con halo gradient
   - Título "Esta función es Pro/Elite"
   - 1 frase explicando valor
   - Botón "Ver planes" (primary)
   - Botón "Cancelar" (ghost)
```

**NO**:
- Deshabilitar el botón sin razón visible.
- Mostrar toast genérico "Mejora tu plan".
- Bloquear el acceso completamente — siempre dar salida al modal.

## 8. Estados de error

| Tipo | Patrón |
|---|---|
| Validación inline | Texto rojo debajo del input + borde rojo |
| Error de red | Toast rojo "Sin conexión" + retry button |
| Error de Supabase | Toast "Error: <mensaje>" + log en console |
| 404 / pantalla no encontrada | Empty state con "Volver al inicio" |

## 9. Loading states

- **Inicial de pantalla**: skeleton de elementos principales (NO spinner).
- **Acción de botón**: cambiar texto a "Cargando..." + disabled.
- **Async background**: indicador sutil arriba (línea de progreso fina).

## 10. Vacío vs sin permisos

| Caso | Tratamiento |
|---|---|
| Usuario nuevo, sin datos | Empty state con ilustración + CTA primario |
| Tiene datos pero filtro vacío | Texto neutral "Sin resultados con este filtro" |
| Sin permisos / plan inferior | Upsell pattern (ver §7) |
| Sin internet | Toast persistente + sync cuando vuelva |

## 11. Confirmación destructiva

Para acciones que eliminan datos:
```
Tap "Eliminar X"
   ↓
[Confirm modal o native confirm()]
   ↓
"¿Eliminar X? Esta acción no se puede deshacer."
   ↓
[Cancelar] [Eliminar (rojo)]
```

Excepción: eliminar **cuenta** requiere typing "ELIMINAR" como confirmación extra.
