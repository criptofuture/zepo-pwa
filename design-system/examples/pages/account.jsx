// Zepo — perfil, planes, blocked screens

// ─── Perfil ─────────────────────────────────────────────────
function PerfilScreen({ plan = 'elite' }) {
  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 100 }}>
      <div style={{ padding: '14px 20px' }}>
        <PageHeader title="Perfil" showSettings={false} />

        {/* hero */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 22 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 32,
            background: Z.gradient,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 26, fontWeight: 800, color: '#0A0A0F', letterSpacing: -0.5,
            boxShadow: '0 0 0 4px #0A0A0F, 0 0 24px rgba(0,240,255,0.3)',
          }}>A</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: -0.3 }}>Andrea Salazar</div>
            <div style={{ fontSize: 12, color: Z.muted, marginTop: 2 }}>andrea.salazar@gmail.com</div>
          </div>
        </div>

        {/* plan card */}
        <GradientBorder radius={16} padding={1}>
          <div style={{ padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <PlanBadge plan={plan} />
                <span style={{ fontSize: 13, color: Z.muted }}>· $10/mes</span>
              </div>
              <div style={{ fontSize: 11, color: Z.muted, fontWeight: 600 }}>RENUEVA 22 MAY</div>
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: -0.3, marginBottom: 12 }}>
              Tienes acceso completo
            </div>
            <ProgressBar value={62} height={4} gradient />
            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: Z.muted }}>
              <span>47 gastos este mes</span>
              <span>Sin límites</span>
            </div>
            <button style={{
              marginTop: 14, width: '100%', height: 42, borderRadius: 10,
              background: 'transparent', border: `1px solid ${Z.border}`,
              color: Z.text, fontWeight: 600, fontSize: 13, fontFamily: Z.font,
            }}>Cambiar plan</button>
          </div>
        </GradientBorder>

        {/* config */}
        <ProfileSection label="CONFIGURACIÓN">
          <ProfileRow label="Moneda principal" right="USD" />
          <ProfileRow label="Notificaciones" toggle defaultOn />
          <ProfileRow label="Resumen diario" toggle defaultOn sub="Cada noche · 21:00" />
          <ProfileRow label="Resumen semanal" toggle sub="Cada domingo" last />
        </ProfileSection>

        <ProfileSection label="INTEGRACIONES">
          <ProfileRow label="Gmail" right="Conectado" rightColor={Z.success} icon="mail" />
          <ProfileRow label="Google Sheets" right="Conectado" rightColor={Z.success} icon="cloud" last />
        </ProfileSection>

        <ProfileSection label="CUENTA">
          <ProfileRow label="Exportar mis datos" icon="download" />
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

function ProfileSection({ label, children }) {
  return (
    <div style={{ marginTop: 22 }}>
      <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1.4, fontWeight: 700, marginBottom: 8, paddingLeft: 4 }}>
        {label}
      </div>
      <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, overflow: 'hidden' }}>
        {children}
      </div>
    </div>
  );
}

function ProfileRow({ label, right, rightColor, sub, toggle, defaultOn, last, danger, icon }) {
  return (
    <div style={{
      padding: '14px 14px', display: 'flex', alignItems: 'center', gap: 12,
      borderBottom: last ? 'none' : `1px solid ${Z.border}`,
    }}>
      {icon && (
        <div style={{
          width: 28, height: 28, borderRadius: 8, background: Z.bg,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name={icon} size={14} color={danger ? Z.danger : Z.cyan} />
        </div>
      )}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: danger ? Z.danger : Z.text }}>{label}</div>
        {sub && <div style={{ fontSize: 11, color: Z.muted, marginTop: 2 }}>{sub}</div>}
      </div>
      {right && (
        <div style={{ fontSize: 12, fontWeight: 600, color: rightColor || Z.muted }}>{right}</div>
      )}
      {toggle && (
        <div style={{
          width: 36, height: 22, borderRadius: 11,
          background: defaultOn ? Z.cyan : '#2a2a3d', position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: 2, left: defaultOn ? 16 : 2,
            width: 18, height: 18, borderRadius: 9, background: '#fff',
          }} />
        </div>
      )}
      {!toggle && !right && <Icon name="chevron-right" size={14} color={Z.dim} />}
    </div>
  );
}

// ─── Planes ─────────────────────────────────────────────────
function PlanesScreen() {
  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 100 }}>
      <div style={{ padding: '14px 20px' }}>
        {/* header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 18, background: Z.surface,
            border: `1px solid ${Z.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Icon name="chevron-left" size={18} color={Z.text} />
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: -0.4 }}>Planes</div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.8, lineHeight: 1.15, marginBottom: 6 }}>
            Tu dinero, <GradientText>claro.</GradientText>
          </div>
          <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.4 }}>
            Empieza gratis. Mejora cuando tu vida financiera se vuelva interesante.
          </div>
        </div>

        {/* annual toggle */}
        <div style={{
          display: 'flex', background: Z.surface, borderRadius: 11, padding: 4,
          border: `1px solid ${Z.border}`, marginBottom: 20, position: 'relative',
        }}>
          <div style={{
            flex: 1, textAlign: 'center', padding: '8px 0', borderRadius: 8,
            background: Z.bg, color: Z.text, fontSize: 13, fontWeight: 600,
          }}>Mensual</div>
          <div style={{
            flex: 1, textAlign: 'center', padding: '8px 0',
            color: Z.muted, fontSize: 13, fontWeight: 500,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}>Anual <span style={{
            fontSize: 9, fontWeight: 700, padding: '2px 5px', borderRadius: 4,
            background: 'rgba(0,229,160,0.2)', color: Z.success, letterSpacing: 0.4,
          }}>−2 MESES</span></div>
        </div>

        {/* full plan cards */}
        <FullPlanCard
          name="Free"
          price="$0"
          period="/mes"
          tagline="Para empezar a registrar"
          warning="Hasta 31 dic 2026"
          features={[
            { v: true,  l: 'Entrada manual' },
            { v: true,  l: 'Historial de 1 mes' },
            { v: true,  l: '6 categorías fijas' },
            { v: false, l: 'IA · texto + voz' },
            { v: false, l: 'Foto de recibo' },
            { v: false, l: 'Dashboard con gráficos' },
          ]}
          cta="Plan actual"
          ctaStyle="outline"
          current
        />
        <FullPlanCard
          name="Pro"
          price="$5"
          period="/mes"
          tagline="Para llevarlo en serio"
          highlight="MÁS POPULAR"
          features={[
            { v: true, l: 'Todo de Free' },
            { v: true, l: 'IA · texto libre + voz' },
            { v: true, l: 'Historial ilimitado' },
            { v: true, l: 'Categorías ilimitadas + custom' },
            { v: true, l: 'Multi-moneda LATAM' },
            { v: true, l: 'Exportar CSV' },
          ]}
          cta="Mejorar a Pro"
          ctaStyle="gradient"
        />
        <FullPlanCard
          name="Elite"
          price="$10"
          period="/mes"
          tagline="Cuando quieres todo automático"
          gradient
          highlight="COMPLETO"
          features={[
            { v: true, l: 'Todo de Pro' },
            { v: true, l: 'Foto de recibo · OCR' },
            { v: true, l: 'Importar PDF/CSV bancario' },
            { v: true, l: 'Dashboard + analytics' },
            { v: true, l: 'Sync Gmail + Google Sheets' },
            { v: true, l: 'Soporte prioritario' },
          ]}
          cta="Mejorar a Elite"
          ctaStyle="gradient"
        />

        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 11, color: Z.dim }}>
          Cancela cuando quieras · Sin permanencia
        </div>
      </div>
    </div>
  );
}

function FullPlanCard({ name, price, period, tagline, warning, highlight, gradient, features, cta, ctaStyle, current }) {
  const inner = (
    <div style={{ padding: '20px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
        <div>
          <div style={{ fontSize: 14, color: Z.muted, fontWeight: 600 }}>{tagline}</div>
          <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.5, marginTop: 2 }}>{name}</div>
        </div>
        {warning ? (
          <span style={{ fontSize: 9, fontWeight: 700, padding: '4px 8px', borderRadius: 5, background: '#FFB80020', color: Z.warning, letterSpacing: 0.6 }}>{warning.toUpperCase()}</span>
        ) : highlight && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '4px 8px', borderRadius: 5, letterSpacing: 0.6,
            background: gradient ? Z.gradient : '#00F0FF18',
            color: gradient ? '#0A0A0F' : Z.cyan,
          }}>{highlight}</span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 16 }}>
        <span style={{ fontSize: 36, fontWeight: 800, letterSpacing: -1.2, fontVariantNumeric: 'tabular-nums' }}>
          <GradientText>{price}</GradientText>
        </span>
        <span style={{ fontSize: 14, color: Z.muted, fontWeight: 500 }}>{period}</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
        {features.map((f, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: f.v ? Z.text : Z.dim }}>
            {f.v ? (
              <div style={{
                width: 18, height: 18, borderRadius: 9,
                background: 'rgba(0,240,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon name="check" size={11} color={Z.cyan} strokeWidth={3} />
              </div>
            ) : (
              <div style={{
                width: 18, height: 18, borderRadius: 9, opacity: 0.4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon name="x" size={11} color={Z.dim} strokeWidth={2.5} />
              </div>
            )}
            {f.l}
          </div>
        ))}
      </div>

      {ctaStyle === 'gradient' ? (
        <GradientButton height={46}>{cta}</GradientButton>
      ) : (
        <button style={{
          width: '100%', height: 46, borderRadius: 23,
          background: 'transparent', border: `1px solid ${current ? Z.cyan : Z.border}`,
          color: current ? Z.cyan : Z.text, fontWeight: 700, fontSize: 14, fontFamily: Z.font,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        }}>
          {current && <Icon name="check" size={14} color={Z.cyan} />}
          {cta}
        </button>
      )}
    </div>
  );

  if (gradient) {
    return (
      <div style={{ marginBottom: 12 }}>
        <GradientBorder radius={18} padding={1.5} glow>
          <div style={{
            background: 'linear-gradient(160deg, rgba(0,240,255,0.06) 0%, rgba(112,0,255,0.08) 100%)',
            borderRadius: 16.5,
          }}>{inner}</div>
        </GradientBorder>
      </div>
    );
  }

  return (
    <div style={{
      marginBottom: 12, background: Z.surface, borderRadius: 18,
      border: `1px solid ${highlight ? Z.cyan : Z.border}`,
      boxShadow: highlight ? '0 0 0 3px rgba(0,240,255,0.06)' : 'none',
    }}>{inner}</div>
  );
}

// ─── Blocked / sunset ───────────────────────────────────────
function BlockedScreen() {
  return (
    <div style={{
      height: '100%', position: 'relative', overflow: 'hidden',
      background: 'radial-gradient(circle at 50% 30%, rgba(255,107,107,0.12) 0%, transparent 60%), #0A0A0F',
    }}>
      <div style={{
        padding: '60px 28px 28px', height: '100%',
        display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
      }}>
        {/* lock icon */}
        <div style={{
          width: 100, height: 100, borderRadius: 28,
          background: 'linear-gradient(135deg, rgba(255,107,107,0.15), rgba(255,184,0,0.15))',
          border: `1px solid ${Z.warning}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 28,
          boxShadow: '0 0 48px rgba(255,107,107,0.25)',
        }}>
          <Icon name="lock" size={42} color={Z.warning} strokeWidth={1.8} />
        </div>

        <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.8, lineHeight: 1.15, marginBottom: 12 }}>
          El plan Free terminó
        </div>
        <div style={{ fontSize: 15, color: Z.muted, lineHeight: 1.5, marginBottom: 24, maxWidth: 320 }}>
          Tus 47 gastos siguen ahí. Cuando mejores a Pro o Elite, los recuperas todos al instante. Nada se borra.
        </div>

        {/* preserved data card */}
        <div style={{
          width: '100%', padding: 18, background: Z.surface,
          borderRadius: 16, border: `1px solid ${Z.border}`,
          marginBottom: 22,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8, background: 'rgba(0,229,160,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Icon name="check" size={14} color={Z.success} strokeWidth={3} />
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, textAlign: 'left' }}>Tus datos están a salvo</div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: Z.muted, marginBottom: 6 }}>
            <span>Gastos guardados</span><span style={{ color: Z.text, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>47</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: Z.muted, marginBottom: 6 }}>
            <span>Total registrado</span><span style={{ color: Z.text, fontWeight: 700 }}>$1,240.50</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: Z.muted }}>
            <span>Desde</span><span style={{ color: Z.text, fontWeight: 600 }}>4 abril 2026</span>
          </div>
        </div>

        <div style={{ width: '100%' }}>
          <GradientButton>Mejorar a Pro · $5/mes</GradientButton>
          <button style={{
            marginTop: 10, width: '100%', height: 50, borderRadius: 25,
            background: 'transparent', border: `1px solid ${Z.border}`,
            color: Z.muted, fontWeight: 600, fontSize: 14, fontFamily: Z.font,
          }}>Exportar mis gastos a CSV</button>
        </div>

        <div style={{ marginTop: 'auto', paddingTop: 20, fontSize: 11, color: Z.dim, lineHeight: 1.5 }}>
          Hasta el 31 dic 2026 · Día 8 después del fin
        </div>
      </div>
    </div>
  );
}

// ─── Sunset 7-day grace banner state ──────────────────────────
function HomeSunsetGrace() {
  return (
    <div style={{ height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '12px 20px 100px' }}>
        <PageHeader title="Hola, Andrea" subtitle="Jueves 8 de enero" showNotif hasUnread={false} />

        {/* urgent red banner */}
        <div style={{
          padding: '14px 16px', borderRadius: 14,
          background: 'linear-gradient(135deg, rgba(255,107,107,0.18), rgba(255,107,107,0.08))',
          border: `1px solid ${Z.danger}`,
          marginBottom: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <Icon name="alert-triangle" size={16} color={Z.danger} />
            <div style={{ fontSize: 13, fontWeight: 700, color: Z.danger, letterSpacing: 0.3 }}>
              4 días para mejorar tu plan
            </div>
          </div>
          <div style={{ fontSize: 12, color: Z.muted, lineHeight: 1.45, marginBottom: 10 }}>
            El plan Free termina pronto. Al expirar, no podrás registrar nuevos gastos hasta mejorar.
          </div>
          <button style={{
            width: '100%', height: 38, borderRadius: 9,
            background: Z.danger, border: 'none', color: '#fff',
            fontWeight: 700, fontSize: 12, fontFamily: Z.font,
          }}>Mejorar plan ahora</button>
        </div>

        <HeroCard amount="1,240.50" delta="+$120" deltaSign="up" monthPct={27} spentPct={35} />

        <div style={{ marginTop: 22, fontSize: 16, fontWeight: 700, letterSpacing: -0.3, marginBottom: 8 }}>Reciente</div>
        <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, padding: '4px 14px' }}>
          <ExpenseRow cat="food" desc="Almuerzo La Tablita" amount="12.50" when="hace 2h" source="edit" />
          <Sep />
          <ExpenseRow cat="taxi" desc="Taxi al aeropuerto" amount="35.00" when="hace 5h" source="edit" />
          <Sep />
          <ExpenseRow cat="coffee" desc="Café cortado" amount="3.50" when="hace 6h" source="edit" />
        </div>
      </div>
    </div>
  );
}

window.PerfilScreen = PerfilScreen;
window.PlanesScreen = PlanesScreen;
window.BlockedScreen = BlockedScreen;
window.HomeSunsetGrace = HomeSunsetGrace;
window.FullPlanCard = FullPlanCard;
window.ProfileSection = ProfileSection;
window.ProfileRow = ProfileRow;
