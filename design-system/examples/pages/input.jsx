// Zepo input sheet — 5 modes (form, AI text, voice, photo, file)

// Sheet shell — bottom sheet that occupies 85% of phone screen
function InputSheet({ mode = 'ai', children, plan = 'elite' }) {
  const tabs = [
    { key: 'ai',    label: 'Texto',   icon: 'edit',      locked: false },
    { key: 'voice', label: 'Voz',     icon: 'mic',       locked: false },
    { key: 'photo', label: 'Foto',    icon: 'camera',    locked: plan !== 'elite' },
    { key: 'file',  label: 'Archivo', icon: 'paperclip', locked: plan !== 'elite' },
  ];
  return (
    <div style={{ height: '100%', position: 'relative', overflow: 'hidden' }}>
      {/* dimmed home behind */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, rgba(10,10,15,0.4) 0%, rgba(10,10,15,0.85) 100%)',
        backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
      }} />
      {/* hint of home behind */}
      <div style={{ position: 'absolute', top: 60, left: 20, right: 20, opacity: 0.25 }}>
        <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.6, color: Z.text }}>Hola, Andrea</div>
        <div style={{ fontSize: 12, color: Z.muted, marginTop: 2 }}>Jueves 8 de mayo</div>
      </div>

      {/* sheet */}
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        height: '88%', background: Z.bg,
        borderTopLeftRadius: 28, borderTopRightRadius: 28,
        borderTop: `1px solid ${Z.border2}`,
        boxShadow: '0 -20px 60px rgba(0,240,255,0.08), 0 -2px 0 rgba(255,255,255,0.04)',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* grabber */}
        <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 10, paddingBottom: 4 }}>
          <div style={{ width: 36, height: 4, borderRadius: 2, background: '#3a3a55' }} />
        </div>

        {/* tabs */}
        <div style={{ display: 'flex', gap: 6, padding: '12px 16px 0', overflowX: 'auto' }}>
          {tabs.map(t => {
            const active = t.key === mode;
            return (
              <div key={t.key} style={{
                padding: '8px 12px', borderRadius: 10, fontSize: 12, fontWeight: 600,
                background: active ? Z.surface2 : 'transparent',
                border: `1px solid ${active ? Z.cyan : Z.border}`,
                color: active ? Z.text : Z.muted,
                display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
                position: 'relative', flexShrink: 0,
              }}>
                {t.icon && <Icon name={t.icon} size={12} color={active ? Z.cyan : Z.muted} />}
                {t.label}
                {t.locked && <LockIcon size={10} color={Z.cyan} />}
              </div>
            );
          })}
        </div>

        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          {children}
        </div>
      </div>
    </div>
  );
}

// ─── Text mode ──────────────────────────────────────────────
function AITextMode() {
  return (
    <InputSheet mode="ai">
      <div style={{ padding: '24px 22px 20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <Icon name="edit" size={16} color={Z.cyan} />
          <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: -0.2 }}>Describe tu gasto</div>
        </div>

        <div style={{
          padding: 16, borderRadius: 14, background: Z.surface,
          border: `1px solid ${Z.cyan}`,
          boxShadow: '0 0 0 4px rgba(0,240,255,0.08)',
          minHeight: 110,
        }}>
          <div style={{ fontSize: 16, color: Z.text, lineHeight: 1.5, fontWeight: 500 }}>
            almuerzo 15 dividido con juan
          </div>
          <div style={{ marginTop: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: 6 }}>
              <div style={{ width: 30, height: 30, borderRadius: 15, background: Z.surface2, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon name="mic" size={13} color={Z.muted} />
              </div>
            </div>
            <div style={{ fontSize: 11, color: Z.dim }}>43/500</div>
          </div>
        </div>

        {/* analyze button */}
        <div style={{ marginTop: 12 }}>
          <button style={{
            width: '100%', height: 46, borderRadius: 12,
            background: 'rgba(0,240,255,0.08)', border: `1px solid ${Z.cyan}`,
            color: Z.cyan, fontWeight: 700, fontSize: 14,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            cursor: 'pointer', fontFamily: Z.font,
          }}>
            <Icon name="arrow-right" size={14} color={Z.cyan} /> Analizar
          </button>
        </div>

        {/* result preview */}
        <div style={{ marginTop: 18 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 8 }}>
            DETECTADO
          </div>
          <GradientBorder radius={16} padding={1}>
            <div style={{ padding: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <CategoryChip k="food" size={36} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>Comida</div>
                    <div style={{ fontSize: 11, color: Z.muted }}>2 cafés y un sándwich</div>
                  </div>
                </div>
                <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.8, fontVariantNumeric: 'tabular-nums' }}>
                  <GradientText>$8.50</GradientText>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {[
                  { l: 'La Esquina', i: 'flag' },
                  { l: 'Hoy · 8 may', i: 'calendar' },
                  { l: 'USD', i: 'globe' },
                ].map((c, i) => (
                  <div key={i} style={{
                    padding: '5px 9px', borderRadius: 8, fontSize: 11,
                    background: 'rgba(0,240,255,0.08)', color: Z.cyan,
                    display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600,
                  }}>
                    <Icon name={c.i} size={10} color={Z.cyan} /> {c.l}
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 10, fontSize: 11, color: Z.dim, display: 'flex', alignItems: 'center', gap: 4 }}>
                <Icon name="edit" size={10} color={Z.dim} /> Toca cualquier campo para editar
              </div>
            </div>
          </GradientBorder>
        </div>

        <div style={{ flex: 1 }} />
        <GradientButton>Revisar y aprobar</GradientButton>
      </div>
    </InputSheet>
  );
}

// ─── Voice mode ─────────────────────────────────────────────
function VoiceMode() {
  return (
    <InputSheet mode="voice">
      <div style={{
        padding: '24px 22px 20px', height: '100%',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        background: 'radial-gradient(circle at 50% 32%, rgba(0,240,255,0.12) 0%, transparent 60%)',
      }}>
        <div style={{ fontSize: 13, color: Z.muted, marginTop: 10, fontWeight: 500 }}>Habla ahora…</div>

        {/* waveform circles */}
        <div style={{ position: 'relative', width: 200, height: 200, marginTop: 36 }}>
          {[1.0, 0.78, 0.56, 0.34].map((s, i) => (
            <div key={i} style={{
              position: 'absolute', top: '50%', left: '50%',
              width: s * 200, height: s * 200,
              transform: 'translate(-50%, -50%)',
              borderRadius: '50%',
              background: `radial-gradient(circle, rgba(0,240,255,${0.15 + i*0.05}) 0%, transparent 70%)`,
              border: `1px solid rgba(0,240,255,${0.4 - i*0.08})`,
            }} />
          ))}
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 80, height: 80, borderRadius: 40,
            background: Z.gradient,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 32px rgba(0,240,255,0.5)',
          }}>
            <Icon name="mic" size={32} color="#0A0A0F" strokeWidth={2.4} />
          </div>
        </div>

        {/* transcription bar */}
        <div style={{ marginTop: 36, fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600 }}>TRANSCRIPCIÓN</div>
        <div style={{
          marginTop: 8, padding: '12px 16px', borderRadius: 14,
          background: Z.surface, border: `1px solid ${Z.border}`,
          fontSize: 14, color: Z.text, lineHeight: 1.4, width: '100%', textAlign: 'center',
          fontFamily: Z.mono,
        }}>
          "Taxi doce dólares <span style={{ background: 'rgba(0,240,255,0.15)', padding: '0 4px', borderRadius: 3, color: Z.cyan }}>dividido</span> con maria y pedro"
        </div>

        {/* live waveform line */}
        <div style={{ marginTop: 22, display: 'flex', alignItems: 'center', gap: 3, height: 40 }}>
          {[12, 18, 8, 28, 14, 32, 10, 22, 36, 16, 24, 12, 28, 18, 10, 14, 22, 16, 8, 20].map((h, i) => (
            <div key={i} style={{
              width: 3, height: h, borderRadius: 1.5, background: Z.cyan, opacity: 0.5 + (h / 80),
            }} />
          ))}
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ display: 'flex', gap: 10, width: '100%' }}>
          <button style={{
            height: 50, padding: '0 18px', borderRadius: 25,
            background: 'transparent', border: `1px solid ${Z.border}`,
            color: Z.muted, fontWeight: 600, fontSize: 13, fontFamily: Z.font,
          }}>Cancelar</button>
          <div style={{ flex: 1 }}><GradientButton height={50}>Revisar y aprobar</GradientButton></div>
        </div>
      </div>
    </InputSheet>
  );
}

// ─── Photo mode ────────────────────────────────────────────
function PhotoMode() {
  return (
    <InputSheet mode="photo">
      <div style={{ padding: '24px 22px 20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <Icon name="camera" size={16} color={Z.cyan} />
          <div style={{ fontSize: 14, fontWeight: 700 }}>Foto del recibo</div>
          <PlanBadge plan="elite" />
        </div>

        {/* receipt placeholder */}
        <div style={{
          height: 220, borderRadius: 16,
          background: 'repeating-linear-gradient(135deg, #1a1a25 0px, #1a1a25 8px, #15151f 8px, #15151f 16px)',
          border: `1px solid ${Z.border}`,
          position: 'relative', overflow: 'hidden',
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
          padding: 20,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ fontFamily: Z.mono, fontSize: 10, color: Z.muted, opacity: 0.6 }}>
              [ recibo capturado ]
            </div>
            <div style={{
              padding: '4px 10px', borderRadius: 16,
              background: 'rgba(0,240,255,0.15)', color: Z.cyan,
              fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <div style={{ width: 5, height: 5, borderRadius: 3, background: Z.cyan, animation: 'none' }} />
              ANALIZANDO
            </div>
          </div>
          {/* scan line */}
          <div style={{
            position: 'absolute', top: '50%', left: 0, right: 0, height: 2,
            background: 'linear-gradient(90deg, transparent, #00F0FF, transparent)',
            boxShadow: '0 0 12px #00F0FF',
          }} />
          {/* corner brackets */}
          {[
            { t: 12, l: 12, br: '0 0 0 0' },
            { t: 12, r: 12 },
            { b: 12, l: 12 },
            { b: 12, r: 12 },
          ].map((p, i) => (
            <div key={i} style={{
              position: 'absolute', ...p, width: 18, height: 18,
              borderTop: i < 2 ? `2px solid ${Z.cyan}` : 'none',
              borderBottom: i >= 2 ? `2px solid ${Z.cyan}` : 'none',
              borderLeft: i % 2 === 0 ? `2px solid ${Z.cyan}` : 'none',
              borderRight: i % 2 === 1 ? `2px solid ${Z.cyan}` : 'none',
            }} />
          ))}
        </div>

        {/* extracted fields */}
        <div style={{ marginTop: 16, fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 8 }}>
          DATOS EXTRAÍDOS
        </div>
        <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, padding: '4px 0' }}>
          {[
            { k: 'Comercio', v: 'Supermaxi La Carolina', i: 'flag' },
            { k: 'Total',    v: '$68.40', big: true, i: 'globe' },
            { k: 'Fecha',    v: '8 may 2026 · 14:32', i: 'calendar' },
            { k: 'Items',    v: '12 productos', i: 'list' },
          ].map((r, i, arr) => (
            <div key={i} style={{
              padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              borderBottom: i < arr.length - 1 ? `1px solid ${Z.border}` : 'none',
            }}>
              <div style={{ fontSize: 12, color: Z.muted }}>{r.k}</div>
              <div style={{ fontSize: r.big ? 16 : 13, fontWeight: r.big ? 700 : 500, color: Z.text, letterSpacing: r.big ? -0.4 : 0 }}>
                {r.big ? <GradientText>{r.v}</GradientText> : r.v}
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1 }} />
        <GradientButton>Revisar y aprobar</GradientButton>
      </div>
    </InputSheet>
  );
}

// ─── File mode (Archivo) ───────────────────────────────────
function FileMode() {
  return (
    <InputSheet mode="file">
      <div style={{ padding: '24px 22px 20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <Icon name="paperclip" size={16} color={Z.cyan} />
          <div style={{ fontSize: 14, fontWeight: 700 }}>Importar archivo</div>
          <PlanBadge plan="elite" />
        </div>

        {/* Dropzone */}
        <div style={{
          padding: '24px 18px', borderRadius: 16,
          background: 'rgba(0,240,255,0.04)',
          border: `1.5px dashed ${Z.cyan}`,
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
        }}>
          <div style={{
            width: 56, height: 56, borderRadius: 14,
            background: 'linear-gradient(135deg, rgba(0,240,255,0.12), rgba(112,0,255,0.10))',
            border: `1px solid ${Z.cyan}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 24px rgba(0,240,255,0.15)',
          }}>
            <Icon name="upload" size={24} color={Z.cyan} />
          </div>
          <div style={{ fontSize: 14, fontWeight: 700, textAlign: 'center' }}>Sube un PDF, Excel o CSV</div>
          <div style={{ fontSize: 11, color: Z.muted, textAlign: 'center', lineHeight: 1.4 }}>
            Estado de cuenta, factura electrónica o exportación bancaria
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
            {['PDF', 'XLSX', 'CSV', 'XML'].map(t => (
              <div key={t} style={{
                padding: '3px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700,
                background: Z.bg, color: Z.muted, letterSpacing: 0.6, fontFamily: Z.mono,
              }}>{t}</div>
            ))}
          </div>
        </div>

        {/* Selected file */}
        <div style={{ marginTop: 14, fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 8 }}>
          ARCHIVO SELECCIONADO
        </div>
        <div style={{
          padding: '14px 14px', background: Z.surface, borderRadius: 14,
          border: `1px solid ${Z.cyan}`, boxShadow: '0 0 0 4px rgba(0,240,255,0.06)',
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <div style={{
            width: 40, height: 48, borderRadius: 6,
            background: 'linear-gradient(160deg, rgba(255,107,107,0.18), rgba(255,107,107,0.06))',
            border: `1px solid rgba(255,107,107,0.4)`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 9, fontWeight: 800, color: Z.danger, letterSpacing: 0.6,
          }}>PDF</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 13, fontWeight: 600, color: Z.text,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>estado_cuenta_mayo_2026.pdf</div>
            <div style={{ fontSize: 11, color: Z.muted, marginTop: 2, fontFamily: Z.mono }}>
              182 KB · 3 páginas
            </div>
          </div>
          <Icon name="x" size={16} color={Z.muted} />
        </div>

        {/* Progress / preview */}
        <div style={{ marginTop: 14, fontSize: 11, color: Z.muted, letterSpacing: 1, fontWeight: 600, marginBottom: 8 }}>
          GASTOS DETECTADOS · 12
        </div>
        <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, padding: '4px 14px' }}>
          {[
            { cat: 'market', desc: 'Supermaxi · La Carolina', amt: '68.40', d: '2 may' },
            { cat: 'rent',   desc: 'Arriendo Cumbayá',        amt: '650.00', d: '3 may' },
            { cat: 'food',   desc: 'KFC · Iñaquito',          amt: '14.20', d: '4 may' },
          ].map((r, i, arr) => (
            <div key={i}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0' }}>
                <CategoryChip k={r.cat} size={32} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.desc}</div>
                  <div style={{ fontSize: 11, color: Z.muted, marginTop: 2 }}>{r.d}</div>
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: Z.text }}>
                  −${r.amt}
                </div>
                <div style={{
                  width: 18, height: 18, borderRadius: 5,
                  background: Z.cyan, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon name="check" size={11} color="#0A0A0F" strokeWidth={3.4} />
                </div>
              </div>
              {i < arr.length - 1 && <div style={{ height: 1, background: Z.border }} />}
            </div>
          ))}
          <div style={{
            padding: '10px 0', textAlign: 'center', fontSize: 11, color: Z.cyan, fontWeight: 600,
            borderTop: `1px solid ${Z.border}`,
          }}>+9 gastos más · ver todos</div>
        </div>

        <div style={{ flex: 1 }} />
        <GradientButton>Revisar y aprobar</GradientButton>
      </div>
    </InputSheet>
  );
}

window.InputSheet = InputSheet;
window.AITextMode = AITextMode;
window.VoiceMode = VoiceMode;
window.PhotoMode = PhotoMode;
window.FileMode = FileMode;
