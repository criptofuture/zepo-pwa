// Zepo · pages/empty-states.jsx
//   Primer uso (Home) · Sin historial · Sin cobros.
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function EmptyHomeScreen() {
  return (
    <div style={{ height: '100%', overflow: 'hidden', position: 'relative' }}>
      <div style={{ padding: '12px 20px 100px' }}>
        <PageHeader title="Hola, Andrea" subtitle="Jueves 8 de mayo" showNotif hasUnread={false} />

        {/* Stat row vacío */}
        <div style={{ display: 'flex', gap: 10, marginTop: 4, marginBottom: 26 }}>
          <EmptyStatCard label="ESTA SEMANA" value="$0.00" sub="0 gastos" />
          <EmptyStatCard label="ESTE MES" value="$0.00" sub="0 gastos" />
          <EmptyStatCard label="PROMEDIO" value="—" sub="Sin datos" />
        </div>

        {/* Hero ilustración */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          textAlign: 'center', marginTop: 20, padding: '0 12px',
        }}>
          <div style={{
            width: 120, height: 120, borderRadius: 32,
            background: 'radial-gradient(circle at 30% 30%, rgba(0,240,255,0.22), rgba(112,0,255,0.18) 60%, transparent 80%)',
            border: `1px solid ${Z.cyan}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 24, position: 'relative',
            boxShadow: '0 0 60px rgba(0,240,255,0.18), inset 0 0 24px rgba(112,0,255,0.15)',
          }}>
            <Icon name="sparkles" size={56} color={Z.cyan} strokeWidth={1.6} />
            {/* sparkles flotantes */}
            <div style={{
              position: 'absolute', top: 10, right: 14, width: 12, height: 12,
              background: Z.cyan, borderRadius: 2, transform: 'rotate(45deg)', opacity: 0.7,
              boxShadow: '0 0 12px ' + Z.cyan,
            }} />
            <div style={{
              position: 'absolute', bottom: 16, left: 12, width: 8, height: 8,
              background: '#B794F6', borderRadius: 2, transform: 'rotate(45deg)', opacity: 0.8,
              boxShadow: '0 0 12px #B794F6',
            }} />
          </div>

          <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.6, lineHeight: 1.15, marginBottom: 8 }}>
            Registra tu <GradientText>primer gasto</GradientText>
          </div>
          <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.5, maxWidth: 280, marginBottom: 16 }}>
            Toca el botón <span style={{ color: Z.cyan, fontWeight: 700 }}>+</span> para empezar.
            En segundos, con texto, voz o foto.
          </div>

          {/* Flecha indicadora hacia el FAB */}
          <div style={{
            marginTop: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
            color: Z.cyan, opacity: 0.7,
          }}>
            <div style={{
              fontSize: 10, fontWeight: 700, letterSpacing: 1.4,
              padding: '4px 10px', borderRadius: 6,
              background: 'rgba(0,240,255,0.1)', border: `1px solid rgba(0,240,255,0.3)`,
            }}>EMPIEZA AQUÍ</div>
            <svg width="18" height="40" viewBox="0 0 18 40" fill="none">
              <path d="M9 2v32M3 28l6 6 6-6" stroke={Z.cyan} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="3 3"/>
            </svg>
          </div>
        </div>
      </div>

    </div>
  );
}

function EmptyStatCard({ label, value, sub }) {
  return (
    <div style={{
      flex: 1, padding: 12, borderRadius: 14,
      background: Z.surface, border: `1px dashed ${Z.border2}`,
      minWidth: 0,
    }}>
      <div style={{ fontSize: 9, color: Z.muted, letterSpacing: 1, fontWeight: 700, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: Z.dim, letterSpacing: -0.4, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      <div style={{ fontSize: 10, color: Z.dim, marginTop: 4 }}>{sub}</div>
    </div>
  );
}
window.EmptyHomeScreen = EmptyHomeScreen;

// 4b · Historial vacío
function EmptyHistorialScreen() {
  return (
    <div style={{ height: '100%', overflow: 'hidden', position: 'relative' }}>
      <div style={{ padding: '14px 20px' }}>
        <PageHeader title="Historial" subtitle="Mayo 2026" />
        {/* Filtros vacíos como esqueleto */}
        <div style={{ display: 'flex', gap: 6, marginTop: 6, marginBottom: 32, opacity: 0.5 }}>
          {['Todos', 'Comida', 'Transporte', 'Hogar'].map(t => (
            <div key={t} style={{
              padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600,
              background: Z.surface, border: `1px solid ${Z.border}`, color: Z.dim,
            }}>{t}</div>
          ))}
        </div>
      </div>

      {/* Centro */}
      <div style={{
        position: 'absolute', top: '52%', left: 24, right: 24,
        transform: 'translateY(-50%)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
      }}>
        <div style={{
          width: 112, height: 112, borderRadius: 28,
          background: 'radial-gradient(circle at 35% 35%, rgba(0,240,255,0.15), rgba(112,0,255,0.10) 60%, transparent 80%)',
          border: `1px solid rgba(0,240,255,0.35)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 22,
          boxShadow: '0 0 48px rgba(0,240,255,0.12)',
        }}>
          <Icon name="clock" size={48} color={Z.cyan} strokeWidth={1.6} />
        </div>

        <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.6, lineHeight: 1.15, marginBottom: 8 }}>
          Sin historial <GradientText>aún</GradientText>
        </div>
        <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.5, maxWidth: 280 }}>
          Tus gastos del mes aparecerán aquí ordenados por fecha.
        </div>

        {/* Skeleton hint */}
        <div style={{
          width: '100%', maxWidth: 280, marginTop: 28,
          display: 'flex', flexDirection: 'column', gap: 8, opacity: 0.35,
        }}>
          {[1,2,3].map(i => (
            <div key={i} style={{
              height: 44, borderRadius: 12,
              background: Z.surface, border: `1px solid ${Z.border}`,
              display: 'flex', alignItems: 'center', padding: '0 12px', gap: 10,
            }}>
              <div style={{ width: 24, height: 24, borderRadius: 6, background: Z.border }} />
              <div style={{ flex: 1, height: 8, borderRadius: 4, background: Z.border }} />
              <div style={{ width: 40, height: 8, borderRadius: 4, background: Z.border }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
window.EmptyHistorialScreen = EmptyHistorialScreen;

// 4c · Cobros vacío
function EmptyCobrosScreen() {
  return (
    <div style={{ height: '100%', overflow: 'hidden', position: 'relative' }}>
      <div style={{ padding: '14px 20px' }}>
        <PageHeader title="Cobros" subtitle="Te deben dinero" />
      </div>

      <div style={{
        position: 'absolute', top: '50%', left: 24, right: 24,
        transform: 'translateY(-50%)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
      }}>
        <div style={{
          width: 112, height: 112, borderRadius: 28,
          background: 'radial-gradient(circle at 35% 35%, rgba(112,0,255,0.18), rgba(0,240,255,0.10) 60%, transparent 80%)',
          border: `1px solid rgba(112,0,255,0.35)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 22, position: 'relative',
          boxShadow: '0 0 48px rgba(112,0,255,0.15)',
        }}>
          <Icon name="users" size={48} color="#B794F6" strokeWidth={1.6} />
          {/* check pegado */}
          <div style={{
            position: 'absolute', bottom: -6, right: -6,
            width: 32, height: 32, borderRadius: 10,
            background: Z.success, display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: `3px solid ${Z.bg}`,
          }}>
            <Icon name="check" size={16} color="#0A0A0F" strokeWidth={3.2} />
          </div>
        </div>

        <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.6, lineHeight: 1.15, marginBottom: 8 }}>
          Sin cobros <GradientText>pendientes</GradientText>
        </div>
        <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.5, maxWidth: 300, marginBottom: 22 }}>
          Cuando dividas un gasto, los cobros aparecen aquí automáticamente.
        </div>

        <button style={{
          width: '100%', maxWidth: 280, height: 46, borderRadius: 23,
          background: 'transparent', border: `1px solid ${Z.cyan}`,
          color: Z.cyan, fontWeight: 700, fontSize: 14, fontFamily: Z.font,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          cursor: 'pointer',
        }}>
          <Icon name="plus" size={14} color={Z.cyan} /> Crear cobro manual
        </button>
      </div>
    </div>
  );
}
window.EmptyCobrosScreen = EmptyCobrosScreen;