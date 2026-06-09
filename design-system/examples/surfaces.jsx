// Zepo · surfaces & text — Card, GradientBorder, GradientText.
// The visual containers + gradient text fill used everywhere.

// GradientBorder — wraps content with a 1px cyan→purple gradient border.
// Implemented with padding + masked background for crisp 1px line.
function GradientBorder({ children, radius = 16, padding = 1, style = {}, glow = false }) {
  return (
    <div style={{
      borderRadius: radius, padding, background: Z.gradient,
      boxShadow: glow ? '0 0 32px rgba(0, 240, 255, 0.18), 0 0 64px rgba(112, 0, 255, 0.12)' : 'none',
      ...style,
    }}>
      <div style={{ borderRadius: radius - padding, background: Z.surface, height: '100%', width: '100%' }}>
        {children}
      </div>
    </div>
  );
}
window.GradientBorder = GradientBorder;

// Card — surface card with border
function Card({ children, style = {}, padded = true, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: Z.surface, border: `1px solid ${Z.border}`, borderRadius: 16,
      padding: padded ? 16 : 0, ...style,
    }}>
      {children}
    </div>
  );
}
window.Card = Card;

// GradientText — paints child text with the brand gradient
function GradientText({ children, style = {} }) {
  return (
    <span style={{
      background: Z.gradient, WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent', backgroundClip: 'text', ...style,
    }}>{children}</span>
  );
}
window.GradientText = GradientText;
