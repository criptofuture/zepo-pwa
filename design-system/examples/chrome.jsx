// Zepo · app chrome — TabBar, FAB, PageHeader, PlanBadge, ProgressBar.
// The recurring navigation + status furniture for the main tab screens.

// Tab bar — sits at the bottom on the 5 main pages.
function TabBar({ active = 'home', planLevel = 'free' }) {
  const tabs = [
    { key: 'home',    icon: 'home',   locked: false, label: 'Home' },
    { key: 'budget',  icon: 'target', locked: planLevel === 'free', label: 'Presup.' },
    { key: 'fab',     icon: 'plus' },
    { key: 'cobros',  icon: 'users',  locked: false, label: 'Cobros' },
    { key: 'dash',    icon: 'chart',  locked: planLevel !== 'elite', label: 'Dash' },
  ];
  return (
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0,
      height: 84, paddingBottom: 24, paddingTop: 8,
      background: Z.surface, borderTop: `1px solid ${Z.border}`,
      display: 'flex', alignItems: 'center', justifyContent: 'space-around',
      zIndex: 100,
    }}>
      {tabs.map(t => {
        if (t.key === 'fab') {
          return <div key={t.key} style={{ width: 64 }} />; // gap for FAB
        }
        const isActive = t.key === active;
        const color = isActive ? Z.cyan : Z.muted;
        return (
          <div key={t.key} style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
            position: 'relative', width: 56,
          }}>
            <div style={{ position: 'relative' }}>
              <Icon name={t.icon} size={22} color={color} strokeWidth={isActive ? 2.4 : 2} />
              {t.locked && (
                <div style={{
                  position: 'absolute', top: -4, right: -8,
                  width: 14, height: 14, borderRadius: 7,
                  background: Z.surface2, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <LockIcon size={9} color={Z.cyan} />
                </div>
              )}
            </div>
            <div style={{
              fontSize: 9, fontWeight: isActive ? 700 : 600,
              color, letterSpacing: 0.2, lineHeight: 1,
            }}>{t.label}</div>
          </div>
        );
      })}
    </div>
  );
}
window.TabBar = TabBar;

// FAB — center button that overlaps the TabBar
function FAB({ pulse = false }) {
  return (
    <div style={{
      position: 'absolute', left: '50%', bottom: 38,
      transform: 'translateX(-50%)', zIndex: 110,
    }}>
      <div style={{
        width: 64, height: 64, borderRadius: 32,
        background: Z.gradient,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 0 0 4px #0A0A0F, 0 8px 32px rgba(0,240,255,0.4), 0 0 48px rgba(112,0,255,0.3)',
        position: 'relative',
      }}>
        {pulse && (
          <div style={{
            position: 'absolute', inset: -8, borderRadius: 40,
            border: `2px solid ${Z.cyan}`, opacity: 0.4,
          }} />
        )}
        <Icon name="plus" size={28} color="#0A0A0F" strokeWidth={2.6} />
      </div>
    </div>
  );
}
window.FAB = FAB;

// PageHeader — shared header for the 5 main pages
//   - Always: title (+ optional subtitle and right-side adornment)
//   - Always: settings circle button
//   - Optional: bell with unread indicator (Home only, by convention)
function PageHeader({ title, subtitle, badge, showNotif = false, showSettings = true, hasUnread = true, big = false }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      marginBottom: 14, gap: 12,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: big ? 28 : 22, fontWeight: 700, letterSpacing: big ? -0.8 : -0.6,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</span>
          {badge}
        </div>
        {subtitle && <div style={{ fontSize: 12, color: Z.muted, marginTop: 2 }}>{subtitle}</div>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {showNotif && <HeaderIconButton icon="bell" unread={hasUnread} />}
        {showSettings && <HeaderIconButton icon="settings" />}
      </div>
    </div>
  );
}
window.PageHeader = PageHeader;

// Plan badge — small label used in headers, cards, hero rows
function PlanBadge({ plan = 'free' }) {
  const map = {
    free:  { bg: '#FFB80020', fg: Z.warning, label: 'FREE' },
    pro:   { bg: '#00F0FF18', fg: Z.cyan,    label: 'PRO' },
    elite: { bg: Z.gradient,  fg: '#0A0A0F', label: 'ELITE' },
  };
  const m = map[plan];
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: 1,
      padding: '3px 8px', borderRadius: 6,
      background: m.bg, color: m.fg,
    }}>{m.label}</span>
  );
}
window.PlanBadge = PlanBadge;

// ProgressBar — colored progress meter (auto-colors by % when no color given)
function ProgressBar({ value = 50, height = 6, color, bg = Z.border, gradient = false }) {
  const c = color || (value > 90 ? Z.danger : value > 70 ? Z.warning : Z.success);
  return (
    <div style={{ width: '100%', height, background: bg, borderRadius: height / 2, overflow: 'hidden' }}>
      <div style={{
        width: `${Math.min(100, value)}%`, height: '100%',
        background: gradient ? Z.gradient : c, borderRadius: height / 2,
      }} />
    </div>
  );
}
window.ProgressBar = ProgressBar;
