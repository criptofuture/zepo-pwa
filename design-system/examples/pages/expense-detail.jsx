// Zepo · pages/expense-detail.jsx
//   Detalle / Editar gasto · con recibo · split (read-only).
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function ExpenseDetailScreen({ withSplit = false }) {
  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 130 }}>
      <ScreenHeader title="Editar gasto" right={
        <div style={{
          fontSize: 10, fontWeight: 700, padding: '4px 8px', borderRadius: 6,
          background: Z.surface, border: `1px solid ${Z.border}`, color: Z.muted,
          letterSpacing: 0.6, display: 'flex', alignItems: 'center', gap: 4,
        }}>
          <Icon name="camera" size={10} color={Z.muted} /> FOTO
        </div>
      } />

      <div style={{ padding: '0 20px' }}>
        {/* Monto editable */}
        <div style={{
          padding: '20px 18px', borderRadius: 16,
          background: 'linear-gradient(160deg, rgba(0,240,255,0.06), rgba(112,0,255,0.06))',
          border: `1px solid ${Z.border2}`,
          marginBottom: 14,
        }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>
            MONTO
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span style={{ fontSize: 22, color: Z.muted, fontWeight: 600 }}>$</span>
            <span style={{ fontSize: 48, fontWeight: 800, letterSpacing: -2, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
              <GradientText>{withSplit ? '15.00' : '68.40'}</GradientText>
            </span>
            <div style={{ flex: 1 }} />
            <Icon name="edit" size={16} color={Z.muted} />
          </div>
          <div style={{ marginTop: 6, fontSize: 12, color: Z.dim }}>USD · toca para editar</div>
        </div>

        <FieldBox
          label="DESCRIPCIÓN"
          value={withSplit ? 'Almuerzo con Juan' : 'Supermaxi La Carolina'}
          onIcon="edit"
        />

        {/* Categoría */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>CATEGORÍA</div>
          <div style={{
            height: 50, borderRadius: 12, background: Z.surface,
            border: `1px solid ${Z.border}`, padding: '0 14px',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            {(() => {
              const c = APPROVE_CATS[0]; // Comida
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
        </div>

        <FieldBox label="FECHA" value="4 may 2026 · 13:24" right={<Icon name="calendar" size={16} color={Z.muted} />} />

        {/* Recibo adjunto */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 6 }}>RECIBO ADJUNTO</div>
          <div style={{
            padding: '12px 14px', borderRadius: 12, background: Z.surface,
            border: `1px solid ${Z.border}`,
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            {/* thumbnail */}
            <div style={{
              width: 56, height: 64, borderRadius: 8, flexShrink: 0,
              background: 'repeating-linear-gradient(135deg, #1a1a25 0px, #1a1a25 6px, #15151f 6px, #15151f 12px)',
              border: `1px solid ${Z.border2}`,
              position: 'relative', overflow: 'hidden',
            }}>
              <div style={{
                position: 'absolute', inset: 4,
                border: `1px dashed ${Z.cyan}`, borderRadius: 4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon name="image" size={14} color={Z.cyan} />
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>recibo_supermaxi.jpg</div>
              <div style={{ fontSize: 11, color: Z.muted, marginTop: 2, fontFamily: Z.mono }}>342 KB · capturado el 4 may</div>
            </div>
            <div style={{
              padding: '6px 10px', borderRadius: 8,
              background: 'rgba(0,240,255,0.08)', border: `1px solid rgba(0,240,255,0.25)`,
              color: Z.cyan, fontSize: 11, fontWeight: 700, letterSpacing: 0.4,
              display: 'flex', alignItems: 'center', gap: 4,
            }}>
              <Icon name="image" size={11} color={Z.cyan} /> VER
            </div>
          </div>
        </div>

        {/* Split (solo lectura) */}
        {withSplit && (
          <div style={{
            marginTop: 14, borderRadius: 14,
            background: 'rgba(112,0,255,0.04)',
            border: `1px solid rgba(112,0,255,0.25)`,
            overflow: 'hidden',
          }}>
            <div style={{ padding: '14px 14px', display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 10,
                background: 'rgba(112,0,255,0.18)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon name="users" size={15} color="#B794F6" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 600 }}>Dividido con 1 persona</div>
                <div style={{ fontSize: 11, color: Z.muted, marginTop: 2 }}>Solo lectura · ya generó cobros</div>
              </div>
              <Icon name="lock" size={13} color={Z.muted} />
            </div>
            <div style={{ padding: '0 14px 14px' }}>
              {/* barra proporción */}
              <div style={{ height: 6, borderRadius: 3, overflow: 'hidden', display: 'flex', marginBottom: 10, background: Z.border }}>
                <div style={{ width: '50%', background: Z.cyan }} />
                <div style={{ width: '50%', background: Z.purple }} />
              </div>
              {[
                { name: 'Tú',   pct: 50, amt: 7.50, you: true, color: Z.cyan },
                { name: 'Juan', pct: 50, amt: 7.50, color: Z.purple },
              ].map((p, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0',
                }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: p.color, flexShrink: 0 }} />
                  <div style={{ flex: 1, fontSize: 13, fontWeight: p.you ? 600 : 500 }}>
                    {p.name}
                    {p.you && <span style={{ marginLeft: 6, fontSize: 9, color: Z.cyan, fontWeight: 700 }}>· TÚ</span>}
                  </div>
                  <div style={{ fontSize: 12, color: Z.muted, fontVariantNumeric: 'tabular-nums' }}>{p.pct}%</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: Z.text, fontVariantNumeric: 'tabular-nums', minWidth: 56, textAlign: 'right' }}>
                    ${p.amt.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Guardar (visible porque "se editó algo") */}
        <div style={{ marginTop: 22 }}>
          <GradientButton>Guardar cambios</GradientButton>
        </div>

        {/* Eliminar */}
        <button style={{
          marginTop: 14, width: '100%', height: 46, borderRadius: 23,
          background: 'transparent', border: 'none',
          color: Z.danger, fontWeight: 600, fontSize: 14, fontFamily: Z.font,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          cursor: 'pointer',
        }}>
          <Icon name="trash" size={14} color={Z.danger} /> Eliminar gasto
        </button>
      </div>
    </div>
  );
}
window.ExpenseDetailScreen = ExpenseDetailScreen;