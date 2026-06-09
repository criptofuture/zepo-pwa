// Zepo · buttons — gradient CTA + small icon button + page-level back header.
// Anything that's tappable and shared across screens lives here.

function GradientButton({ children, full = true, height = 52, style = {}, onClick }) {
  return (
    <button onClick={onClick} style={{
      width: full ? '100%' : 'auto', height,
      borderRadius: height / 2, border: 'none',
      background: Z.gradient, color: '#0A0A0F',
      fontFamily: Z.font, fontWeight: 700, fontSize: 16, letterSpacing: -0.2,
      cursor: 'pointer', padding: full ? 0 : '0 24px',
      boxShadow: '0 4px 24px rgba(0, 240, 255, 0.25), inset 0 1px 0 rgba(255,255,255,0.3)',
      ...style,
    }}>{children}</button>
  );
}
window.GradientButton = GradientButton;

function HeaderIconButton({ icon, unread = false, onClick }) {
  return (
    <div onClick={onClick} style={{
      width: 40, height: 40, borderRadius: 20,
      background: Z.surface, border: `1px solid ${Z.border}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      position: 'relative', cursor: 'pointer', flexShrink: 0,
    }}>
      <Icon name={icon} size={18} color={Z.text} />
      {unread && (
        <div style={{
          position: 'absolute', top: 8, right: 8,
          width: 7, height: 7, borderRadius: 4, background: Z.cyan,
          boxShadow: '0 0 6px rgba(0,240,255,0.8)',
        }} />
      )}
    </div>
  );
}
window.HeaderIconButton = HeaderIconButton;

// ScreenHeader — back-arrow + title + optional right slot.
// Used on standalone (non-tab) screens like Settings, Aprobar, Editar gasto…
function ScreenHeader({ title, onBack = true, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px 12px' }}>
      {onBack && (
        <div style={{
          width: 36, height: 36, borderRadius: 18, background: Z.surface,
          border: `1px solid ${Z.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name="chevron-left" size={18} color={Z.text} />
        </div>
      )}
      <div style={{ flex: 1, fontSize: 20, fontWeight: 700, letterSpacing: -0.4 }}>{title}</div>
      {right}
    </div>
  );
}
window.ScreenHeader = ScreenHeader;
