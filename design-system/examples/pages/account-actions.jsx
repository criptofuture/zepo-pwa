// Zepo · pages/account-actions.jsx
//   Cambiar contraseña · Confirmar eliminación (modal).
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function DeleteAccountModal() {
  return (
    <div style={{ height: '100%', position: 'relative', overflow: 'hidden' }}>
      {/* Settings detrás, atenuado */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'rgba(10,10,15,0.85)',
        backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
      }} />
      <div style={{ position: 'absolute', top: 60, left: 20, right: 20, opacity: 0.15 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: -0.4, color: Z.text }}>Configuración</div>
        <div style={{ marginTop: 14, height: 50, borderRadius: 12, background: Z.surface, border: `1px solid ${Z.border}` }} />
        <div style={{ marginTop: 8, height: 50, borderRadius: 12, background: Z.surface, border: `1px solid ${Z.border}` }} />
        <div style={{ marginTop: 8, height: 50, borderRadius: 12, background: Z.surface, border: `1px solid ${Z.border}` }} />
      </div>

      {/* Card centrada */}
      <div style={{
        position: 'absolute', top: '50%', left: 20, right: 20,
        transform: 'translateY(-50%)',
        background: Z.surface, borderRadius: 22,
        border: `1px solid ${Z.border2}`,
        padding: '26px 22px 20px',
        boxShadow: '0 20px 80px rgba(255,107,107,0.18), 0 0 0 1px rgba(255,107,107,0.15)',
      }}>
        {/* Icono alerta */}
        <div style={{
          width: 64, height: 64, borderRadius: 18, margin: '0 auto 18px',
          background: 'linear-gradient(135deg, rgba(255,107,107,0.18), rgba(255,184,0,0.10))',
          border: `1px solid ${Z.danger}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 32px rgba(255,107,107,0.25)',
        }}>
          <Icon name="alert-triangle" size={30} color={Z.danger} strokeWidth={1.8} />
        </div>

        <div style={{
          fontSize: 22, fontWeight: 700, letterSpacing: -0.5, textAlign: 'center',
          marginBottom: 10, color: Z.text,
        }}>¿Eliminar tu cuenta?</div>
        <div style={{
          fontSize: 13, color: Z.muted, lineHeight: 1.55, textAlign: 'center',
          marginBottom: 18,
        }}>
          Se eliminarán todos tus datos permanentemente:
          <br/>
          <span style={{ color: Z.text, fontWeight: 600 }}>47 gastos · 8 cobros · 3 recibos</span>.
          <br/>
          Esta acción no se puede deshacer.
        </div>

        {/* Input ELIMINAR */}
        <div style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>
            ESCRIBE <span style={{ color: Z.danger, fontFamily: Z.mono }}>ELIMINAR</span> PARA CONFIRMAR
          </div>
          <div style={{
            height: 50, borderRadius: 12, background: Z.bg,
            border: `1px solid ${Z.border}`, padding: '0 14px',
            display: 'flex', alignItems: 'center',
            fontFamily: Z.mono, fontSize: 16, color: Z.dim, letterSpacing: 1.2,
          }}>
            <span style={{ color: Z.muted, opacity: 0.5 }}>ELIMINAR</span>
            <div style={{
              width: 1.5, height: 18, marginLeft: 2, background: Z.cyan,
            }} />
          </div>
        </div>

        {/* Botones */}
        <button style={{
          marginTop: 18, width: '100%', height: 50, borderRadius: 25,
          background: 'rgba(255,107,107,0.15)', border: `1px solid rgba(255,107,107,0.3)`,
          color: Z.danger, opacity: 0.55,
          fontWeight: 700, fontSize: 15, fontFamily: Z.font, letterSpacing: -0.1,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        }}>
          <Icon name="trash" size={15} color={Z.danger} strokeWidth={2.2} />
          Eliminar mi cuenta
        </button>
        <button style={{
          marginTop: 8, width: '100%', height: 46, borderRadius: 23,
          background: 'transparent', border: 'none',
          color: Z.muted, fontWeight: 600, fontSize: 14, fontFamily: Z.font,
        }}>Cancelar</button>
      </div>
    </div>
  );
}
window.DeleteAccountModal = DeleteAccountModal;

// ═══════════════════════════════════════════════════════════════════
// 3 · CAMBIAR CONTRASEÑA
// ═══════════════════════════════════════════════════════════════════

function ChangePasswordScreen() {
  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 60 }}>
      <ScreenHeader title="Cambiar contraseña" />

      <div style={{ padding: '0 24px' }}>
        {/* Hint icon */}
        <div style={{
          width: 56, height: 56, borderRadius: 16,
          background: 'rgba(0,240,255,0.08)', border: `1px solid ${Z.cyan}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 16,
          boxShadow: '0 0 24px rgba(0,240,255,0.12)',
        }}>
          <Icon name="lock" size={24} color={Z.cyan} strokeWidth={1.8} />
        </div>

        <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.5, marginBottom: 22 }}>
          Para tu seguridad, ingresa tu contraseña actual antes de definir una nueva.
        </div>

        <PasswordField label="CONTRASEÑA ACTUAL" value="••••••••" />
        <PasswordField label="NUEVA CONTRASEÑA" value="••••••••••" />
        <PasswordField label="CONFIRMAR NUEVA CONTRASEÑA" value="••••••••••" />

        {/* Strength meter */}
        <div style={{ marginTop: -6, marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, display: 'flex', gap: 3 }}>
              {[1,2,3,4].map(i => (
                <div key={i} style={{
                  flex: 1, height: 4, borderRadius: 2,
                  background: i <= 3 ? Z.success : Z.border,
                }} />
              ))}
            </div>
            <span style={{ fontSize: 11, color: Z.success, fontWeight: 700, letterSpacing: 0.4 }}>FUERTE</span>
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: Z.muted, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="check" size={11} color={Z.success} strokeWidth={3} />
            Mínimo 8 caracteres · al menos 1 número
          </div>
        </div>

        <div style={{ marginTop: 26 }}>
          <GradientButton>Actualizar contraseña</GradientButton>
        </div>

        <div style={{ marginTop: 18, textAlign: 'center' }}>
          <span style={{ fontSize: 12, color: Z.cyan, fontWeight: 600 }}>¿Olvidaste la actual?</span>
        </div>
      </div>
    </div>
  );
}

// PasswordField moved to components/forms.jsx — used here as a window-global.
window.ChangePasswordScreen = ChangePasswordScreen;