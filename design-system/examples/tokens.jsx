// Zepo · design tokens — colors, fonts, dimensions.
// First script to load: every other component depends on `Z`.

const Z = {
  bg:        '#0A0A0F',
  surface:   '#13131A',
  surface2:  '#191923',
  border:    '#1E1E2E',
  border2:   '#2A2A3D',
  cyan:      '#00F0FF',
  purple:    '#7000FF',
  text:      '#FFFFFF',
  muted:     '#8888AA',
  dim:       '#5A5A75',
  success:   '#00E5A0',
  warning:   '#FFB800',
  danger:    '#FF6B6B',
  gradient:  'linear-gradient(135deg, #00F0FF 0%, #7000FF 100%)',
  gradientH: 'linear-gradient(90deg, #00F0FF 0%, #7000FF 100%)',
  font:      "'Inter', -apple-system, system-ui, sans-serif",
  mono:      "'JetBrains Mono', 'SF Mono', ui-monospace, monospace",
};
window.Z = Z;

// Standard phone screen dims used in the iOS frame minus chrome
const SCREEN_W = 402;
const SCREEN_H = 874;
window.SCREEN_W = SCREEN_W;
window.SCREEN_H = SCREEN_H;

// ─────────────────────────────────────────────────────────────
// Format helpers
// ─────────────────────────────────────────────────────────────
function fmtMoney(n, currency = 'USD') {
  const sym = { USD: '$', COP: '$', PEN: 'S/', MXN: '$', CLP: '$', ARS: '$' }[currency] || '$';
  return sym + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
window.fmtMoney = fmtMoney;
