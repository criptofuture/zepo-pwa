// Zepo onboarding screens — splash, auth, currency, plan, first expense.
// Each is a fixed-size component sized to fill PhoneShell's content area.

const ONB_W = window.SCREEN_W;
const ONB_H = window.SCREEN_H;

// ─── Splash ──────────────────────────────────────────────────
function SplashScreen() {
  return (
    <div style={{
      width: '100%', height: '100%', position: 'relative', overflow: 'hidden',
      background: '#0A0A0F',
    }}>
      {/* radial gradient halo */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        width: 600, height: 600, transform: 'translate(-50%, -50%)',
        background: 'radial-gradient(circle, rgba(0,240,255,0.25) 0%, rgba(112,0,255,0.18) 35%, transparent 65%)',
        filter: 'blur(40px)',
      }} />
      {/* logo */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18,
      }}>
        <ZepoLogo size={84} />
        <div style={{
          fontFamily: Z.font, fontSize: 56, fontWeight: 800,
          letterSpacing: -2, lineHeight: 1, color: Z.text,
        }}>
          <GradientText>zepo</GradientText>
        </div>
        <div style={{ color: Z.muted, fontSize: 14, letterSpacing: 0.3, fontWeight: 500 }}>
          Tu dinero, claro.
        </div>
      </div>
      {/* dots indicator */}
      <div style={{
        position: 'absolute', bottom: 80, left: 0, right: 0,
        display: 'flex', gap: 6, justifyContent: 'center',
      }}>
        {[0,1,2].map(i => (
          <div key={i} style={{
            width: 6, height: 6, borderRadius: 3,
            background: i === 1 ? Z.cyan : '#2a2a3d',
          }} />
        ))}
      </div>
    </div>
  );
}

// NOTE: ZepoLogo moved to components/brand.jsx — Field moved to components/forms.jsx.
//       Both are window-globals so the screens below pick them up automatically.

// ─── Auth ────────────────────────────────────────────────────
function AuthScreen() {
  return (
    <div style={{ padding: '32px 24px 0', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
        <ZepoLogo size={36} />
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: -0.5 }}>zepo</div>
      </div>

      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 32, fontWeight: 700, letterSpacing: -1, lineHeight: 1.1, marginBottom: 8 }}>
          Crea tu cuenta
        </div>
        <div style={{ color: Z.muted, fontSize: 15 }}>
          Tu memoria financiera, en 30 segundos.
        </div>
      </div>

      {/* tabs */}
      <div style={{
        display: 'flex', background: Z.surface, borderRadius: 12,
        padding: 4, marginBottom: 24, border: `1px solid ${Z.border}`,
      }}>
        <div style={{
          flex: 1, padding: '10px 0', textAlign: 'center', borderRadius: 9,
          background: Z.bg, color: Z.text, fontWeight: 600, fontSize: 14,
        }}>Crear cuenta</div>
        <div style={{
          flex: 1, padding: '10px 0', textAlign: 'center', color: Z.muted,
          fontWeight: 500, fontSize: 14,
        }}>Ya tengo cuenta</div>
      </div>

      {/* OAuth buttons */}
      <button style={{
        width: '100%', height: 52, borderRadius: 14,
        background: Z.surface, border: `1px solid ${Z.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
        color: Z.text, fontWeight: 600, fontSize: 15, marginBottom: 10,
      }}>
        <Icon name="google" size={20} />
        Continuar con Google
      </button>
      <button style={{
        width: '100%', height: 52, borderRadius: 14,
        background: Z.surface, border: `1px solid ${Z.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
        color: Z.text, fontWeight: 600, fontSize: 15, marginBottom: 24,
      }}>
        <Icon name="apple" size={20} color={Z.text} />
        Continuar con Apple
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <div style={{ flex: 1, height: 1, background: Z.border }} />
        <span style={{ color: Z.muted, fontSize: 12, letterSpacing: 1 }}>O CON EMAIL</span>
        <div style={{ flex: 1, height: 1, background: Z.border }} />
      </div>

      <Field label="Nombre completo" placeholder="Andrea Salazar" />
      <Field label="Email" placeholder="andrea@ejemplo.com" iconName="mail" />
      <Field label="Contraseña" placeholder="Mínimo 8 caracteres" iconName="eye-off" type="••••••••••" />

      <div style={{ marginTop: 'auto', paddingTop: 16 }}>
        <GradientButton>Crear cuenta</GradientButton>
        <div style={{ textAlign: 'center', color: Z.dim, fontSize: 12, marginTop: 16 }}>
          Al continuar aceptas nuestros <span style={{ color: Z.muted, textDecoration: 'underline' }}>Términos</span>
        </div>
      </div>
    </div>
  );
}

// NOTE: Field moved to components/forms.jsx — it's a window-global so the
//       Auth / Login / SignUp / Forgot screens pick it up automatically.



// ─── Welcome + Currency (combined since spec is small) ──────
function WelcomeScreen() {
  return (
    <div style={{ padding: '24px 24px 32px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <ProgressDots step={1} total={3} />
      <div style={{ marginTop: 32, marginBottom: 40 }}>
        <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.8, lineHeight: 1.15, marginBottom: 12 }}>
          Hola, <GradientText>Andrea</GradientText>.
        </div>
        <div style={{ fontSize: 16, color: Z.muted, lineHeight: 1.4 }}>
          Vamos a configurar Zepo en 2 pasos.
        </div>
      </div>

      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 12, color: Z.muted, marginBottom: 8, fontWeight: 500, letterSpacing: 0.3 }}>
          NOMBRE EN LA APP
        </div>
        <div style={{
          height: 60, borderRadius: 14, background: Z.surface,
          border: `1px solid ${Z.cyan}`, padding: '0 18px',
          display: 'flex', alignItems: 'center',
          boxShadow: '0 0 0 4px rgba(0,240,255,0.08)',
        }}>
          <input style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            color: Z.text, fontFamily: Z.font, fontSize: 20, fontWeight: 600, letterSpacing: -0.4,
          }} value="Andrea" readOnly />
          <Icon name="edit" size={18} color={Z.muted} />
        </div>
        <div style={{ fontSize: 12, color: Z.dim, marginTop: 8 }}>
          Puedes editarlo cuando quieras desde Perfil.
        </div>
      </div>

      <div style={{ flex: 1 }} />

      <GradientButton>Continuar</GradientButton>
    </div>
  );
}

function CurrencyScreen() {
  const cur = [
    { code: 'USD', flag: '🇪🇨', name: 'Dólar', country: 'Ecuador', selected: true },
    { code: 'COP', flag: '🇨🇴', name: 'Peso',  country: 'Colombia' },
    { code: 'PEN', flag: '🇵🇪', name: 'Sol',   country: 'Perú' },
    { code: 'MXN', flag: '🇲🇽', name: 'Peso',  country: 'México' },
    { code: 'CLP', flag: '🇨🇱', name: 'Peso',  country: 'Chile' },
    { code: 'ARS', flag: '🇦🇷', name: 'Peso',  country: 'Argentina' },
  ];
  return (
    <div style={{ padding: '24px 24px 32px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <ProgressDots step={2} total={3} />
      <div style={{ marginTop: 32, marginBottom: 28 }}>
        <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.8, lineHeight: 1.15, marginBottom: 8 }}>
          Tu moneda principal
        </div>
        <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.4 }}>
          Es la moneda en que registrarás la mayoría de gastos.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {cur.map(c => (
          <div key={c.code} style={{
            padding: '14px 14px', borderRadius: 14,
            background: c.selected ? 'linear-gradient(135deg, rgba(0,240,255,0.08), rgba(112,0,255,0.08))' : Z.surface,
            border: `1px solid ${c.selected ? Z.cyan : Z.border}`,
            position: 'relative',
          }}>
            <div style={{ fontSize: 28, marginBottom: 4 }}>{c.flag}</div>
            <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: -0.3, color: Z.text }}>
              {c.code}
            </div>
            <div style={{ fontSize: 11, color: Z.muted }}>{c.country}</div>
            {c.selected && (
              <div style={{
                position: 'absolute', top: 10, right: 10,
                width: 18, height: 18, borderRadius: 9, background: Z.cyan,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon name="check" size={11} color="#0A0A0F" strokeWidth={3.5} />
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 20, padding: '12px 14px', borderRadius: 10, background: 'rgba(0,240,255,0.06)', border: `1px solid rgba(0,240,255,0.15)`, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <Icon name="sparkles" size={14} color={Z.cyan} />
        <div style={{ fontSize: 12, color: Z.muted, lineHeight: 1.45 }}>
          Puedes agregar más monedas con el plan <span style={{ color: Z.cyan, fontWeight: 600 }}>Pro</span> o <span style={{ color: Z.cyan, fontWeight: 600 }}>Elite</span>.
        </div>
      </div>

      <div style={{ flex: 1 }} />
      <GradientButton>Continuar</GradientButton>
    </div>
  );
}

function ProgressDots({ step, total }) {
  return (
    <div style={{ display: 'flex', gap: 6 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{
          flex: 1, height: 4, borderRadius: 2,
          background: i < step ? Z.gradient : Z.border,
        }} />
      ))}
    </div>
  );
}

// ─── Plan picker ────────────────────────────────────────────
function PlanScreen() {
  return (
    <div style={{ padding: '24px 20px 32px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <ProgressDots step={3} total={3} />
      <div style={{ marginTop: 24, marginBottom: 20 }}>
        <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.7, lineHeight: 1.15, marginBottom: 6 }}>
          Elige tu plan
        </div>
        <div style={{ fontSize: 13, color: Z.muted }}>
          Empieza gratis. Mejora cuando quieras.
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <PlanCard
          name="Free"
          price="$0"
          tagline="Para empezar"
          warning="Solo hasta 31 dic 2026"
          bullets={['Entrada manual', 'Historial de 1 mes', '6 categorías fijas']}
        />
        <PlanCard
          name="Pro"
          price="$5"
          tagline="Más popular"
          highlight
          bullets={['IA · texto + voz', 'Historial ilimitado', 'Multi-moneda LATAM']}
        />
        <PlanCard
          name="Elite"
          price="$10"
          tagline="Completo"
          gradient
          bullets={['Foto de recibo + OCR', 'Dashboard con gráficos', 'Sync Gmail + Sheets']}
        />
      </div>

      <div style={{ flex: 1 }} />
      <div style={{ marginTop: 20 }}>
        <GradientButton>Empezar gratis</GradientButton>
        <div style={{ textAlign: 'center', marginTop: 14 }}>
          <span style={{ fontSize: 13, color: Z.muted, textDecoration: 'underline' }}>
            Comparar todos los planes
          </span>
        </div>
      </div>
    </div>
  );
}

function PlanCard({ name, price, tagline, warning, highlight, gradient, bullets }) {
  const inner = (
    <div style={{ padding: 16, position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: -0.3 }}>{name}</span>
          <span style={{ fontSize: 22, fontWeight: 700, letterSpacing: -1 }}>{price}</span>
          <span style={{ fontSize: 12, color: Z.muted }}>/mes</span>
        </div>
        {warning ? (
          <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 7px', borderRadius: 5, background: '#FFB80020', color: Z.warning, letterSpacing: 0.4 }}>
            HASTA 31 DIC
          </span>
        ) : highlight ? (
          <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 7px', borderRadius: 5, background: '#00F0FF18', color: Z.cyan, letterSpacing: 0.4 }}>
            MÁS POPULAR
          </span>
        ) : (
          <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 7px', borderRadius: 5, background: 'rgba(112,0,255,0.18)', color: '#B794F6', letterSpacing: 0.4 }}>
            COMPLETO
          </span>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {bullets.map((b, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: Z.muted }}>
            <Icon name="check" size={12} color={Z.cyan} strokeWidth={2.6} />
            {b}
          </div>
        ))}
      </div>
    </div>
  );
  if (gradient) {
    return (
      <GradientBorder radius={16} padding={1}>
        <div style={{
          background: 'linear-gradient(135deg, rgba(0,240,255,0.05), rgba(112,0,255,0.06))',
          borderRadius: 15,
        }}>{inner}</div>
      </GradientBorder>
    );
  }
  return (
    <div style={{
      background: Z.surface, borderRadius: 16,
      border: `1px solid ${highlight ? Z.cyan : Z.border}`,
      boxShadow: highlight ? '0 0 0 3px rgba(0,240,255,0.08)' : 'none',
    }}>{inner}</div>
  );
}
window.PlanCard = PlanCard;

// ─── First expense (numpad-driven) ───────────────────────────
function FirstExpenseScreen() {
  return (
    <div style={{ padding: '24px 24px 32px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 4, fontSize: 13, color: Z.muted, fontWeight: 500 }}>
        Último paso
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.6, lineHeight: 1.2, marginBottom: 28 }}>
        Tu primer gasto.
      </div>

      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        <div style={{
          fontFamily: Z.font, fontSize: 64, fontWeight: 800,
          letterSpacing: -3, lineHeight: 1, color: Z.text,
        }}>
          <span style={{ fontSize: 36, color: Z.muted, fontWeight: 600, verticalAlign: 8, marginRight: 4 }}>$</span>
          <GradientText>12.50</GradientText>
        </div>
        <div style={{ marginTop: 8, fontSize: 13, color: Z.muted }}>
          USD · Hoy, jueves
        </div>
      </div>

      <div style={{
        height: 48, borderRadius: 12, background: Z.surface,
        border: `1px solid ${Z.border}`, padding: '0 14px',
        display: 'flex', alignItems: 'center', marginBottom: 16,
      }}>
        <input style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: Z.text, fontSize: 14 }} value="Almuerzo en La Tablita" readOnly />
      </div>

      {/* category chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
        {[['food', true], ['transport', false], ['health', false], ['fun', false], ['shop', false], ['other', false]].map(([k, sel]) => {
          const c = CATEGORIES[k];
          return (
            <div key={k} style={{
              padding: '8px 12px', borderRadius: 10, fontSize: 12,
              background: sel ? `${c.color}18` : Z.surface,
              border: `1px solid ${sel ? c.color : Z.border}`,
              color: sel ? Z.text : Z.muted, fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <span>{c.emoji}</span>{c.label}
            </div>
          );
        })}
      </div>

      {/* mini numpad preview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 16 }}>
        {['1','2','3','4','5','6','7','8','9','.','0','⌫'].map(k => (
          <div key={k} style={{
            height: 38, borderRadius: 10, background: Z.surface,
            border: `1px solid ${Z.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, fontWeight: 600, color: Z.text,
          }}>{k}</div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 10 }}>
        <button style={{
          height: 50, padding: '0 20px', borderRadius: 25,
          background: 'transparent', border: `1px solid ${Z.border}`,
          color: Z.muted, fontWeight: 600, fontSize: 14,
        }}>Saltar</button>
        <div style={{ flex: 1 }}>
          <GradientButton height={50}>Guardar gasto</GradientButton>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SplashScreen, AuthScreen, WelcomeScreen, CurrencyScreen, PlanScreen, FirstExpenseScreen });
