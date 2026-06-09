# Zepo · Catálogo de componentes

> Lee `DESIGN.md` y `tokens.json` antes de tocar este archivo.
> Cada componente aquí tiene: **uso**, **props mentales**, **snippet HTML+Alpine**, **estados**.

## Índice

- [Card](#card)
- [Card hero (con gradient)](#card-hero)
- [Button primary (CTA)](#button-primary)
- [Button secondary (outline)](#button-secondary)
- [Button ghost](#button-ghost)
- [Button danger](#button-danger)
- [FAB (floating action)](#fab)
- [Chip / Pill](#chip)
- [Badge plan](#badge-plan)
- [Input text](#input-text)
- [Input numeric (monto)](#input-numeric)
- [Toggle switch](#toggle)
- [Bottom sheet](#bottom-sheet)
- [Modal de confirmación](#modal)
- [List item](#list-item)
- [Empty state](#empty-state)
- [Progress bar](#progress-bar)
- [Tab bar](#tab-bar)
- [Toast](#toast)

---

## <a name="card"></a>Card
**Uso**: contenedor de información de primer nivel. No glass.

```html
<div style="background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:18px;">
  ...
</div>
```

## <a name="card-hero"></a>Card hero (con gradient)
**Uso**: una sola por pantalla — destaca el balance principal o métrica clave.

```html
<div style="background:linear-gradient(135deg, rgba(0,240,255,0.06), rgba(112,0,255,0.08));
            border:1.5px solid rgba(112,0,255,0.3); border-radius:20px;
            box-shadow:0 0 24px rgba(112,0,255,0.08); padding:24px;">
  <div style="font-size:11px; color:var(--muted); font-weight:700; letter-spacing:1.2px;">GASTADO EN MAYO</div>
  <div style="font-size:48px; font-weight:800; letter-spacing:-1.5px; font-family:'JetBrains Mono';
              font-feature-settings:'tnum';">
    <span style="color:var(--muted); font-size:24px; vertical-align:12px;">$</span>
    <span class="gradient-text">2,847.30</span>
  </div>
</div>
```

## <a name="button-primary"></a>Button primary (CTA)
**Uso**: acción principal de la pantalla. Máximo 1 por vista.

```html
<button @click="action" style="
  width:100%; height:48px; border-radius:14px;
  background:linear-gradient(135deg, #00F0FF, #7000FF);
  color:#0A0A0F; font-size:15px; font-weight:700;
  box-shadow:0 4px 16px rgba(0,240,255,0.2);
  display:flex; align-items:center; justify-content:center; gap:8px;
  transition:transform 120ms ease-out;
" onpointerdown="this.style.transform='scale(0.97)'" onpointerup="this.style.transform='scale(1)'">
  Texto del botón
</button>
```

## <a name="button-secondary"></a>Button secondary (outline)
```html
<button style="width:100%;height:46px;border-radius:23px;background:transparent;
  border:1px solid var(--cyan); color:var(--cyan); font-weight:700; font-size:14px;">
  Texto
</button>
```

## <a name="button-ghost"></a>Button ghost
**Uso**: acciones secundarias dentro de sheets ("Cancelar").
```html
<button style="width:100%;height:40px;background:transparent;color:var(--muted);
  font-size:13px;font-weight:600;">Cancelar</button>
```

## <a name="button-danger"></a>Button danger
```html
<button style="width:100%;padding:14px;border-radius:999px;
  border:1px solid rgba(255,107,107,0.3); color:var(--danger);
  background:rgba(255,107,107,0.05); font-weight:600;">
  Eliminar
</button>
```

## <a name="fab"></a>FAB
```html
<button class="fab" @click="openNew">
  <svg viewBox="0 0 24 24" fill="none"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
</button>
```
CSS:
```css
.fab {
  position:fixed; bottom:80px; left:50%; transform:translateX(-50%);
  width:60px; height:60px; border-radius:30px;
  background:linear-gradient(135deg, #00F0FF, #7000FF);
  box-shadow:0 4px 16px rgba(0,240,255,0.3);
  display:flex; align-items:center; justify-content:center;
}
```

## <a name="chip"></a>Chip / Pill
**Uso**: filtros, selectores de categoría, tags.
```html
<button :class="{ selected: active }" style="
  padding:8px 14px; border-radius:999px; font-size:13px; font-weight:600;
  background:var(--surface); border:1px solid var(--border); color:var(--muted);
">Etiqueta</button>

<!-- estado seleccionado -->
.selected { background:rgba(0,240,255,0.10); border-color:var(--cyan); color:var(--cyan); }
```

## <a name="badge-plan"></a>Badge plan
```html
<span class="plan-badge free">FREE</span>
<span class="plan-badge pro">PRO</span>
<span class="plan-badge elite">ELITE</span>
```
CSS:
```css
.plan-badge { font-size:10px; font-weight:700; padding:3px 8px; border-radius:6px; letter-spacing:0.4px; }
.plan-badge.free  { background:rgba(0,229,160,0.12); color:var(--success); }
.plan-badge.pro   { background:rgba(0,240,255,0.12); color:var(--cyan); }
.plan-badge.elite { background:rgba(112,0,255,0.15); color:var(--purple); }
```

## <a name="input-text"></a>Input text
```html
<input class="field-input" type="text" x-model="form.field" placeholder="Placeholder">
```
CSS:
```css
.field-input {
  width:100%; height:48px; padding:0 16px;
  background:var(--surface); border:1px solid var(--border); border-radius:14px;
  color:var(--text); font-size:15px; font-family:inherit;
  transition:border-color 200ms ease;
}
.field-input:focus { outline:none; border-color:var(--cyan); box-shadow:0 0 0 3px rgba(0,240,255,0.2); }
```

## <a name="input-numeric"></a>Input numeric (monto)
**Crítico**: sin flechitas spinner. Mono font para alineación.
```html
<input type="number" inputmode="decimal" step="0.01" min="0" placeholder="0.00"
       x-model="form.amount" class="field-input"
       style="font-family:'JetBrains Mono';font-feature-settings:'tnum';text-align:right;">
```
El reset global ya está en `index.html`:
```css
input[type=number]::-webkit-inner-spin-button,
input[type=number]::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
input[type=number] { -moz-appearance:textfield; appearance:textfield; }
```

## <a name="toggle"></a>Toggle switch
```html
<button @click="form.flag = !form.flag" class="toggle" :class="{ on: form.flag }">
  <span class="toggle-dot"></span>
</button>
```
CSS:
```css
.toggle { width:44px; height:24px; border-radius:12px; background:var(--surface2); border:1px solid var(--border); position:relative; transition:background 200ms; }
.toggle-dot { position:absolute; left:2px; top:2px; width:18px; height:18px; border-radius:9px; background:var(--muted); transition:all 200ms; }
.toggle.on { background:rgba(0,240,255,0.15); border-color:var(--cyan); }
.toggle.on .toggle-dot { left:22px; background:var(--cyan); }
```

## <a name="bottom-sheet"></a>Bottom sheet
**Uso**: para acciones contextuales (agregar gasto, crear presupuesto, etc).

```html
<template x-if="sheetOpen">
  <div>
    <div class="sheet-backdrop" @click="sheetOpen = false"></div>
    <div class="sheet">
      <div class="sheet-grabber"></div>
      <!-- contenido -->
    </div>
  </div>
</template>
```
CSS:
```css
.sheet-backdrop { position:fixed; inset:0; background:rgba(10,10,15,0.6); backdrop-filter:blur(8px); z-index:90; animation:fadeIn 200ms ease-out; }
.sheet {
  position:fixed; bottom:0; left:0; right:0; max-width:480px; margin:0 auto;
  background:rgba(19,19,26,0.92); backdrop-filter:blur(24px) saturate(140%);
  border-top:1px solid var(--border); border-radius:24px 24px 0 0;
  padding:20px 24px 32px; z-index:100; max-height:90vh; overflow-y:auto;
  animation:slideUp 320ms cubic-bezier(0.32, 0.72, 0, 1);
}
.sheet-grabber { width:36px; height:4px; background:var(--border2); border-radius:2px; margin:0 auto 16px; }
@keyframes slideUp { from { transform:translateY(100%) } to { transform:translateY(0) } }
```

## <a name="modal"></a>Modal de confirmación
**Uso**: acciones destructivas (eliminar cuenta).

```html
<div x-show="showModal" style="position:fixed;inset:0;background:rgba(0,0,0,0.7);
     backdrop-filter:blur(8px);z-index:200;display:flex;align-items:center;justify-content:center;padding:24px;">
  <div style="max-width:360px;background:var(--surface);border:1px solid var(--border);
              border-radius:20px;padding:24px;">
    <!-- icon + título + texto + 2 botones -->
  </div>
</div>
```

## <a name="list-item"></a>List item (gasto, cobro, etc)
```html
<div class="expense-row" @click="openEdit(item)">
  <div class="expense-cat-icon" :style="'background:'+catColor">🍽</div>
  <div style="flex:1;min-width:0;">
    <div style="font-size:14px;font-weight:600;color:var(--text);" x-text="item.description"></div>
    <div style="font-size:11px;color:var(--dim);" x-text="formatDate(item.date)"></div>
  </div>
  <div style="font-family:'JetBrains Mono';font-feature-settings:'tnum';font-weight:700;font-size:15px;
              color:var(--text);" x-text="'-$' + fmtMoney(item.amount)"></div>
</div>
```

## <a name="empty-state"></a>Empty state
```html
<div style="text-align:center;padding:48px 24px;">
  <div style="width:72px;height:72px;border-radius:20px;background:rgba(0,240,255,0.08);
              border:1px solid rgba(0,240,255,0.2);display:flex;align-items:center;justify-content:center;
              margin:0 auto 20px;">
    <svg width="32" height="32" stroke="var(--cyan)" stroke-width="1.8" fill="none">...</svg>
  </div>
  <div style="font-size:18px;font-weight:800;margin-bottom:8px;">Sin <span class="gradient-text">X</span></div>
  <div style="font-size:13px;color:var(--muted);line-height:1.5;margin-bottom:24px;">
    Texto guía explicando qué hacer.
  </div>
  <button class="cta-button">Acción primaria</button>
</div>
```

## <a name="progress-bar"></a>Progress bar
```html
<div style="height:4px;background:var(--border);border-radius:2px;overflow:hidden;">
  <div style="height:100%;border-radius:2px;transition:width 400ms ease;"
       :style="'width:' + pct + '%; background:' + (pct >= 100 ? 'var(--danger)' : pct >= 80 ? 'var(--warning)' : 'var(--gradient)')"></div>
</div>
```

## <a name="tab-bar"></a>Tab bar
```html
<nav class="tab-bar">
  <button class="tab-item" :class="{ active: tab === 'home' }" @click="tab = 'home'">
    <svg>...</svg>
    <span>Inicio</span>
  </button>
  ...
</nav>
```
CSS:
```css
.tab-bar { position:fixed; bottom:0; left:0; right:0; max-width:480px; margin:0 auto;
  display:flex; padding:8px 4px 12px; background:rgba(10,10,15,0.85);
  backdrop-filter:blur(20px); border-top:1px solid var(--border); z-index:50; }
.tab-item { flex:1; display:flex; flex-direction:column; align-items:center; gap:2px;
  font-size:10px; color:var(--dim); font-weight:600; padding:6px 0; }
.tab-item.active { color:var(--cyan); }
.tab-item.active svg { stroke:var(--cyan); }
```

## <a name="toast"></a>Toast
```html
<div x-show="toast" x-transition style="
  position:fixed; bottom:96px; left:50%; transform:translateX(-50%);
  background:var(--surface); border:1px solid var(--border); padding:12px 20px;
  border-radius:999px; font-size:13px; font-weight:600; z-index:300;
  box-shadow:0 8px 32px rgba(0,0,0,0.4);
" x-text="toast"></div>
```
JS:
```js
showToast(msg) { this.toast = msg; setTimeout(() => this.toast = '', 3000); }
```

---

## Cuándo crear un componente nuevo

- Se usa en **2+ pantallas** → componente.
- Se usa en 1 pantalla pero tiene >50 líneas de markup → extraer (legibilidad).
- Es markup específico de la página sin reuso previsto → inline.

## Cómo proponer un componente nuevo

1. Edita este archivo en una rama.
2. Agrega sección con nombre, uso, snippet, estados.
3. Si requiere tokens nuevos, edita `tokens.json` también.
4. Documenta dónde se usa la primera vez.
