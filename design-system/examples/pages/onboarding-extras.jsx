// Zepo · pages/onboarding-extras.jsx
//   Presupuesto inicial + Método preferido.
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function BudgetSetupScreen() {
  return (
    <div style={{ padding: '24px 24px 32px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <ProgressDots step={2} total={3} />
      <div style={{ marginTop: 28, marginBottom: 20 }}>
        <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.7, lineHeight: 1.15, marginBottom: 6 }}>
          Tu presupuesto <GradientText>mensual</GradientText>
        </div>
        <div style={{ fontSize: 13, color: Z.muted, lineHeight: 1.4 }}>
          Cuánto planeas gastar en total este mes. Puedes ajustarlo cuando quieras.
        </div>
      </div>

      {/* Big amount */}
      <div style={{
        padding: '22px 18px', borderRadius: 18,
        background: 'linear-gradient(160deg, rgba(0,240,255,0.06), rgba(112,0,255,0.06))',
        border: `1px solid ${Z.cyan}`,
        boxShadow: '0 0 0 4px rgba(0,240,255,0.06)',
        textAlign: 'center', marginBottom: 18,
      }}>
        <div style={{ fontSize: 10, color: Z.muted, letterSpacing: 1.2, fontWeight: 700, marginBottom: 8 }}>LÍMITE MENSUAL</div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 4 }}>
          <span style={{ fontSize: 28, color: Z.muted, fontWeight: 600 }}>$</span>
          <span style={{ fontSize: 60, fontWeight: 800, letterSpacing: -2.6, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
            <GradientText>800</GradientText>
          </span>
        </div>
        <div style={{ marginTop: 8, fontSize: 12, color: Z.muted }}>USD · ≈ $26 / día</div>
      </div>

      {/* Quick presets */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 18 }}>
        {['$400', '$800', '$1,200', '$2,000'].map((p, i) => (
          <div key={p} style={{
            flex: 1, padding: '10px 0', textAlign: 'center', borderRadius: 10,
            background: i === 1 ? 'rgba(0,240,255,0.10)' : Z.surface,
            border: `1px solid ${i === 1 ? Z.cyan : Z.border}`,
            fontSize: 13, fontWeight: 700, color: i === 1 ? Z.text : Z.muted,
            fontVariantNumeric: 'tabular-nums',
          }}>{p}</div>
        ))}
      </div>

      {/* Mini numpad */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 18 }}>
        {['1','2','3','4','5','6','7','8','9','.','0','⌫'].map(k => (
          <div key={k} style={{
            height: 42, borderRadius: 10, background: Z.surface,
            border: `1px solid ${Z.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, fontWeight: 600, color: Z.text,
          }}>{k}</div>
        ))}
      </div>

      <div style={{ flex: 1 }} />
      <GradientButton>Continuar</GradientButton>
      <div style={{ textAlign: 'center', marginTop: 14 }}>
        <span style={{ fontSize: 12, color: Z.muted, textDecoration: 'underline' }}>Configurar después</span>
      </div>
    </div>
  );
}
window.BudgetSetupScreen = BudgetSetupScreen;

function MethodPickScreen() {
  const methods = [
    { k: 'text',  icon: 'edit',   l: 'Texto',  d: 'Escribe en lenguaje natural', selected: true },
    { k: 'voice', icon: 'mic',    l: 'Voz',    d: 'Habla y nosotros transcribimos', selected: false },
    { k: 'photo', icon: 'camera', l: 'Foto',   d: 'Captura el recibo, listo', selected: false },
  ];
  return (
    <div style={{ padding: '24px 24px 32px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <ProgressDots step={3} total={3} />
      <div style={{ marginTop: 28, marginBottom: 22 }}>
        <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.7, lineHeight: 1.15, marginBottom: 6 }}>
          ¿Cómo prefieres <GradientText>registrar?</GradientText>
        </div>
        <div style={{ fontSize: 13, color: Z.muted, lineHeight: 1.4 }}>
          Elige tu método favorito. Puedes usar los tres siempre que quieras.
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
        {methods.map(m => (
          <div key={m.k} style={{
            padding: '18px 16px', borderRadius: 16,
            background: m.selected ? 'linear-gradient(135deg, rgba(0,240,255,0.08), rgba(112,0,255,0.06))' : Z.surface,
            border: `1px solid ${m.selected ? Z.cyan : Z.border}`,
            boxShadow: m.selected ? '0 0 0 3px rgba(0,240,255,0.06)' : 'none',
            display: 'flex', alignItems: 'center', gap: 14, position: 'relative',
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: m.selected ? Z.gradient : Z.bg,
              border: m.selected ? 'none' : `1px solid ${Z.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: m.selected ? '0 0 16px rgba(0,240,255,0.25)' : 'none',
            }}>
              <Icon name={m.icon} size={22} color={m.selected ? '#0A0A0F' : Z.muted} strokeWidth={2.2} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: -0.3 }}>{m.l}</div>
              <div style={{ fontSize: 12, color: Z.muted, marginTop: 2 }}>{m.d}</div>
            </div>
            {m.selected && (
              <div style={{
                width: 22, height: 22, borderRadius: 11, background: Z.cyan,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon name="check" size={12} color="#0A0A0F" strokeWidth={3.5} />
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 18 }}>
        <GradientButton>Empezar</GradientButton>
      </div>
    </div>
  );
}
window.MethodPickScreen = MethodPickScreen;