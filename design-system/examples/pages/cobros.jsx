// Zepo · pages/cobros.jsx
//   Listado de cobros + Nuevo cobro (sheet).
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function CobrosScreen() {
  const cobros = [
    { n: 'Juan Pérez',     a: 7.50,  d: 'Almuerzo',         t: 'hace 2h',   s: 'pending', auto: true },
    { n: 'María González', a: 4.00,  d: 'Taxi compartido',  t: 'hace 1d',   s: 'pending', auto: true },
    { n: 'Pedro Vargas',   a: 4.00,  d: 'Taxi compartido',  t: 'hace 1d',   s: 'pending', auto: true },
    { n: 'Sofía López',    a: 22.50, d: 'Cena Da Mario',    t: 'hace 3d',   s: 'pending', auto: false },
    { n: 'Diego Romero',   a: 15.00, d: 'Entradas cine',    t: 'hace 5d',   s: 'paid',   auto: false },
    { n: 'Camila Ríos',    a: 8.75,  d: 'Café Tribu',       t: 'la sem.',   s: 'paid',   auto: true },
  ];
  const pending = cobros.filter(c => c.s === 'pending');
  const paid    = cobros.filter(c => c.s === 'paid');
  const totalPend = pending.reduce((s, c) => s + c.a, 0);

  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 110 }}>
      <div style={{ padding: '14px 20px 0' }}>
        <PageHeader title="Cobros" subtitle="Te deben dinero" />

        {/* Hero: total pendiente */}
        <GradientBorder radius={16} padding={1}>
          <div style={{ padding: 18 }}>
            <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600 }}>TE DEBEN</div>
            <div style={{ marginTop: 4, display: 'flex', alignItems: 'baseline', gap: 4 }}>
              <span style={{ fontSize: 22, color: Z.muted, fontWeight: 600 }}>$</span>
              <span style={{ fontSize: 44, fontWeight: 800, letterSpacing: -2, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
                <GradientText>{totalPend.toFixed(2)}</GradientText>
              </span>
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 10, fontSize: 12, color: Z.muted }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: 3, background: Z.warning }} />
                {pending.length} pendientes
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: 3, background: Z.success }} />
                {paid.length} cobrados
              </div>
            </div>
          </div>
        </GradientBorder>

        {/* Nuevo cobro CTA */}
        <button style={{
          marginTop: 14, width: '100%', height: 48, borderRadius: 14,
          background: Z.surface, border: `1px dashed ${Z.cyan}`,
          color: Z.cyan, fontWeight: 700, fontSize: 14, fontFamily: Z.font,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        }}>
          <Icon name="plus" size={16} color={Z.cyan} /> Nuevo cobro
        </button>

        {/* Pendientes */}
        <div style={{ marginTop: 22 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1.4, fontWeight: 700, marginBottom: 8, paddingLeft: 4 }}>
            PENDIENTES · {pending.length}
          </div>
          <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, overflow: 'hidden' }}>
            {pending.map((c, i) => (
              <CobroRow key={i} c={c} last={i === pending.length - 1} />
            ))}
          </div>
        </div>

        {/* Cobrados */}
        <div style={{ marginTop: 20 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1.4, fontWeight: 700, marginBottom: 8, paddingLeft: 4 }}>
            COBRADOS
          </div>
          <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, overflow: 'hidden', opacity: 0.85 }}>
            {paid.map((c, i) => (
              <CobroRow key={i} c={c} last={i === paid.length - 1} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function CobroRow({ c, last }) {
  const initial = c.n[0];
  const isPaid = c.s === 'paid';
  return (
    <div style={{
      padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12,
      borderBottom: last ? 'none' : `1px solid ${Z.border}`,
      position: 'relative',
    }}>
      {/* Swipe hint en pendientes */}
      {!isPaid && (
        <div style={{
          position: 'absolute', right: 0, top: 0, bottom: 0, width: 6,
          background: 'linear-gradient(90deg, transparent, rgba(0,229,160,0.2))',
          borderTopRightRadius: last ? 13 : 0, borderBottomRightRadius: last ? 13 : 0,
        }} />
      )}
      <div style={{
        width: 38, height: 38, borderRadius: 19,
        background: isPaid ? Z.bg : Z.gradient,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 14, fontWeight: 800, color: isPaid ? Z.muted : '#0A0A0F',
        border: isPaid ? `1px solid ${Z.border}` : 'none',
        textDecoration: isPaid ? 'line-through' : 'none',
      }}>{initial}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: isPaid ? Z.muted : Z.text }}>
          {c.n}
          {c.auto && !isPaid && (
            <span style={{
              marginLeft: 6, fontSize: 9, padding: '1px 5px', borderRadius: 4,
              background: 'rgba(112,0,255,0.18)', color: '#B794F6', fontWeight: 700, letterSpacing: 0.4,
              verticalAlign: 1,
            }}>AUTO</span>
          )}
        </div>
        <div style={{ fontSize: 11, color: Z.muted, marginTop: 2 }}>{c.d} · {c.t}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontSize: 16, fontWeight: 700, letterSpacing: -0.3,
          color: isPaid ? Z.muted : Z.text,
          fontVariantNumeric: 'tabular-nums',
          textDecoration: isPaid ? 'line-through' : 'none',
        }}>${c.a.toFixed(2)}</div>
        {!isPaid ? (
          <div style={{
            marginTop: 4, fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5,
            background: 'rgba(255,184,0,0.15)', color: Z.warning, letterSpacing: 0.4, display: 'inline-block',
          }}>PENDIENTE</div>
        ) : (
          <div style={{
            marginTop: 4, fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5,
            background: 'rgba(0,229,160,0.15)', color: Z.success, letterSpacing: 0.4, display: 'inline-block',
          }}>PAGADO</div>
        )}
      </div>
    </div>
  );
}
window.CobrosScreen = CobrosScreen;

// Nuevo cobro — sheet style
function NewCobroScreen() {
  return (
    <div style={{ height: '100%', position: 'relative', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, rgba(10,10,15,0.4) 0%, rgba(10,10,15,0.85) 100%)',
        backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
      }} />
      <div style={{ position: 'absolute', top: 60, left: 20, right: 20, opacity: 0.25 }}>
        <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.6, color: Z.text }}>Cobros</div>
      </div>

      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        height: '78%', background: Z.bg,
        borderTopLeftRadius: 28, borderTopRightRadius: 28,
        borderTop: `1px solid ${Z.border2}`,
        boxShadow: '0 -20px 60px rgba(0,240,255,0.08)',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 10, paddingBottom: 4 }}>
          <div style={{ width: 36, height: 4, borderRadius: 2, background: '#3a3a55' }} />
        </div>
        <div style={{ padding: '12px 22px 20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.5, marginBottom: 4 }}>Nuevo cobro</div>
          <div style={{ fontSize: 13, color: Z.muted, marginBottom: 22 }}>Agrega un cobro manual a alguien</div>

          {/* Persona */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>PERSONA</div>
            <div style={{
              height: 56, borderRadius: 14, background: Z.surface,
              border: `1px solid ${Z.cyan}`, padding: '0 14px',
              display: 'flex', alignItems: 'center', gap: 12,
              boxShadow: '0 0 0 4px rgba(0,240,255,0.08)',
            }}>
              <div style={{
                width: 36, height: 36, borderRadius: 18, background: Z.gradient,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, fontWeight: 800, color: '#0A0A0F',
              }}>S</div>
              <input style={{
                flex: 1, background: 'transparent', border: 'none', outline: 'none',
                color: Z.text, fontFamily: Z.font, fontSize: 16, fontWeight: 600,
              }} value="Sofía López" readOnly />
            </div>
            {/* Sugerencias */}
            <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
              {['Juan', 'María', 'Pedro', 'Diego'].map(n => (
                <div key={n} style={{
                  padding: '6px 10px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                  background: Z.surface, border: `1px solid ${Z.border}`, color: Z.muted,
                }}>{n}</div>
              ))}
            </div>
          </div>

          {/* Monto */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>MONTO</div>
            <div style={{
              height: 64, borderRadius: 14, background: Z.surface,
              border: `1px solid ${Z.border}`, padding: '0 16px',
              display: 'flex', alignItems: 'baseline',
            }}>
              <span style={{ fontSize: 22, color: Z.muted, fontWeight: 600, alignSelf: 'center' }}>$</span>
              <span style={{
                marginLeft: 6, fontSize: 32, fontWeight: 800, letterSpacing: -1.2, alignSelf: 'center',
                fontVariantNumeric: 'tabular-nums',
              }}>
                <GradientText>22.50</GradientText>
              </span>
            </div>
          </div>

          {/* Descripción */}
          <FieldBox label="DESCRIPCIÓN (OPCIONAL)" value="Cena Da Mario" onIcon="edit" />

          <div style={{ flex: 1 }} />
          <GradientButton>Crear cobro</GradientButton>
          <button style={{
            marginTop: 8, width: '100%', height: 46, borderRadius: 23,
            background: 'transparent', border: 'none',
            color: Z.muted, fontWeight: 600, fontSize: 14, fontFamily: Z.font,
          }}>Cancelar</button>
        </div>
      </div>
    </div>
  );
}
window.NewCobroScreen = NewCobroScreen;