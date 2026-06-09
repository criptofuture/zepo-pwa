// Zepo · brand mark. Cyan→purple rounded square with a stylised "z" stroke.
// One component so any page that needs the logo gets the same proportions.

function ZepoLogo({ size = 64 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: size * 0.28,
      background: Z.gradient, position: 'relative', overflow: 'hidden',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 0 32px rgba(0,240,255,0.4), inset 0 1px 0 rgba(255,255,255,0.4)',
    }}>
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 32 32" fill="none">
        <path d="M6 8h20L8 24h20" stroke="#0A0A0F" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
  );
}
window.ZepoLogo = ZepoLogo;
