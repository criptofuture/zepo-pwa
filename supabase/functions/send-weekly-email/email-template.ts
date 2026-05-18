// Template de email semanal — estilo Zepo (dark, cyan/purple gradient)
// Usa tablas HTML para máxima compatibilidad con clientes de email

export interface WeeklySummary {
  userName: string;
  weekLabel: string;          // "12 – 18 mayo 2026"
  totalGastos: number;
  totalIngresos: number;
  balance: number;
  numTransacciones: number;
  topCategories: Array<{ label: string; emoji: string; amount: number; pct: number }>;
  pendingCobros: number;      // monto total de cobros pendientes
  appUrl: string;
}

const CAT_LABELS: Record<string, { label: string; emoji: string }> = {
  food:       { label: "Comida",        emoji: "🍽️" },
  transport:  { label: "Transporte",    emoji: "🚕" },
  market:     { label: "Mercado",       emoji: "🛒" },
  health:     { label: "Salud",         emoji: "💊" },
  rent:       { label: "Hogar",         emoji: "🏠" },
  fun:        { label: "Ocio",          emoji: "🎮" },
  shop:       { label: "Compras",       emoji: "🛍️" },
  coffee:     { label: "Café",          emoji: "☕" },
  pets:       { label: "Mascotas",      emoji: "🐾" },
  savings:    { label: "Ahorro",        emoji: "🏦" },
  invest_out: { label: "Inversión",     emoji: "📈" },
  other:      { label: "Otros",         emoji: "📦" },
  salary:     { label: "Sueldo",        emoji: "💰" },
  freelance:  { label: "Freelance",     emoji: "💻" },
  business:   { label: "Negocio",       emoji: "🏢" },
};

export function getCatMeta(key: string) {
  return CAT_LABELS[key] ?? { label: key, emoji: "📦" };
}

export function buildWeeklyEmail(s: WeeklySummary): string {
  const fmt = (n: number) => n.toFixed(2);
  const balanceColor = s.balance >= 0 ? "#00E5A0" : "#FF6B6B";
  const balanceSign  = s.balance >= 0 ? "+" : "";

  const categoryRows = s.topCategories.slice(0, 5).map(c => `
    <tr>
      <td style="padding:10px 0;border-bottom:1px solid #1E1E2E;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="width:32px;font-size:18px;">${c.emoji}</td>
            <td style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:14px;color:#C8C8E0;">${c.label}</td>
            <td align="right" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:14px;font-weight:700;color:#FFFFFF;">$${fmt(c.amount)}</td>
            <td align="right" style="width:40px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:11px;color:#6B6B8A;padding-left:8px;">${c.pct}%</td>
          </tr>
          <tr>
            <td colspan="4" style="padding-top:6px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="background:#1E1E2E;border-radius:3px;height:4px;">
                    <table width="${Math.min(c.pct, 100)}%" cellpadding="0" cellspacing="0" border="0">
                      <tr><td style="background:linear-gradient(90deg,#00F0FF,#7000FF);border-radius:3px;height:4px;font-size:0;">&nbsp;</td></tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>`).join("");

  const cobrosSection = s.pendingCobros > 0 ? `
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:24px;">
      <tr>
        <td style="background:linear-gradient(135deg,rgba(0,240,255,0.08),rgba(112,0,255,0.08));border:1px solid rgba(0,240,255,0.25);border-radius:12px;padding:16px 20px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:12px;color:#00F0FF;letter-spacing:1px;font-weight:700;">COBROS PENDIENTES</td>
              <td align="right" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:18px;font-weight:800;color:#FFFFFF;">$${fmt(s.pendingCobros)}</td>
            </tr>
            <tr>
              <td colspan="2" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:12px;color:#6B6B8A;padding-top:4px;">Te deben este dinero. Recuérdales.</td>
            </tr>
          </table>
        </td>
      </tr>
    </table>` : "";

  return `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>Zepo — Tu resumen semanal</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background:#0A0A0F;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0A0A0F;min-height:100vh;">
  <tr>
    <td align="center" style="padding:40px 16px;">

      <!-- Container -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:540px;">

        <!-- ── Logo ── -->
        <tr>
          <td align="center" style="padding-bottom:32px;">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:linear-gradient(135deg,#00F0FF,#7000FF);border-radius:18px;padding:1px;">
                  <table cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td style="background:#0A0A0F;border-radius:17px;padding:10px 18px;">
                        <span style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:22px;font-weight:900;background:linear-gradient(135deg,#00F0FF,#7000FF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;color:#00F0FF;letter-spacing:-0.5px;">Zepo</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── Header ── -->
        <tr>
          <td style="padding-bottom:8px;">
            <p style="margin:0;font-size:13px;color:#6B6B8A;letter-spacing:1px;font-weight:600;text-align:center;">RESUMEN SEMANAL</p>
            <h1 style="margin:8px 0 0;font-size:28px;font-weight:800;color:#FFFFFF;text-align:center;letter-spacing:-0.5px;">
              Hola, ${s.userName} 👋
            </h1>
            <p style="margin:8px 0 0;font-size:14px;color:#6B6B8A;text-align:center;">${s.weekLabel}</p>
          </td>
        </tr>

        <!-- ── Balance hero ── -->
        <tr>
          <td style="padding:24px 0 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:linear-gradient(135deg,#00F0FF,#7000FF);border-radius:17px;padding:1px;">
                  <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                      <td style="background:#0D0D18;border-radius:16px;padding:24px;">
                        <p style="margin:0;font-size:11px;color:#6B6B8A;letter-spacing:1.2px;font-weight:700;">BALANCE DE LA SEMANA</p>
                        <p style="margin:8px 0 0;font-size:42px;font-weight:800;color:${balanceColor};letter-spacing:-1.5px;line-height:1;">${balanceSign}$${fmt(Math.abs(s.balance))}</p>
                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;">
                          <tr>
                            <td>
                              <p style="margin:0;font-size:11px;color:#6B6B8A;">GASTÉ</p>
                              <p style="margin:4px 0 0;font-size:18px;font-weight:700;color:#FF6B6B;">-$${fmt(s.totalGastos)}</p>
                            </td>
                            <td align="center">
                              <p style="margin:0;font-size:11px;color:#6B6B8A;">TRANSACCIONES</p>
                              <p style="margin:4px 0 0;font-size:18px;font-weight:700;color:#FFFFFF;">${s.numTransacciones}</p>
                            </td>
                            <td align="right">
                              <p style="margin:0;font-size:11px;color:#6B6B8A;">INGRESÉ</p>
                              <p style="margin:4px 0 0;font-size:18px;font-weight:700;color:#00E5A0;">+$${fmt(s.totalIngresos)}</p>
                            </td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── Categorías ── -->
        ${s.topCategories.length > 0 ? `
        <tr>
          <td style="padding-top:28px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0D0D18;border:1px solid #1E1E2E;border-radius:16px;padding:0 20px;">
              <tr>
                <td style="padding:20px 0 8px;">
                  <p style="margin:0;font-size:11px;color:#6B6B8A;letter-spacing:1.2px;font-weight:700;">TOP CATEGORÍAS</p>
                </td>
              </tr>
              ${categoryRows}
            </table>
          </td>
        </tr>` : ""}

        <!-- ── Cobros pendientes ── -->
        ${cobrosSection ? `<tr><td>${cobrosSection}</td></tr>` : ""}

        <!-- ── CTA ── -->
        <tr>
          <td style="padding-top:28px;" align="center">
            <table cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:linear-gradient(135deg,#00F0FF,#7000FF);border-radius:26px;padding:1px;">
                  <a href="${s.appUrl}" style="display:block;padding:14px 36px;background:linear-gradient(135deg,#00F0FF,#7000FF);border-radius:25px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:15px;font-weight:700;color:#0A0A0F;text-decoration:none;letter-spacing:0.2px;">
                    Ver mis gastos →
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── Footer ── -->
        <tr>
          <td style="padding-top:40px;text-align:center;">
            <p style="margin:0;font-size:12px;color:#3A3A5C;line-height:1.6;">
              Recibiste este correo porque activaste el resumen semanal en Zepo.<br>
              <a href="${s.appUrl}?tab=settings" style="color:#6B6B8A;text-decoration:underline;">Desactivar notificaciones</a>
            </p>
            <p style="margin:16px 0 0;font-size:11px;color:#2A2A3C;">
              © ${new Date().getFullYear()} Zepo · Quito, Ecuador
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>

</body>
</html>`;
}
