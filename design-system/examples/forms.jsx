// Zepo · form bits — the inputs that show up across several pages.
//   - FieldBox      → labelled "read-only" field with optional edit icon
//                     (Aprobar, Editar gasto, Nuevo cobro)
//   - PasswordField → masked password row (Cambiar contraseña)
//   - Field         → onboarding input row with placeholder + icon

function FieldBox({ label, value, mono, big, right, color, onIcon, multiline, sub }) {
  return (
    <div style={{ marginBottom: 12 }}>
      {label && (
        <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>{label}</div>
      )}
      <div style={{
        minHeight: big ? 64 : 50, borderRadius: 12, background: Z.surface,
        border: `1px solid ${Z.border}`, padding: multiline ? '12px 14px' : '0 14px',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{
          flex: 1, color: color || Z.text,
          fontSize: big ? 28 : 15, fontWeight: big ? 700 : 500,
          letterSpacing: big ? -0.6 : 0,
          fontFamily: mono ? Z.mono : Z.font,
          fontVariantNumeric: big ? 'tabular-nums' : 'normal',
        }}>
          {value}
          {sub && <div style={{ fontSize: 11, color: Z.muted, fontWeight: 400, marginTop: 2 }}>{sub}</div>}
        </div>
        {right}
        {onIcon && <Icon name={onIcon} size={16} color={Z.muted} />}
      </div>
    </div>
  );
}
window.FieldBox = FieldBox;

function PasswordField({ label, value }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>{label}</div>
      <div style={{
        height: 52, borderRadius: 12, background: Z.surface,
        border: `1px solid ${Z.border}`, padding: '0 14px',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <Icon name="lock" size={15} color={Z.muted} />
        <div style={{
          flex: 1, fontSize: 16, color: Z.text, fontFamily: Z.mono, letterSpacing: 3,
        }}>{value}</div>
        <div style={{
          width: 32, height: 32, borderRadius: 10,
          background: Z.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name="eye-off" size={14} color={Z.muted} />
        </div>
      </div>
    </div>
  );
}
window.PasswordField = PasswordField;

// Onboarding input — placeholder + value + optional right icon
function Field({ label, placeholder, iconName, type }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 12, color: Z.muted, marginBottom: 6, fontWeight: 500 }}>{label}</div>
      <div style={{
        height: 50, borderRadius: 12, background: Z.surface,
        border: `1px solid ${Z.border}`,
        display: 'flex', alignItems: 'center', padding: '0 14px',
      }}>
        <input style={{
          flex: 1, background: 'transparent', border: 'none', outline: 'none',
          color: type ? Z.text : Z.dim, fontFamily: Z.font, fontSize: 15,
        }} value={type || placeholder} readOnly />
        {iconName && <Icon name={iconName} size={18} color={Z.muted} />}
      </div>
    </div>
  );
}
window.Field = Field;
