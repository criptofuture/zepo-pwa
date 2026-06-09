// Zepo · pages/payment.jsx
//   Flujo PayPhone: pre-checkout → procesando → éxito / fallido.
// Depends on window-globals from components/* (Z, Icon, GradientText,
// GradientButton, ScreenHeader, FieldBox, APPROVE_CATS, PasswordField, …).

function CheckoutScreen({ plan = 'pro' }) {
  const isElite = plan === 'elite';
  const price = isElite ? 10.00 : 5.00;
  const name = isElite ? 'Elite' : 'Pro';
  const features = isElite
    ? ['Todo de Pro', 'Foto de recibo · OCR', 'Importar PDF/CSV', 'Dashboard + analytics']
    : ['IA · texto + voz', 'Historial ilimitado', 'Multi-moneda LATAM', 'Exportar CSV'];

  return (
    <div style={{ height: '100%', overflow: 'auto', paddingBottom: 40 }}>
      <ScreenHeader title="Confirmar plan" />

      <div style={{ padding: '0 20px' }}>
        {/* Plan card compacta */}
        <div style={{
          padding: 1.5, borderRadius: 18,
          background: isElite ? Z.gradient : 'rgba(0,240,255,0.5)',
          boxShadow: isElite ? '0 0 32px rgba(0,240,255,0.18), 0 0 64px rgba(112,0,255,0.12)' : 'none',
        }}>
          <div style={{
            padding: '18px 16px', borderRadius: 16.5,
            background: isElite
              ? 'linear-gradient(160deg, rgba(0,240,255,0.06) 0%, rgba(112,0,255,0.08) 100%)'
              : Z.surface,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <PlanBadge plan={plan} />
              <span style={{ fontSize: 13, color: Z.muted }}>Plan seleccionado</span>
              <div style={{ flex: 1 }} />
              <span style={{
                fontSize: 10, fontWeight: 700, padding: '3px 7px', borderRadius: 5, letterSpacing: 0.5,
                background: 'rgba(0,229,160,0.15)', color: Z.success,
              }}>−2 MESES</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 12 }}>
              <span style={{
                fontSize: 36, fontWeight: 800, letterSpacing: -1.2, fontVariantNumeric: 'tabular-nums',
              }}>
                <GradientText>${price.toFixed(2)}</GradientText>
              </span>
              <span style={{ fontSize: 13, color: Z.muted, fontWeight: 500 }}>/mes</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {features.map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: Z.text }}>
                  <div style={{
                    width: 16, height: 16, borderRadius: 8,
                    background: 'rgba(0,240,255,0.12)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Icon name="check" size={10} color={Z.cyan} strokeWidth={3} />
                  </div>
                  {f}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Selector mensual/anual */}
        <div style={{
          display: 'flex', background: Z.surface, borderRadius: 11, padding: 4,
          border: `1px solid ${Z.border}`, marginTop: 18, position: 'relative',
        }}>
          <div style={{
            flex: 1, textAlign: 'center', padding: '8px 0', borderRadius: 8,
            background: Z.bg, color: Z.text, fontSize: 13, fontWeight: 600,
          }}>Mensual · ${price.toFixed(0)}</div>
          <div style={{
            flex: 1, textAlign: 'center', padding: '8px 0',
            color: Z.muted, fontSize: 13, fontWeight: 500,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}>Anual · ${(price * 10).toFixed(0)} <span style={{
            fontSize: 9, fontWeight: 700, padding: '2px 5px', borderRadius: 4,
            background: 'rgba(0,229,160,0.2)', color: Z.success, letterSpacing: 0.4,
          }}>AHORRA</span></div>
        </div>

        {/* Resumen de pago */}
        <div style={{ marginTop: 22 }}>
          <div style={{ fontSize: 11, color: Z.muted, letterSpacing: 1.4, fontWeight: 700, marginBottom: 8, paddingLeft: 4 }}>
            RESUMEN DE PAGO
          </div>
          <div style={{ background: Z.surface, borderRadius: 14, border: `1px solid ${Z.border}`, overflow: 'hidden' }}>
            <SummaryRow label={`Plan ${name}`} value={`$${price.toFixed(2)}/mes`} />
            <SummaryRow label="Impuesto" value="$0.00" />
            <SummaryRow label="Total hoy" value={`$${price.toFixed(2)}`} total />
          </div>
        </div>

        {/* CTA PayPhone */}
        <div style={{ marginTop: 20 }}>
          <button style={{
            width: '100%', height: 56, borderRadius: 28,
            background: Z.gradient, border: 'none', color: '#0A0A0F',
            fontWeight: 700, fontSize: 16, fontFamily: Z.font, letterSpacing: -0.2,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            boxShadow: '0 4px 24px rgba(0, 240, 255, 0.25), inset 0 1px 0 rgba(255,255,255,0.3)',
            cursor: 'pointer',
          }}>
            <Icon name="lock" size={16} color="#0A0A0F" strokeWidth={2.4} />
            Pagar ${price.toFixed(2)} con PayPhone
          </button>
        </div>

        <div style={{
          marginTop: 12, padding: '10px 12px', borderRadius: 10,
          background: 'rgba(0,240,255,0.04)',
          border: `1px solid rgba(0,240,255,0.15)`,
          display: 'flex', alignItems: 'flex-start', gap: 8,
        }}>
          <Icon name="lock" size={12} color={Z.cyan} />
          <div style={{ fontSize: 11, color: Z.muted, lineHeight: 1.5 }}>
            Pago seguro procesado por <span style={{ color: Z.cyan, fontWeight: 700 }}>PayPhone</span>.
            Cancela cuando quieras desde tu perfil.
          </div>
        </div>

        {/* Tarjetas aceptadas */}
        <div style={{ marginTop: 18, display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'center' }}>
          <span style={{ fontSize: 10, color: Z.dim, letterSpacing: 1, fontWeight: 600 }}>ACEPTAMOS</span>
          {[
            { l: 'VISA', c: '#1A1F71' },
            { l: 'MC',   c: '#EB001B' },
            { l: 'DINERS', c: '#0079BE' },
            { l: 'AMEX', c: '#2E77BC' },
          ].map(card => (
            <div key={card.l} style={{
              padding: '4px 8px', borderRadius: 5,
              background: Z.surface, border: `1px solid ${Z.border}`,
              fontSize: 9, fontWeight: 800, color: card.c, letterSpacing: 0.6,
              fontFamily: Z.font,
            }}>{card.l}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SummaryRow({ label, value, total }) {
  return (
    <div style={{
      padding: total ? '14px 14px' : '12px 14px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      borderTop: total ? `1px solid ${Z.border}` : 'none',
      background: total ? 'rgba(0,240,255,0.04)' : 'transparent',
    }}>
      <div style={{ fontSize: total ? 14 : 13, fontWeight: total ? 700 : 500, color: total ? Z.text : Z.muted }}>{label}</div>
      <div style={{
        fontSize: total ? 18 : 13, fontWeight: total ? 800 : 600,
        color: Z.text, letterSpacing: total ? -0.4 : 0,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {total ? <GradientText>{value}</GradientText> : value}
      </div>
    </div>
  );
}
window.CheckoutScreen = CheckoutScreen;

// 5b · Procesando pago
function PaymentProcessingScreen() {
  return (
    <div style={{
      height: '100%', position: 'relative', overflow: 'hidden',
      background: 'radial-gradient(circle at 50% 35%, rgba(0,240,255,0.10) 0%, transparent 60%), #0A0A0F',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: '0 28px',
    }}>
      {/* Spinner: gradient ring rotating */}
      <div style={{
        position: 'relative', width: 120, height: 120, marginBottom: 38,
      }}>
        {/* outer pulses */}
        <div style={{
          position: 'absolute', inset: -14, borderRadius: '50%',
          border: `1px solid rgba(0,240,255,0.18)`,
        }} />
        <div style={{
          position: 'absolute', inset: -28, borderRadius: '50%',
          border: `1px solid rgba(0,240,255,0.08)`,
        }} />

        {/* base track */}
        <div style={{
          position: 'absolute', inset: 0, borderRadius: '50%',
          border: `4px solid ${Z.border}`,
        }} />
        {/* spinning gradient arc — implemented as conic gradient */}
        <div style={{
          position: 'absolute', inset: 0, borderRadius: '50%',
          background: `conic-gradient(from 0deg, ${Z.cyan} 0deg, ${Z.purple} 240deg, transparent 250deg, transparent 360deg)`,
          WebkitMask: 'radial-gradient(circle, transparent 54px, black 56px)',
          mask: 'radial-gradient(circle, transparent 54px, black 56px)',
          filter: 'drop-shadow(0 0 12px rgba(0,240,255,0.6))',
          animation: 'zepoSpin 1.1s linear infinite',
        }} />

        {/* core */}
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 64, height: 64, borderRadius: 32,
          background: 'linear-gradient(135deg, rgba(0,240,255,0.18), rgba(112,0,255,0.18))',
          border: `1px solid rgba(0,240,255,0.35)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <ZepoLogo size={32} />
        </div>
      </div>

      <style>{`@keyframes zepoSpin { from { transform: rotate(0deg);} to { transform: rotate(360deg);} }`}</style>

      <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.6, marginBottom: 10, textAlign: 'center' }}>
        Procesando tu <GradientText>pago…</GradientText>
      </div>
      <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.5, textAlign: 'center', maxWidth: 280, marginBottom: 32 }}>
        Estamos confirmando con PayPhone. No cierres la app.
      </div>

      {/* Estado de pasos */}
      <div style={{
        width: '100%', maxWidth: 320,
        padding: 14, borderRadius: 14,
        background: Z.surface, border: `1px solid ${Z.border}`,
      }}>
        {[
          { l: 'Conectando con PayPhone', done: true },
          { l: 'Verificando datos',       done: true },
          { l: 'Confirmando transacción', loading: true },
          { l: 'Activando tu plan' },
        ].map((s, i, arr) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '8px 0',
            borderBottom: i < arr.length - 1 ? `1px solid ${Z.border}` : 'none',
          }}>
            <div style={{
              width: 20, height: 20, borderRadius: 10,
              background: s.done ? Z.success : s.loading ? 'rgba(0,240,255,0.15)' : Z.bg,
              border: `1px solid ${s.done ? Z.success : s.loading ? Z.cyan : Z.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              {s.done && <Icon name="check" size={11} color="#0A0A0F" strokeWidth={3.5} />}
              {s.loading && <div style={{ width: 6, height: 6, borderRadius: 3, background: Z.cyan, boxShadow: `0 0 8px ${Z.cyan}` }} />}
            </div>
            <div style={{
              fontSize: 13, fontWeight: s.loading ? 700 : 500,
              color: s.done ? Z.muted : s.loading ? Z.text : Z.dim,
            }}>{s.l}</div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 24, fontSize: 11, color: Z.dim, fontFamily: Z.mono, letterSpacing: 0.4 }}>
        TXN · ZP-{(Math.random() * 9e8 + 1e8).toFixed(0).slice(0, 8)}
      </div>
    </div>
  );
}
window.PaymentProcessingScreen = PaymentProcessingScreen;

// 5c · Pago exitoso
function PaymentSuccessScreen({ plan = 'pro' }) {
  const isElite = plan === 'elite';
  const price = isElite ? 10.00 : 5.00;
  const name = isElite ? 'Elite' : 'Pro';
  return (
    <div style={{
      height: '100%', position: 'relative', overflow: 'hidden',
      background: 'radial-gradient(circle at 50% 25%, rgba(0,229,160,0.18) 0%, transparent 55%), #0A0A0F',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '60px 28px 32px', textAlign: 'center',
    }}>
      {/* Check grande */}
      <div style={{
        width: 108, height: 108, borderRadius: 28,
        background: 'linear-gradient(135deg, rgba(0,229,160,0.22), rgba(0,240,255,0.12))',
        border: `1px solid ${Z.success}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 28, position: 'relative',
        boxShadow: '0 0 64px rgba(0,229,160,0.35)',
      }}>
        <Icon name="check" size={52} color={Z.success} strokeWidth={2.6} />
        {/* anillos sutiles */}
        <div style={{
          position: 'absolute', inset: -10, borderRadius: 38,
          border: `1px solid rgba(0,229,160,0.3)`,
        }} />
        <div style={{
          position: 'absolute', inset: -22, borderRadius: 50,
          border: `1px solid rgba(0,229,160,0.12)`,
        }} />
      </div>

      <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.9, lineHeight: 1.1, marginBottom: 10 }}>
        ¡Bienvenido a <GradientText>{name}!</GradientText>
      </div>
      <div style={{ fontSize: 15, color: Z.muted, lineHeight: 1.5, marginBottom: 28, maxWidth: 320 }}>
        Tu plan está activo. Disfruta todas las funciones desde ya mismo.
      </div>

      {/* Card resumen */}
      <div style={{
        width: '100%', padding: 18, borderRadius: 16,
        background: Z.surface, border: `1px solid ${Z.border}`,
        textAlign: 'left',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <PlanBadge plan={plan} />
          <span style={{ fontSize: 12, color: Z.muted, fontWeight: 600 }}>Activado</span>
          <div style={{ flex: 1 }} />
          <div style={{
            fontSize: 10, fontWeight: 700, padding: '3px 7px', borderRadius: 5, letterSpacing: 0.5,
            background: 'rgba(0,229,160,0.18)', color: Z.success,
          }}>PAGADO</div>
        </div>

        <SummaryRow label="Plan" value={name} />
        <div style={{ height: 1, background: Z.border }} />
        <SummaryRow label="Monto cobrado" value={`$${price.toFixed(2)}`} />
        <div style={{ height: 1, background: Z.border }} />
        <SummaryRow label="Próximo cobro" value="8 jun 2026" />
        <div style={{ height: 1, background: Z.border }} />
        <div style={{ padding: '12px 0 2px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 12, color: Z.muted }}>Recibo enviado a</div>
          <div style={{ fontSize: 12, color: Z.cyan, fontWeight: 600, fontFamily: Z.mono }}>andrea@…com</div>
        </div>
      </div>

      <div style={{ flex: 1 }} />
      <div style={{ width: '100%' }}>
        <GradientButton>Empezar a usar</GradientButton>
        <button style={{
          marginTop: 10, width: '100%', height: 46, borderRadius: 23,
          background: 'transparent', border: 'none',
          color: Z.muted, fontWeight: 600, fontSize: 13, fontFamily: Z.font,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
        }}>
          <Icon name="download" size={13} color={Z.muted} /> Descargar recibo
        </button>
      </div>
    </div>
  );
}
window.PaymentSuccessScreen = PaymentSuccessScreen;

// 5d · Pago fallido
function PaymentFailedScreen() {
  return (
    <div style={{
      height: '100%', position: 'relative', overflow: 'hidden',
      background: 'radial-gradient(circle at 50% 25%, rgba(255,107,107,0.18) 0%, transparent 55%), #0A0A0F',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '60px 28px 32px', textAlign: 'center',
    }}>
      {/* Alert */}
      <div style={{
        width: 108, height: 108, borderRadius: 28,
        background: 'linear-gradient(135deg, rgba(255,107,107,0.22), rgba(255,184,0,0.10))',
        border: `1px solid ${Z.danger}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 28, position: 'relative',
        boxShadow: '0 0 64px rgba(255,107,107,0.3)',
      }}>
        <Icon name="alert-triangle" size={48} color={Z.danger} strokeWidth={1.9} />
        <div style={{
          position: 'absolute', inset: -10, borderRadius: 38,
          border: `1px solid rgba(255,107,107,0.25)`,
        }} />
      </div>

      <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.7, lineHeight: 1.15, marginBottom: 10 }}>
        No se pudo procesar el pago
      </div>
      <div style={{ fontSize: 14, color: Z.muted, lineHeight: 1.55, marginBottom: 22, maxWidth: 320 }}>
        Revisa los datos de tu tarjeta o intenta con otro método de pago.
      </div>

      {/* Error code card */}
      <div style={{
        width: '100%', padding: '14px 16px', borderRadius: 14,
        background: 'rgba(255,107,107,0.05)',
        border: `1px solid rgba(255,107,107,0.25)`,
        textAlign: 'left',
        display: 'flex', gap: 12, alignItems: 'flex-start',
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 9, flexShrink: 0,
          background: 'rgba(255,107,107,0.15)', border: `1px solid rgba(255,107,107,0.3)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name="x" size={16} color={Z.danger} strokeWidth={2.6} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: Z.text, marginBottom: 4 }}>
            Tarjeta rechazada
          </div>
          <div style={{ fontSize: 12, color: Z.muted, lineHeight: 1.5 }}>
            Tu banco rechazó el cargo. No se realizó ningún cobro.
          </div>
          <div style={{
            marginTop: 8, padding: '4px 8px', borderRadius: 5,
            background: Z.bg, border: `1px solid ${Z.border}`,
            display: 'inline-block',
            fontSize: 10, fontFamily: Z.mono, color: Z.muted, letterSpacing: 0.6,
          }}>CÓDIGO · PP_DECLINED_05</div>
        </div>
      </div>

      {/* Alternativas */}
      <div style={{
        width: '100%', marginTop: 18,
        display: 'flex', flexDirection: 'column', gap: 6,
        textAlign: 'left',
      }}>
        {[
          'Verifica que tu tarjeta tenga fondos',
          'Confirma con tu banco que aceptan cargos online',
          'Prueba con otra tarjeta',
        ].map((t, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: Z.muted }}>
            <div style={{ width: 4, height: 4, borderRadius: 2, background: Z.dim }} />
            {t}
          </div>
        ))}
      </div>

      <div style={{ flex: 1 }} />
      <div style={{ width: '100%' }}>
        <GradientButton>Reintentar pago</GradientButton>
        <button style={{
          marginTop: 10, width: '100%', height: 46, borderRadius: 23,
          background: 'transparent', border: 'none',
          color: Z.muted, fontWeight: 600, fontSize: 14, fontFamily: Z.font,
        }}>Volver a planes</button>
      </div>
    </div>
  );
}
window.PaymentFailedScreen = PaymentFailedScreen;