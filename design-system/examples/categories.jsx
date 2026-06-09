// Zepo · expense + income categories. Two parallel maps for the two surfaces
// they appear in:
//   - CATEGORIES   — keyed name → emoji/label/color, used in expense rows
//   - APPROVE_CATS — ordered array used by the approval / settings pickers
// CategoryChip renders the small rounded-square emoji tile shared by both.

const CATEGORIES = {
  food:    { emoji: '🍽',  label: 'Comida',         color: '#FF6B6B' },
  transport:{emoji: '🚌',  label: 'Transporte',     color: '#00F0FF' },
  health:  { emoji: '💊',  label: 'Salud',          color: '#00E5A0' },
  fun:     { emoji: '🎮',  label: 'Entretenimiento', color: '#7000FF' },
  shop:    { emoji: '🛍',  label: 'Compras',        color: '#FFB800' },
  other:   { emoji: '✨',  label: 'Otros',          color: '#8888AA' },
  coffee:  { emoji: '☕️',  label: 'Café',           color: '#C49A6C' },
  taxi:    { emoji: '🚖',  label: 'Taxi',           color: '#FFB800' },
  market:  { emoji: '🛒',  label: 'Mercado',        color: '#00E5A0' },
  rent:    { emoji: '🏠',  label: 'Vivienda',       color: '#7000FF' },
};
window.CATEGORIES = CATEGORIES;

// Categories surfaced in the Aprobar / Editar / Settings flow.
const APPROVE_CATS = [
  { k: 'food',      l: 'Comida',          emoji: '🍽',  c: '#FF6B6B' },
  { k: 'transport', l: 'Transporte',      emoji: '🚌',  c: '#00F0FF' },
  { k: 'health',    l: 'Salud',           emoji: '💊',  c: '#00E5A0' },
  { k: 'home',      l: 'Hogar',           emoji: '🏠',  c: '#7000FF' },
  { k: 'fun',       l: 'Entretenimiento', emoji: '🎮',  c: '#B794F6' },
  { k: 'edu',       l: 'Educación',       emoji: '📚',  c: '#FFB800' },
  { k: 'other',     l: 'Otro',            emoji: '✨',  c: '#8888AA' },
];
window.APPROVE_CATS = APPROVE_CATS;

function CategoryChip({ k, size = 40 }) {
  const c = CATEGORIES[k] || CATEGORIES.other;
  return (
    <div style={{
      width: size, height: size, borderRadius: 12,
      background: `${c.color}15`,
      border: `1px solid ${c.color}30`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.5, flexShrink: 0,
    }}>{c.emoji}</div>
  );
}
window.CategoryChip = CategoryChip;
