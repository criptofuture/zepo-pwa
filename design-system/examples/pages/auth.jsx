// Zepo · pages/auth.jsx
//   Login · SignUp · Olvidé mi contraseña (2 estados).
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function LoginScreen() {
  return (
    <div style={{ padding: '32px 24px 0', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
        <ZepoLogo size={36} />
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: -0.5 }}>zepo</div>
      </div>

      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 32, fontWeight: 700, letterSpacing: -1, lineHeight: 1.1, marginBottom: 8 }}>
          Bienvenido <GradientText>de nuevo</GradientText>
        </div>
        <div style={{ color: Z.muted, fontSize: 15 }}>
          Inicia sesión para continuar.
        </div>
      </div>

      <Field label="Email" placeholder="andrea@ejemplo.com" iconName="mail" type="andrea@ejemplo.com" />
      <Field label="Contraseña" placeholder="Tu contraseña" iconName="eye-off" type="••••••••••" />

      <GradientButton>Iniciar sesión</GradientButton>

      {/* Forgot password link */}
      <div style={{ textAlign: 'center', marginTop: 16 }}>
        <span style={{ fontSize: 13, color: Z.cyan, fontWeight: 600, textDecoration: 'underline' }}>
          Olvidé mi contraseña
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 28, marginBottom: 18 }}>
        <div style={{ flex: 1, height: 1, background: Z.border }} />
        <span style={{ color: Z.muted, fontSize: 12, letterSpacing: 1 }}>O CONTINÚA CON</span>
        <div style={{ flex: 1, height: 1, background: Z.border }} />
      </div>

      <div style={{ display: 'flex', gap: 10 }}>
        <button style={{
          flex: 1, height: 50, borderRadius: 14,
          background: Z.surface, border: `1px solid ${Z.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          color: Z.text, fontWeight: 600, fontSize: 13,
        }}>
          <Icon name="google" size={18} /> Google
        </button>
        <button style={{
          flex: 1, height: 50, borderRadius: 14,
          background: Z.surface, border: `1px solid ${Z.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          color: Z.text, fontWeight: 600, fontSize: 13,
        }}>
          <Icon name="apple" size={18} color={Z.text} /> Apple
        </button>
      </div>

      <div style={{ marginTop: 'auto', paddingTop: 20, paddingBottom: 14, textAlign: 'center', color: Z.muted, fontSize: 13 }}>
        ¿No tienes cuenta? <span style={{ color: Z.cyan, fontWeight: 600 }}>Regístrate</span>
      </div>
    </div>
  );
}
window.LoginScreen = LoginScreen;

function ForgotPasswordScreen() {
  return (
    <div style={{ padding: '14px 24px 32px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 18, background: Z.surface,
          border: `1px solid ${Z.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name="chevron-left" size={18} color={Z.text} />
        </div>
      </div>

      <div style={{
        width: 64, height: 64, borderRadius: 18,
        background: 'rgba(0,240,255,0.08)', border: `1px solid ${Z.cyan}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 22,
        boxShadow: '0 0 24px rgba(0,240,255,0.15)',
      }}>
        <Icon name="lock" size={28} color={Z.cyan} strokeWidth={1.8} />
      </div>

      <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.8, lineHeight: 1.15, marginBottom: 10 }}>
        ¿Olvidaste tu <GradientText>contraseña?</GradientText>
      </div>
      <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.5, marginBottom: 28 }}>
        Ingresa el email de tu cuenta y te enviaremos un enlace para crear una nueva.
      </div>

      <Field label="Email" placeholder="tu@email.com" iconName="mail" type="andrea@ejemplo.com" />

      <GradientButton>Enviar enlace de recuperación</GradientButton>

      <div style={{ flex: 1 }} />
      <div style={{ textAlign: 'center', color: Z.muted, fontSize: 13 }}>
        ¿Te acordaste? <span style={{ color: Z.cyan, fontWeight: 600 }}>Inicia sesión</span>
      </div>
    </div>
  );
}
window.ForgotPasswordScreen = ForgotPasswordScreen;

function ForgotConfirmScreen() {
  return (
    <div style={{
      padding: '60px 28px 32px', height: '100%',
      display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
      background: 'radial-gradient(circle at 50% 25%, rgba(0,240,255,0.10) 0%, transparent 55%)',
    }}>
      <div style={{
        width: 100, height: 100, borderRadius: 28,
        background: 'linear-gradient(135deg, rgba(0,240,255,0.15), rgba(112,0,255,0.15))',
        border: `1px solid ${Z.cyan}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 28,
        boxShadow: '0 0 48px rgba(0,240,255,0.25)',
      }}>
        <Icon name="mail" size={42} color={Z.cyan} strokeWidth={1.8} />
      </div>

      <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.7, lineHeight: 1.15, marginBottom: 12 }}>
        Revisa tu <GradientText>correo</GradientText>
      </div>
      <div style={{ fontSize: 15, color: Z.muted, lineHeight: 1.55, marginBottom: 20, maxWidth: 320 }}>
        Te enviamos un enlace para restablecer tu contraseña a
      </div>
      <div style={{
        padding: '8px 14px', borderRadius: 10,
        background: Z.surface, border: `1px solid ${Z.border}`,
        fontSize: 14, fontWeight: 600, color: Z.text, fontFamily: Z.mono,
        marginBottom: 28,
      }}>andrea@ejemplo.com</div>

      <div style={{
        width: '100%', padding: '12px 14px', borderRadius: 12,
        background: 'rgba(0,240,255,0.06)', border: `1px solid rgba(0,240,255,0.18)`,
        display: 'flex', gap: 10, alignItems: 'flex-start', textAlign: 'left',
        marginBottom: 22,
      }}>
        <Icon name="clock" size={14} color={Z.cyan} />
        <div style={{ fontSize: 12, color: Z.muted, lineHeight: 1.5 }}>
          El enlace expira en 30 minutos. Si no lo ves, revisa tu carpeta de spam.
        </div>
      </div>

      <div style={{ flex: 1 }} />
      <div style={{ width: '100%' }}>
        <GradientButton>Volver al login</GradientButton>
        <button style={{
          marginTop: 10, width: '100%', height: 46, borderRadius: 23,
          background: 'transparent', border: 'none',
          color: Z.cyan, fontWeight: 600, fontSize: 13, fontFamily: Z.font,
        }}>Reenviar enlace</button>
      </div>
    </div>
  );
}
window.ForgotConfirmScreen = ForgotConfirmScreen;

// SignUp screen (explicit con email)
function SignUpScreen() {
  return (
    <div style={{ padding: '32px 24px 0', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
        <ZepoLogo size={36} />
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: -0.5 }}>zepo</div>
      </div>

      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: -1, lineHeight: 1.1, marginBottom: 8 }}>
          Crea tu cuenta
        </div>
        <div style={{ color: Z.muted, fontSize: 14 }}>
          Tres campos y empezamos.
        </div>
      </div>

      <Field label="Nombre completo" placeholder="Andrea Salazar" type="Andrea Salazar" />
      <Field label="Email" placeholder="andrea@ejemplo.com" iconName="mail" type="andrea@ejemplo.com" />
      <Field label="Contraseña" placeholder="Mínimo 8 caracteres" iconName="eye-off" type="••••••••••" />

      {/* password strength */}
      <div style={{ marginTop: -4, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: Z.border, overflow: 'hidden' }}>
          <div style={{ width: '70%', height: '100%', background: Z.success }} />
        </div>
        <span style={{ fontSize: 11, color: Z.success, fontWeight: 600 }}>Buena</span>
      </div>

      <GradientButton>Crear cuenta</GradientButton>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 20, marginBottom: 14 }}>
        <div style={{ flex: 1, height: 1, background: Z.border }} />
        <span style={{ color: Z.muted, fontSize: 12, letterSpacing: 1 }}>O</span>
        <div style={{ flex: 1, height: 1, background: Z.border }} />
      </div>

      <div style={{ display: 'flex', gap: 10 }}>
        <button style={{
          flex: 1, height: 48, borderRadius: 14,
          background: Z.surface, border: `1px solid ${Z.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          color: Z.text, fontWeight: 600, fontSize: 13,
        }}>
          <Icon name="google" size={18} /> Google
        </button>
        <button style={{
          flex: 1, height: 48, borderRadius: 14,
          background: Z.surface, border: `1px solid ${Z.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          color: Z.text, fontWeight: 600, fontSize: 13,
        }}>
          <Icon name="apple" size={18} color={Z.text} /> Apple
        </button>
      </div>

      <div style={{ marginTop: 'auto', paddingTop: 18, paddingBottom: 14, textAlign: 'center', color: Z.dim, fontSize: 12 }}>
        Al continuar aceptas nuestros <span style={{ color: Z.muted, textDecoration: 'underline' }}>Términos</span> y <span style={{ color: Z.muted, textDecoration: 'underline' }}>Privacidad</span>
      </div>
    </div>
  );
}
window.SignUpScreen = SignUpScreen;