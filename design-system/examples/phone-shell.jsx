// Zepo · PhoneShell — wraps a screen in the dark Zepo background with
// status bar, optional tab bar and FAB, and the iOS home indicator.
// Lighter chrome than IOSDevice; used inside DesignCanvas artboards.

function PhoneShell({ children, statusBar = true, time = '9:41', tabBar, fab, w = SCREEN_W, h = SCREEN_H }) {
  return (
    <div style={{
      width: w, height: h, background: Z.bg, color: Z.text,
      fontFamily: Z.font, position: 'relative', overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      {statusBar && <ZepoStatusBar time={time} />}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {children}
      </div>
      {fab}
      {tabBar}
      {/* home indicator */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: 34,
        display: 'flex', justifyContent: 'center', alignItems: 'flex-end',
        paddingBottom: 8, pointerEvents: 'none', zIndex: 200,
      }}>
        <div style={{ width: 139, height: 5, borderRadius: 100, background: 'rgba(255,255,255,0.5)' }} />
      </div>
    </div>
  );
}
window.PhoneShell = PhoneShell;

function ZepoStatusBar({ time = '9:41' }) {
  return (
    <div style={{
      height: 54, paddingTop: 18, display: 'flex', alignItems: 'center',
      justifyContent: 'space-between', padding: '18px 32px 0',
      position: 'relative', zIndex: 30,
    }}>
      <div style={{ fontSize: 17, fontWeight: 600, letterSpacing: -0.3, color: Z.text }}>{time}</div>
      <div style={{
        position: 'absolute', top: 11, left: '50%', transform: 'translateX(-50%)',
        width: 122, height: 36, borderRadius: 22, background: '#000',
      }} />
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <svg width="17" height="11" viewBox="0 0 17 11"><path d="M8.5 2.5C10.7 2.5 12.7 3.4 14.2 4.8L15.2 3.8C13.4 2 10.9 .8 8.5 .8C6.1 .8 3.6 2 1.8 3.8L2.8 4.8C4.3 3.4 6.3 2.5 8.5 2.5Z" fill="#fff"/><circle cx="8.5" cy="9" r="1.5" fill="#fff"/></svg>
        <svg width="15" height="11" viewBox="0 0 15 11"><rect x="0" y="6" width="2.5" height="4" rx="0.5" fill="#fff"/><rect x="4" y="4" width="2.5" height="6" rx="0.5" fill="#fff"/><rect x="8" y="2" width="2.5" height="8" rx="0.5" fill="#fff"/><rect x="12" y="0" width="2.5" height="10" rx="0.5" fill="#fff"/></svg>
        <svg width="25" height="12" viewBox="0 0 25 12"><rect x="0.5" y="0.5" width="22" height="11" rx="3" stroke="#fff" strokeOpacity="0.4" fill="none"/><rect x="2" y="2" width="18" height="8" rx="1.5" fill={Z.success}/><rect x="23" y="4" width="1.5" height="4" rx="0.5" fill="#fff" fillOpacity="0.4"/></svg>
      </div>
    </div>
  );
}
window.ZepoStatusBar = ZepoStatusBar;
