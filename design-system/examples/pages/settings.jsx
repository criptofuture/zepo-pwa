// Zepo · pages/settings.jsx
//   Configuración: moneda · categorías · presupuestos · notif · cuenta.
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function SettingsScreen() {
  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 60 }}>
      <ScreenHeader title="Configuración" />

      <div style={{ padding: '0 20px' }}>
        {/* Moneda */}
        <ProfileSection label="MONEDA">
          <div style={{ padding: '14px 14px' }}>
            <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 0.6, fontWeight: 600, marginBottom: 8 }}>PRINCIPAL</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {[
                { c: 'USD', f: '🇪🇨', s: true },
                { c: 'EUR', f: '🇪🇺' },
                { c: 'COP', f: '🇨🇴' },
                { c: 'PEN', f: '🇵🇪' },
                { c: 'MXN', f: '🇲🇽' },
              ].map(m => (
                <div key={m.c} style={{
                  padding: '8px 12px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                  background: m.s ? 'rgba(0,240,255,0.10)' : Z.bg,
                  border: `1px solid ${m.s ? Z.cyan : Z.border}`,
                  color: m.s ? Z.text : Z.muted,
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <span style={{ fontSize: 14 }}>{m.f}</span>{m.c}
                  {m.s && <Icon name="check" size={11} color={Z.cyan} strokeWidth={3} />}
                </div>
              ))}
            </div>
          </div>
        </ProfileSection>

        {/* Categorías */}
        <ProfileSection label="CATEGORÍAS">
          <div style={{ padding: '12px 14px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {APPROVE_CATS.map(c => (
                <div key={c.k} style={{
                  padding: '7px 10px', borderRadius: 9, fontSize: 12, fontWeight: 600,
                  background: `${c.c}12`, border: `1px solid ${c.c}30`,
                  color: Z.text, display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <span style={{ fontSize: 13 }}>{c.emoji}</span>{c.l}
                  <Icon name="x" size={10} color={Z.muted} />
                </div>
              ))}
              <div style={{
                padding: '7px 10px', borderRadius: 9, fontSize: 12, fontWeight: 600,
                background: 'transparent', border: `1px dashed ${Z.cyan}`,
                color: Z.cyan, display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <Icon name="plus" size={10} color={Z.cyan} /> Agregar
              </div>
            </div>
            <div style={{ fontSize: 11, color: Z.dim }}>Toca una categoría para editarla.</div>
          </div>
        </ProfileSection>

        {/* Presupuestos */}
        <ProfileSection label="PRESUPUESTOS">
          {[
            { k: 'food',      total: 250, used: 175, c: '#FF6B6B' },
            { k: 'transport', total: 120, used: 48,  c: '#00F0FF' },
            { k: 'home',      total: 600, used: 480, c: '#7000FF' },
          ].map((b, i, arr) => {
            const cat = APPROVE_CATS.find(c => c.k === b.k);
            const pct = Math.round(b.used / b.total * 100);
            return (
              <div key={b.k} style={{
                padding: '14px 14px',
                borderBottom: i < arr.length - 1 ? `1px solid ${Z.border}` : 'none',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: `${cat.c}18`, border: `1px solid ${cat.c}30`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 13,
                  }}>{cat.emoji}</div>
                  <div style={{ flex: 1, fontSize: 14, fontWeight: 600 }}>{cat.l}</div>
                  <div style={{ fontSize: 12, color: Z.muted, fontVariantNumeric: 'tabular-nums' }}>
                    <span style={{ color: Z.text, fontWeight: 700 }}>${b.used}</span> / ${b.total}
                  </div>
                </div>
                <ProgressBar value={pct} height={5} />
                <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                  {[50, 75, 90].map(a => (
                    <div key={a} style={{
                      padding: '3px 7px', borderRadius: 5, fontSize: 10, fontWeight: 700, letterSpacing: 0.4,
                      background: pct >= a ? 'rgba(255,184,0,0.15)' : Z.bg,
                      color: pct >= a ? Z.warning : Z.dim,
                      border: `1px solid ${pct >= a ? 'rgba(255,184,0,0.3)' : Z.border}`,
                    }}>{a}%</div>
                  ))}
                </div>
              </div>
            );
          })}
          <div style={{
            padding: '12px 14px', borderTop: `1px solid ${Z.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            color: Z.cyan, fontWeight: 600, fontSize: 13,
          }}>
            <Icon name="plus" size={13} color={Z.cyan} /> Agregar presupuesto
          </div>
        </ProfileSection>

        {/* Notificaciones */}
        <ProfileSection label="NOTIFICACIONES">
          <ProfileRow label="Recordatorio diario" sub="Cada noche · 21:00" toggle defaultOn />
          <ProfileRow label="Alertas de presupuesto" sub="50% · 75% · 90%" toggle defaultOn />
          <ProfileRow label="Resumen semanal" toggle last />
        </ProfileSection>

        {/* Exportar */}
        <ProfileSection label="DATOS">
          <ProfileRow label="Exportar Excel · mes actual" icon="download" />
          <ProfileRow label="Exportar todo el historial" icon="download" last />
        </ProfileSection>

        {/* Cuenta */}
        <ProfileSection label="CUENTA">
          <ProfileRow label="Cambiar contraseña" icon="lock" />
          <ProfileRow label="Cerrar sesión" icon="log-out" />
          <ProfileRow label="Eliminar cuenta" danger last />
        </ProfileSection>

        <div style={{ textAlign: 'center', padding: '20px 0', color: Z.dim, fontSize: 11 }}>
          Zepo v1.0 · Hecho en Ecuador 🇪🇨
        </div>
      </div>
    </div>
  );
}
window.SettingsScreen = SettingsScreen;