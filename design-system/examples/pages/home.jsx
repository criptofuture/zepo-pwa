// Zepo home + tab screens — multiple plan variants

// ─── Hero card with big total ──────────────────────────────────
function HeroCard({ amount = '1,240.50', month = 'mayo', delta = '+$120', deltaSign = 'up', monthPct = 27, spentPct = 35 }) {
  return (
    <GradientBorder radius={20} padding={1.2} glow>
      <div style={{ padding: '20px 22px 18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1.2, fontWeight: 600 }}>
            GASTADO EN {month.toUpperCase()}
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            fontSize: 11, color: deltaSign === 'up' ? Z.danger : Z.success, fontWeight: 600,
          }}>
            <Icon name={deltaSign === 'up' ? 'trending-up' : 'trending-down'} size={11} />
            {delta} vs mes anterior
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 14 }}>
          <span style={{ fontSize: 20, color: Z.muted, fontWeight: 600, marginRight: 2 }}>$</span>
          <span style={{
            fontSize: 48, fontWeight: 800, letterSpacing: -2.2, lineHeight: 1, color: Z.text,
            fontVariantNumeric: 'tabular-nums',
          }}>
            <GradientText>{amount}</GradientText>
          </span>
        </div>
        <div>
          <div style={{
            position: 'relative', height: 6, background: Z.border, borderRadius: 3, overflow: 'hidden',
          }}>
            <div style={{ position: 'absolute', inset: 0, width: `${spentPct}%`, background: Z.gradient, borderRadius: 3 }} />
            <div style={{
              position: 'absolute', top: -2, left: `${monthPct}%`, width: 1.5, height: 10,
              background: Z.text, opacity: 0.9,
            }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11, color: Z.muted }}>
            <span>{spentPct}% gastado</span>
            <span>{monthPct}% del mes transcurrido</span>
          </div>
        </div>
      </div>
    </GradientBorder>
  );
}
window.HeroCard = HeroCard;

function StatCard({ label, value, sub, locked, color = Z.text }) {
  return (
    <div style={{
      flex: '1 0 38%', minWidth: 140,
      padding: 14, background: Z.surface, borderRadius: 14,
      border: `1px solid ${Z.border}`, position: 'relative',
      opacity: locked ? 0.55 : 1,
    }}>
      <div style={{ fontSize: 10, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: -0.5, color, fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 11, color: Z.muted, marginTop: 4 }}>{sub}</div>}
      {locked && (
        <div style={{ position: 'absolute', top: 12, right: 12 }}>
          <LockIcon size={13} color={Z.cyan} />
        </div>
      )}
    </div>
  );
}
window.StatCard = StatCard;

function ExpenseRow({ cat = 'food', desc, amount, when, source = 'edit', blurred = false }) {
  const sourceIcons = { edit: '✏️', ai: '✨', voice: '🎤', photo: '📷', file: '📄' };
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 0',
      filter: blurred ? 'blur(5px)' : 'none',
    }}>
      <CategoryChip k={cat} size={40} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: Z.text, letterSpacing: -0.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {desc}
        </div>
        <div style={{ fontSize: 11, color: Z.muted, marginTop: 2, display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ opacity: 0.8 }}>{sourceIcons[source]}</span>
          {when}
        </div>
      </div>
      <div style={{ fontSize: 15, fontWeight: 700, color: Z.text, letterSpacing: -0.3, fontVariantNumeric: 'tabular-nums' }}>
        −${amount}
      </div>
    </div>
  );
}
window.ExpenseRow = ExpenseRow;

// ─── HomeScreen — Free plan ─────────────────────────────────
function HomeFree() {
  return (
    <div style={{ height: '100%', overflow: 'hidden', position: 'relative' }}>
      <div style={{ padding: '12px 20px 100px' }}>
        {/* header */}
        <PageHeader
          title="Hola, Andrea"
          subtitle="Jueves 8 de mayo"
          showNotif
          showSettings
        />

        {/* sunset banner */}
        <div style={{
          marginTop: 14, padding: '10px 14px', borderRadius: 12,
          background: Z.warning, color: '#0A0A0F',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          fontSize: 12, fontWeight: 600,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon name="alert-triangle" size={14} color="#0A0A0F" strokeWidth={2.5} />
            <span>Plan Free vence el 31 dic · 237 días</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 2, fontWeight: 700 }}>
            Mejorar <Icon name="arrow-right" size={12} color="#0A0A0F" strokeWidth={2.6} />
          </div>
        </div>

        {/* hero */}
        <div style={{ marginTop: 16 }}>
          <HeroCard amount="1,240.50" delta="+$120" deltaSign="up" monthPct={27} spentPct={35} />
        </div>

        {/* stat row */}
        <div style={{ display: 'flex', gap: 10, marginTop: 14, overflowX: 'auto' }}>
          <StatCard label="ESTA SEMANA" value="$284.20" sub="6 gastos" />
          <StatCard label="CATEGORÍA TOP" value="🍽 Comida" sub="$420 · 34%" />
          <StatCard label="PRESUPUESTO" value="—" sub="Pro" locked color={Z.muted} />
        </div>

        {/* recent */}
        <div style={{ marginTop: 22, display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: -0.3 }}>Reciente</div>
          <div style={{ fontSize: 12, color: Z.cyan, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 2 }}>
            Ver todo <Icon name="arrow-right" size={12} color={Z.cyan} />
          </div>
        </div>

        <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, padding: '4px 14px' }}>
          <ExpenseRow cat="food"   desc="Almuerzo La Tablita" amount="12.50" when="hace 2h" source="edit" />
          <Sep />
          <ExpenseRow cat="taxi"   desc="Taxi al aeropuerto"  amount="35.00" when="hace 5h" source="edit" />
          <Sep />
          <ExpenseRow cat="coffee" desc="Café cortado"        amount="3.50"  when="hace 6h" source="edit" />
          <Sep />
          <ExpenseRow cat="market" desc="Supermaxi"           amount="68.40" when="ayer"   source="edit" />
          <Sep />
          <ExpenseRow cat="fun"    desc="Cine + canchita"     amount="18.00" when="ayer"   source="edit" />
        </div>

        {/* upgrade tease for old expenses */}
        <div style={{
          marginTop: 14, padding: 14, borderRadius: 14,
          background: Z.surface2,
          border: `1px dashed ${Z.cyan}`, position: 'relative',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <LockIcon size={16} color={Z.cyan} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>Gastos de mes anterior bloqueados</div>
              <div style={{ fontSize: 11, color: Z.muted, marginTop: 2 }}>Mejora a Pro para ver historial completo.</div>
            </div>
            <div style={{ fontSize: 11, color: Z.cyan, fontWeight: 700 }}>Mejorar →</div>
          </div>
        </div>
      </div>
    </div>
  );
}
function Sep() { return <div style={{ height: 1, background: Z.border }} />; }

// ─── HomeScreen — Elite plan ────────────────────────────────
function HomeElite() {
  return (
    <div style={{ height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '12px 20px 100px' }}>
        <PageHeader
          title="Hola, Andrea"
          subtitle="Jueves 8 de mayo"
          badge={<PlanBadge plan="elite" />}
          showNotif
          showSettings
        />

        <HeroCard amount="2,847.30" delta="−$180" deltaSign="down" monthPct={27} spentPct={22} />

        <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
          <StatCard label="ESTA SEMANA" value="$684.20" sub="14 gastos" />
          <StatCard label="CATEGORÍA TOP" value="🍽 Comida" sub="$840 · 29%" />
          <StatCard label="PRESUPUESTO" value="68%" sub="$2,047 / 3,000" color={Z.warning} />
        </div>

        {/* mini bar chart for week */}
        <div style={{ marginTop: 22 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: -0.3 }}>Esta semana</div>
            <div style={{ fontSize: 11, color: Z.muted }}>Promedio · $97.74/día</div>
          </div>
          <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, padding: 14 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 70 }}>
              {[
                { d: 'L', v: 0.5 }, { d: 'M', v: 0.8 }, { d: 'X', v: 0.3 },
                { d: 'J', v: 1.0 }, { d: 'V', v: 0.9 }, { d: 'S', v: 0.4 },
                { d: 'D', v: 0.6 },
              ].map((b, i) => (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                  <div style={{
                    width: '100%', height: `${b.v * 100}%`,
                    background: Z.gradient, borderRadius: 4,
                    minHeight: 4,
                  }} />
                  <div style={{ fontSize: 10, color: Z.muted }}>{b.d}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* recurring */}
        <div style={{ marginTop: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: -0.3, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon name="repeat" size={14} color={Z.cyan} /> Recurrentes próximos
            </div>
            <div style={{ fontSize: 11, color: Z.muted }}>3</div>
          </div>
          <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, padding: '4px 14px' }}>
            <ExpenseRow cat="rent"   desc="Arriendo · Cumbayá" amount="650.00" when="en 3 días"  source="edit" />
            <Sep />
            <ExpenseRow cat="other"  desc="Netflix"            amount="14.99"  when="en 5 días"  source="edit" />
            <Sep />
            <ExpenseRow cat="other"  desc="Gym Smartfit"       amount="29.90"  when="en 12 días" source="edit" />
          </div>
        </div>
      </div>
    </div>
  );
}

window.HomeFree = HomeFree;
window.HomeElite = HomeElite;
window.Sep = Sep;
