// Zepo · pages/approve.jsx
//   Aprobar registro + split colapsable.
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function ApproveScreen({ source = 'texto', preSplit = null, showScrollHint = false }) {
  // source: 'texto' | 'voz' | 'foto' — solo afecta el subtítulo
  // preSplit: null | 'one' | 'equal3' — qué prellenado mostrar
  // showScrollHint: cuando true, dibuja un fade + chevron en la parte inferior
  //                 para indicar que la pantalla continúa al hacer scroll
  return (
    <div style={{ height: '100%', position: 'relative' }}>
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 40 }}>
      <ScreenHeader title="Aprobar registro" right={
        <div style={{
          fontSize: 10, fontWeight: 700, padding: '4px 8px', borderRadius: 6,
          background: Z.surface, border: `1px solid ${Z.border}`, color: Z.muted, letterSpacing: 0.6,
        }}>{source.toUpperCase()}</div>
      } />

      <div style={{ padding: '0 20px' }}>
        {/* Monto grande editable */}
        <div style={{
          padding: '20px 18px', borderRadius: 16,
          background: 'linear-gradient(160deg, rgba(0,240,255,0.06), rgba(112,0,255,0.06))',
          border: `1px solid ${Z.border2}`,
          marginBottom: 14,
        }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>
            MONTO DETECTADO
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span style={{ fontSize: 22, color: Z.muted, fontWeight: 600 }}>$</span>
            <span style={{ fontSize: 48, fontWeight: 800, letterSpacing: -2, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
              <GradientText>{preSplit === 'one' ? '15.00' : preSplit === 'equal3' ? '12.00' : '68.40'}</GradientText>
            </span>
            <div style={{ flex: 1 }} />
            <Icon name="edit" size={16} color={Z.muted} />
          </div>
          <div style={{ marginTop: 6, fontSize: 12, color: Z.dim }}>USD · toca para editar</div>
        </div>

        {/* Descripción */}
        <FieldBox
          label="DESCRIPCIÓN"
          value={preSplit === 'one' ? 'Almuerzo' : preSplit === 'equal3' ? 'Taxi compartido' : 'Supermaxi La Carolina'}
          onIcon="edit"
        />

        {/* Categoría dropdown */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>CATEGORÍA</div>
          <div style={{
            height: 50, borderRadius: 12, background: Z.surface,
            border: `1px solid ${Z.border}`, padding: '0 14px',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            {(() => {
              const c = APPROVE_CATS[preSplit === 'one' ? 0 : preSplit === 'equal3' ? 1 : 0];
              return (
                <>
                  <div style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: `${c.c}18`, border: `1px solid ${c.c}40`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14,
                  }}>{c.emoji}</div>
                  <div style={{ flex: 1, fontSize: 15, fontWeight: 500 }}>{c.l}</div>
                  <Icon name="chevron-down" size={16} color={Z.muted} />
                </>
              );
            })()}
          </div>
          {/* horizontal scroll de las opciones */}
          <div style={{ display: 'flex', gap: 6, overflowX: 'auto', marginTop: 8, paddingBottom: 2 }}>
            {APPROVE_CATS.slice(1, 7).map((c, i) => (
              <div key={c.k} style={{
                padding: '6px 10px', borderRadius: 8, fontSize: 11,
                background: Z.surface, border: `1px solid ${Z.border}`,
                color: Z.muted, fontWeight: 600, whiteSpace: 'nowrap',
                display: 'flex', alignItems: 'center', gap: 5,
              }}>
                <span style={{ fontSize: 12 }}>{c.emoji}</span>{c.l}
              </div>
            ))}
          </div>
        </div>

        {/* Fecha */}
        <FieldBox label="FECHA" value="Hoy · 8 may 2026" right={<Icon name="calendar" size={16} color={Z.muted} />} />

        {/* Sección de split */}
        <SplitSection preset={preSplit} />

        {/* Botones */}
        <div style={{ marginTop: 18, marginBottom: 8 }}>
          <button style={{
            width: '100%', height: 52, borderRadius: 26,
            background: Z.success, border: 'none', color: '#0A0A0F',
            fontWeight: 700, fontSize: 16, fontFamily: Z.font, letterSpacing: -0.2,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            boxShadow: '0 4px 24px rgba(0,229,160,0.25), inset 0 1px 0 rgba(255,255,255,0.3)',
            cursor: 'pointer',
          }}>
            <Icon name="check" size={18} color="#0A0A0F" strokeWidth={3} />
            Aprobar
          </button>
          <button style={{
            marginTop: 8, width: '100%', height: 46, borderRadius: 23,
            background: 'transparent', border: 'none',
            color: Z.muted, fontWeight: 600, fontSize: 14, fontFamily: Z.font,
            cursor: 'pointer',
          }}>Cancelar</button>
        </div>
      </div>
    </div>
    {showScrollHint && (
      <>
        <div style={{
          position: 'absolute', left: 0, right: 0, bottom: 0, height: 90,
          background: 'linear-gradient(to bottom, rgba(10,10,15,0), rgba(10,10,15,0.95) 60%)',
          pointerEvents: 'none', zIndex: 50,
        }} />
        <div style={{
          position: 'absolute', left: '50%', bottom: 18, transform: 'translateX(-50%)',
          display: 'flex', alignItems: 'center', gap: 6, zIndex: 51,
          padding: '6px 12px', borderRadius: 999,
          background: 'rgba(0,240,255,0.10)', border: `1px solid rgba(0,240,255,0.30)`,
          fontSize: 11, fontWeight: 600, color: '#00F0FF', letterSpacing: 0.4,
          fontFamily: Z.font,
        }}>
          <span>desliza para ver split</span>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#00F0FF" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
        </div>
      </>
    )}
    </div>
  );
}

// Sección colapsable "Dividir gasto"
function SplitSection({ preset }) {
  // preset: null = toggle off; 'one' = Juan 50/50; 'equal3' = Maria + Pedro 33/33/33
  const open = preset !== null;

  // Construir filas de personas
  let people = [];
  if (preset === 'one') {
    people = [
      { name: 'Tú',   pct: 50, amt: 7.50, you: true, color: '#00F0FF' },
      { name: 'Juan', pct: 50, amt: 7.50, color: '#7000FF' },
    ];
  } else if (preset === 'equal3') {
    people = [
      { name: 'Tú',    pct: 33.33, amt: 4.00, you: true, color: '#00F0FF' },
      { name: 'María', pct: 33.33, amt: 4.00, color: '#7000FF' },
      { name: 'Pedro', pct: 33.34, amt: 4.00, color: '#FFB800' },
    ];
  }

  return (
    <div style={{
      marginTop: 14, borderRadius: 14,
      background: open ? 'rgba(0,240,255,0.03)' : Z.surface,
      border: `1px solid ${open ? Z.cyan : Z.border}`,
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '14px 14px', display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 10,
          background: open ? 'rgba(0,240,255,0.12)' : Z.bg,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name="user" size={15} color={open ? Z.cyan : Z.muted} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Dividir este gasto</div>
          <div style={{ fontSize: 11, color: Z.muted, marginTop: 2 }}>
            {open ? `${people.length} personas` : 'Genera cobros automáticos'}
          </div>
        </div>
        {/* toggle */}
        <div style={{
          width: 38, height: 22, borderRadius: 11,
          background: open ? Z.cyan : '#2a2a3d', position: 'relative',
        }}>
          <div style={{
            position: 'absolute', top: 2, left: open ? 18 : 2,
            width: 18, height: 18, borderRadius: 9, background: '#fff',
          }} />
        </div>
      </div>

      {open && (
        <div style={{ padding: '0 14px 14px' }}>
          {/* Barra de proporción */}
          <div style={{ height: 8, borderRadius: 4, overflow: 'hidden', display: 'flex', marginBottom: 12, background: Z.border }}>
            {people.map((p, i) => (
              <div key={i} style={{ width: `${p.pct}%`, background: p.color }} />
            ))}
          </div>

          {/* Filas */}
          {people.map((p, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
            }}>
              <div style={{
                width: 10, height: 10, borderRadius: 2, background: p.color, flexShrink: 0,
              }} />
              <div style={{
                flex: 1, height: 40, borderRadius: 10, background: Z.surface,
                border: `1px solid ${Z.border}`,
                display: 'flex', alignItems: 'center', padding: '0 10px',
                fontSize: 13, fontWeight: p.you ? 600 : 500,
                color: p.you ? Z.text : Z.text,
              }}>
                {p.name}{p.you && <span style={{ marginLeft: 6, fontSize: 10, color: Z.cyan, fontWeight: 700 }}>· TÚ</span>}
              </div>
              <div style={{
                width: 64, height: 40, borderRadius: 10, background: Z.surface,
                border: `1px solid ${Z.border}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, color: Z.text, fontVariantNumeric: 'tabular-nums',
              }}>{p.pct.toFixed(0)}%</div>
              <div style={{
                width: 70, height: 40, borderRadius: 10, background: Z.surface,
                border: `1px solid ${Z.border}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, color: Z.cyan, fontVariantNumeric: 'tabular-nums',
              }}>${p.amt.toFixed(2)}</div>
              {!p.you && (
                <div style={{
                  width: 30, height: 40, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon name="x" size={14} color={Z.dim} />
                </div>
              )}
            </div>
          ))}

          {/* Suma */}
          <div style={{
            marginTop: 4, padding: '8px 10px', borderRadius: 8,
            background: 'rgba(0,229,160,0.08)', border: `1px solid rgba(0,229,160,0.2)`,
            display: 'flex', justifyContent: 'space-between', fontSize: 11, fontWeight: 600,
          }}>
            <span style={{ color: Z.muted }}>Suma de partes</span>
            <span style={{ color: Z.success }}>100% ✓</span>
          </div>

          {/* Acciones */}
          <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
            <button style={{
              flex: 1, height: 38, borderRadius: 10,
              background: Z.surface, border: `1px dashed ${Z.cyan}`,
              color: Z.cyan, fontWeight: 600, fontSize: 12, fontFamily: Z.font,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}>
              <Icon name="plus" size={12} color={Z.cyan} /> Agregar persona
            </button>
            <button style={{
              flex: 1, height: 38, borderRadius: 10,
              background: 'rgba(112,0,255,0.08)', border: `1px solid rgba(112,0,255,0.3)`,
              color: '#B794F6', fontWeight: 600, fontSize: 12, fontFamily: Z.font,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}>
              <Icon name="repeat" size={12} color="#B794F6" /> Partes iguales
            </button>
          </div>

          {/* Hint */}
          <div style={{
            marginTop: 10, padding: '8px 10px', borderRadius: 8,
            background: 'rgba(0,240,255,0.05)',
            fontSize: 11, color: Z.muted, lineHeight: 1.5,
            display: 'flex', gap: 6, alignItems: 'flex-start',
          }}>
            <Icon name="bell" size={11} color={Z.cyan} />
            <span>Al aprobar, se crearán cobros pendientes en la sección Cobros.</span>
          </div>
        </div>
      )}
    </div>
  );
}

window.ApproveScreen = ApproveScreen;
window.SplitSection = SplitSection;