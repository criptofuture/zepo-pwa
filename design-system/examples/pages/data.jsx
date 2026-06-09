// Zepo — historial, presupuestos, dashboard, perfil, planes, blocked

// ─── Historial ──────────────────────────────────────────────
function HistorialScreen({ plan = 'pro' }) {
  const cats = [
    { k: 'all',  l: 'Todos',     active: true },
    { k: 'food', l: '🍽 Comida' },
    { k: 'transport', l: '🚌 Transporte' },
    { k: 'shop', l: '🛍 Compras' },
    { k: 'fun',  l: '🎮 Entret.' },
    { k: 'other',l: '✨ Otros' },
  ];
  return (
    <div style={{ height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px 0' }}>
        <PageHeader title="Historial" subtitle="Mayo 2026" />

        {/* month nav */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 14px', background: Z.surface, borderRadius: 12,
          border: `1px solid ${Z.border}`, marginBottom: 10,
        }}>
          <Icon name="chevron-left" size={16} color={Z.muted} />
          <div style={{ fontSize: 14, fontWeight: 700 }}>Mayo 2026</div>
          <Icon name="chevron-right" size={16} color={Z.muted} />
        </div>

        {/* cat chips */}
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 6 }}>
          {cats.map(c => (
            <div key={c.k} style={{
              padding: '7px 12px', borderRadius: 9, fontSize: 12, whiteSpace: 'nowrap', fontWeight: 600,
              background: c.active ? Z.gradient : Z.surface,
              color: c.active ? '#0A0A0F' : Z.muted,
              border: c.active ? 'none' : `1px solid ${Z.border}`,
            }}>{c.l}</div>
          ))}
        </div>
      </div>

      <div style={{ padding: '14px 20px 110px', overflow: 'auto', height: 'calc(100% - 140px)' }}>
        {/* HOY */}
        <SectionHead label="HOY" />
        <ListBlock>
          <ExpenseRow cat="food" desc="Almuerzo La Tablita" amount="12.50" when="14:32" source="edit" />
          <Sep />
          <ExpenseRow cat="taxi" desc="Taxi al aeropuerto" amount="35.00" when="08:14" source="voice" />
          <Sep />
          <ExpenseRow cat="coffee" desc="Café cortado · Sweet&Coffee" amount="3.50" when="07:42" source="ai" />
        </ListBlock>

        <SectionHead label="AYER · MIÉRCOLES" total="$96.40" />
        <ListBlock>
          <ExpenseRow cat="market" desc="Supermaxi · semana" amount="68.40" when="18:20" source="photo" />
          <Sep />
          <ExpenseRow cat="fun" desc="Cine + canchita" amount="18.00" when="20:10" source="edit" />
          <Sep />
          <ExpenseRow cat="other" desc="Spotify Premium" amount="10.00" when="00:00" source="edit" />
        </ListBlock>

        <SectionHead label="LUNES 5 DE MAYO" total="$54.30" />
        <ListBlock>
          <ExpenseRow cat="transport" desc="Uber a oficina" amount="6.30" when="07:50" source="ai" />
          <Sep />
          <ExpenseRow cat="health" desc="Farmacia · ibuprofeno" amount="8.20" when="13:15" source="edit" />
          <Sep />
          <ExpenseRow cat="shop" desc="Camiseta Zara" amount="39.80" when="19:40" source="edit" />
        </ListBlock>

        {plan === 'free' && (
          <div style={{ marginTop: 8 }}>
            <SectionHead label="ABRIL 2026" total="$1,124" locked />
            <div style={{
              background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`,
              padding: '4px 14px', position: 'relative', overflow: 'hidden',
            }}>
              <div style={{ filter: 'blur(6px)', opacity: 0.5 }}>
                <ExpenseRow cat="food" desc="Cena en Quito" amount="42.00" when="29 abr" source="edit" />
                <Sep />
                <ExpenseRow cat="market" desc="Supermaxi" amount="78.30" when="28 abr" source="edit" />
              </div>
              <div style={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(180deg, rgba(10,10,15,0.4) 0%, rgba(10,10,15,0.92) 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 8,
              }}>
                <LockIcon size={20} color={Z.cyan} />
                <div style={{ fontSize: 13, fontWeight: 600 }}>Historial bloqueado</div>
                <div style={{ fontSize: 11, color: Z.muted }}>Mejora a Pro para ver meses anteriores</div>
                <button style={{
                  marginTop: 4, padding: '8px 14px', borderRadius: 9, background: Z.gradient,
                  border: 'none', fontWeight: 700, fontSize: 12, color: '#0A0A0F', fontFamily: Z.font,
                }}>Mejorar a Pro · $5/mes</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* footer total */}
      <div style={{
        position: 'absolute', bottom: 84, left: 0, right: 0,
        padding: '12px 20px', background: Z.bg,
        borderTop: `1px solid ${Z.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ fontSize: 12, color: Z.muted }}>47 gastos · mayo</div>
        <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: -0.5, fontVariantNumeric: 'tabular-nums' }}>
          <span style={{ color: Z.muted, fontWeight: 500, fontSize: 13 }}>Total </span>
          <GradientText>$1,240.50</GradientText>
        </div>
      </div>
    </div>
  );
}

function SectionHead({ label, total, locked }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      paddingTop: 14, paddingBottom: 8,
    }}>
      <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1.4, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
        {locked && <LockIcon size={11} color={Z.cyan} />} {label}
      </div>
      {total && (
        <div style={{ fontSize: 12, color: Z.muted, fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>{total}</div>
      )}
    </div>
  );
}

function ListBlock({ children }) {
  return (
    <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, padding: '2px 14px' }}>
      {children}
    </div>
  );
}

// ─── Presupuestos (Pro) ─────────────────────────────────────
function PresupuestosScreen() {
  const items = [
    { k: 'food', name: 'Comida', spent: 420, limit: 500, pct: 84, color: Z.warning },
    { k: 'transport', name: 'Transporte', spent: 210, limit: 300, pct: 70, color: Z.success },
    { k: 'fun', name: 'Entretenimiento', spent: 184, limit: 150, pct: 122, color: Z.danger },
    { k: 'shop', name: 'Compras', spent: 95, limit: 250, pct: 38, color: Z.success },
    { k: 'health', name: 'Salud', spent: 32, limit: 100, pct: 32, color: Z.success },
  ];
  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 100 }}>
      <div style={{ padding: '14px 20px 14px' }}>
        <PageHeader
          title="Presupuestos"
          subtitle="Mayo 2026 · 14 días restantes"
          badge={<PlanBadge plan="pro" />}
        />

        {/* global */}
        <div style={{
          padding: '18px 18px', background: Z.surface, borderRadius: 16,
          border: `1px solid ${Z.border}`, marginBottom: 18,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600 }}>GASTADO TOTAL</div>
              <div style={{ marginTop: 4, fontSize: 28, fontWeight: 800, letterSpacing: -1.2, fontVariantNumeric: 'tabular-nums' }}>
                <GradientText>$941</GradientText>
                <span style={{ fontSize: 16, color: Z.muted, fontWeight: 600 }}> / 1,300</span>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600 }}>RESTANTE</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: Z.success, marginTop: 4 }}>$359</div>
            </div>
          </div>
          <ProgressBar value={72} height={8} color={Z.warning} />
          <div style={{ marginTop: 10, fontSize: 11, color: Z.muted, lineHeight: 1.4 }}>
            A este ritmo cerrarás el mes en <span style={{ color: Z.warning, fontWeight: 700 }}>$1,460</span> · 12% sobre presupuesto.
          </div>
        </div>

        {/* by category */}
        <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1.2, fontWeight: 700, marginBottom: 10 }}>
          POR CATEGORÍA
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map(it => (
            <div key={it.k} style={{
              padding: '14px 14px', background: Z.surface, borderRadius: 14,
              border: `1px solid ${Z.border}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <CategoryChip k={it.k} size={36} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{it.name}</div>
                  <div style={{ fontSize: 11, color: Z.muted, marginTop: 2, fontVariantNumeric: 'tabular-nums' }}>
                    ${it.spent} de ${it.limit}
                  </div>
                </div>
                <div style={{ fontSize: 16, fontWeight: 800, color: it.color, letterSpacing: -0.4, fontVariantNumeric: 'tabular-nums' }}>
                  {it.pct}%
                </div>
              </div>
              <ProgressBar value={Math.min(100, it.pct)} height={5} color={it.color} />
            </div>
          ))}
          <button style={{
            padding: '14px', background: 'transparent', borderRadius: 14,
            border: `1px dashed ${Z.cyan}`, color: Z.cyan, fontWeight: 600, fontSize: 13,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            fontFamily: Z.font, cursor: 'pointer',
          }}>
            <Icon name="plus" size={14} color={Z.cyan} /> Agregar presupuesto
          </button>
        </div>
      </div>
    </div>
  );
}

// Locked Pro feature for Free users
function PresupuestosLocked() {
  return (
    <div style={{ height: '100%', position: 'relative', overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px' }}>
        <PageHeader title="Presupuestos" />
      </div>
      {/* faint preview */}
      <div style={{ filter: 'blur(8px)', opacity: 0.35, padding: '0 20px' }}>
        <div style={{ height: 120, background: Z.surface, borderRadius: 16, border: `1px solid ${Z.border}`, marginBottom: 14 }} />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{ height: 76, background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, marginBottom: 8 }} />
        ))}
      </div>

      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 100, top: 70,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        padding: '0 28px', textAlign: 'center',
      }}>
        <div style={{
          width: 84, height: 84, borderRadius: 24,
          background: 'linear-gradient(135deg, rgba(0,240,255,0.15), rgba(112,0,255,0.15))',
          border: `1px solid ${Z.cyan}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 22,
        }}>
          <Icon name="target" size={36} color={Z.cyan} />
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.6, marginBottom: 10 }}>
          Presupuestos
        </div>
        <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.5, marginBottom: 22, maxWidth: 280 }}>
          Define límites por categoría y deja que Zepo te avise cuando estés cerca. Disponibles en Pro.
        </div>
        <GradientButton full={false} height={48}>Ver planes</GradientButton>
        <div style={{ marginTop: 10, fontSize: 11, color: Z.dim }}>
          Desde $5/mes · cancela cuando quieras
        </div>
      </div>
    </div>
  );
}

// ─── Dashboard (Elite) ──────────────────────────────────────
function DashboardScreen() {
  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 100 }}>
      <div style={{ padding: '14px 20px' }}>
        <PageHeader
          title="Dashboard"
          subtitle="Mayo 2026"
          badge={<PlanBadge plan="elite" />}
        />

        {/* period selector */}
        <div style={{
          display: 'flex', background: Z.surface, borderRadius: 11, padding: 4,
          border: `1px solid ${Z.border}`, marginBottom: 16,
        }}>
          {['Semana', 'Mes', 'Año'].map((p, i) => (
            <div key={p} style={{
              flex: 1, textAlign: 'center', padding: '8px 0', borderRadius: 8,
              background: i === 1 ? Z.bg : 'transparent',
              color: i === 1 ? Z.text : Z.muted, fontSize: 12, fontWeight: 600,
            }}>{p}</div>
          ))}
        </div>

        {/* bar chart */}
        <ChartCard title="Gastos por día" subtitle="May 1 — May 8">
          <BarChartMini />
        </ChartCard>

        {/* donut + categories */}
        <ChartCard title="Por categoría" subtitle="Distribución del mes">
          <DonutLegend />
        </ChartCard>

        {/* trend line */}
        <ChartCard title="Tendencia · 6 meses" subtitle="Proyección punteada">
          <TrendLine />
        </ChartCard>

        {/* analytics insights */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <InsightCard
            icon="trending-up" color={Z.warning}
            title="Día más caro: viernes"
            body="+23% sobre tu promedio diario ($164 vs $134)"
          />
          <InsightCard
            icon="alert-triangle" color={Z.danger}
            title="Restaurantes creció +$45"
            body="vs mes anterior. Categoría con mayor variación."
          />
          <InsightCard
            icon="zap" color={Z.cyan}
            title="A este ritmo cerrarás en $2,940"
            body="Dentro del presupuesto · 2% bajo promedio del trimestre."
          />
        </div>

        {/* integrations */}
        <div style={{ marginTop: 22, fontSize: 11, color: Z.muted, letterSpacing: 1.2, fontWeight: 700, marginBottom: 10 }}>
          INTEGRACIONES
        </div>
        <IntegrationRow icon="mail" label="Gmail" sub="Último sync: hace 2h · 3 recibos" status="ok" />
        <div style={{ height: 8 }} />
        <IntegrationRow icon="cloud" label="Google Sheets" sub="Zepo Export 2026 · hace 1h" status="ok" />
      </div>
    </div>
  );
}

function ChartCard({ title, subtitle, children }) {
  return (
    <div style={{
      padding: 16, background: Z.surface, borderRadius: 16,
      border: `1px solid ${Z.border}`, marginBottom: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: -0.2 }}>{title}</div>
          <div style={{ fontSize: 11, color: Z.muted, marginTop: 2 }}>{subtitle}</div>
        </div>
      </div>
      {children}
    </div>
  );
}

function BarChartMini() {
  const data = [
    { d: '01', v: 0.6 }, { d: '02', v: 0.85 }, { d: '03', v: 0.4 },
    { d: '04', v: 0.7 }, { d: '05', v: 0.55 }, { d: '06', v: 1.0 },
    { d: '07', v: 0.78 }, { d: '08', v: 0.45 },
  ];
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 110, position: 'relative' }}>
        {/* avg line */}
        <div style={{
          position: 'absolute', left: 0, right: 0, top: '40%',
          borderTop: `1px dashed ${Z.muted}`, opacity: 0.4,
        }} />
        <div style={{
          position: 'absolute', right: 4, top: 'calc(40% - 14px)',
          fontSize: 9, color: Z.muted, fontWeight: 600,
        }}>PROM $134</div>
        {data.map((b, i) => (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: '100%', height: `${b.v * 100}%`, minHeight: 4,
              background: Z.gradient, borderRadius: 4,
              boxShadow: i === 5 ? '0 0 16px rgba(0,240,255,0.5)' : 'none',
            }} />
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
        {data.map((b, i) => (
          <div key={i} style={{ flex: 1, fontSize: 9, color: Z.muted, textAlign: 'center', fontVariantNumeric: 'tabular-nums' }}>{b.d}</div>
        ))}
      </div>
    </div>
  );
}

function DonutLegend() {
  // Simple SVG donut with 5 segments
  const segs = [
    { color: '#FF6B6B', pct: 30, label: '🍽 Comida',     value: '$840' },
    { color: '#00F0FF', pct: 22, label: '🚌 Transporte', value: '$612' },
    { color: '#7000FF', pct: 18, label: '🎮 Entret.',    value: '$510' },
    { color: '#FFB800', pct: 16, label: '🛍 Compras',    value: '$455' },
    { color: '#00E5A0', pct: 14, label: '✨ Otros',      value: '$430' },
  ];
  let cum = 0;
  const r = 50, c = 60, cx = 70, cy = 70;
  const segments = segs.map(s => {
    const start = cum;
    cum += s.pct;
    const a1 = (start / 100) * 2 * Math.PI - Math.PI / 2;
    const a2 = (cum / 100) * 2 * Math.PI - Math.PI / 2;
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2);
    const large = s.pct > 50 ? 1 : 0;
    return { ...s, d: `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z` };
  });
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <svg width={140} height={140} viewBox="0 0 140 140">
        {segments.map((s, i) => (
          <path key={i} d={s.d} fill={s.color} />
        ))}
        {/* inner cut */}
        <circle cx={cx} cy={cy} r={32} fill={Z.surface} />
        <text x={cx} y={cy - 4} textAnchor="middle" fill={Z.muted} fontSize={9} fontWeight={600} letterSpacing={0.6}>TOTAL</text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill={Z.text} fontSize={16} fontWeight={800} letterSpacing={-0.4}>$2,847</text>
      </svg>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {segs.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: 4, background: s.color }} />
            <div style={{ flex: 1, fontSize: 11, color: Z.text }}>{s.label}</div>
            <div style={{ fontSize: 11, fontWeight: 700, color: Z.text, fontVariantNumeric: 'tabular-nums' }}>{s.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TrendLine() {
  // 6 months + projection
  const pts = [
    { x: 0,   y: 60 },
    { x: 50,  y: 45 },
    { x: 100, y: 70 },
    { x: 150, y: 35 },
    { x: 200, y: 50 },
    { x: 250, y: 30 },
  ];
  const proj = { x: 300, y: 25 };
  const linePath = 'M ' + pts.map(p => `${p.x} ${p.y}`).join(' L ');
  const areaPath = linePath + ` L ${pts[pts.length - 1].x} 100 L 0 100 Z`;
  return (
    <div>
      <svg width="100%" height={130} viewBox="0 0 320 110" preserveAspectRatio="none">
        <defs>
          <linearGradient id="trendgrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.4"/>
            <stop offset="100%" stopColor="#7000FF" stopOpacity="0"/>
          </linearGradient>
          <linearGradient id="trendline" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#00F0FF"/>
            <stop offset="100%" stopColor="#7000FF"/>
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#trendgrad)" />
        <path d={linePath} fill="none" stroke="url(#trendline)" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
        {/* projection */}
        <path d={`M ${pts[pts.length - 1].x} ${pts[pts.length - 1].y} L ${proj.x} ${proj.y}`}
          fill="none" stroke={Z.warning} strokeWidth={2} strokeDasharray="4 4" strokeLinecap="round" />
        {pts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={3} fill={Z.bg} stroke="#00F0FF" strokeWidth={1.6} />
        ))}
        <circle cx={proj.x} cy={proj.y} r={4} fill={Z.warning} />
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: Z.muted, marginTop: 4, fontWeight: 600 }}>
        {['Dic', 'Ene', 'Feb', 'Mar', 'Abr', 'May', <span key="p" style={{ color: Z.warning }}>Jun</span>].map((m, i) => <span key={i}>{m}</span>)}
      </div>
      <div style={{
        marginTop: 10, padding: '8px 12px', borderRadius: 10,
        background: 'rgba(255,184,0,0.08)', border: `1px solid rgba(255,184,0,0.2)`,
        fontSize: 11, color: Z.warning, fontWeight: 600,
      }}>
        Proyección junio: $2,610 · −8% vs mayo
      </div>
    </div>
  );
}

function InsightCard({ icon, color, title, body }) {
  return (
    <div style={{
      padding: 14, background: Z.surface, borderRadius: 14,
      border: `1px solid ${Z.border}`,
      display: 'flex', gap: 12,
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 10,
        background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <Icon name={icon} size={16} color={color} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: -0.2 }}>{title}</div>
        <div style={{ fontSize: 11, color: Z.muted, marginTop: 4, lineHeight: 1.4 }}>{body}</div>
      </div>
    </div>
  );
}

function IntegrationRow({ icon, label, sub, status }) {
  return (
    <div style={{
      padding: '14px 14px', background: Z.surface, borderRadius: 14,
      border: `1px solid ${Z.border}`,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 10, background: Z.bg,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon name={icon} size={16} color={Z.cyan} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{label}</div>
        <div style={{ fontSize: 11, color: Z.muted, marginTop: 2 }}>{sub}</div>
      </div>
      <div style={{
        padding: '4px 8px', borderRadius: 7, fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
        background: 'rgba(0,229,160,0.15)', color: Z.success,
      }}>CONECTADO</div>
    </div>
  );
}

window.HistorialScreen = HistorialScreen;
window.PresupuestosScreen = PresupuestosScreen;
window.PresupuestosLocked = PresupuestosLocked;
window.DashboardScreen = DashboardScreen;
window.SectionHead = SectionHead;
window.ListBlock = ListBlock;
window.IntegrationRow = IntegrationRow;
