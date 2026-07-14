// Plantillas de correo de marca — Zepo y Elé (Supabase Send Email Hook → Resend)
// Diseño aprobado por Alvaro 2026-07-14 (base: recovery Zepo crema/sage).

type Theme = {
  name: string;
  from: string;
  bg: string;
  card: string;
  ink: string;
  muted: string;
  faint: string;
  border: string;
  accent: string;
  ctaText: string;
  display: string; // font stack para wordmark/h1
  body: string;    // font stack para texto
  tagline: string;
  appUrl: string;
};

const ZEPO: Theme = {
  name: "Zepo",
  from: "Zepo <zepo@lynoia.com>",
  bg: "#EFEADB",
  card: "#FFFFFF",
  ink: "#1A2418",
  muted: "rgba(26,36,24,0.72)",
  faint: "rgba(26,36,24,0.48)",
  border: "rgba(26,36,24,0.10)",
  accent: "#507D5A",
  ctaText: "#FFFFFF",
  display: "'Bricolage Grotesque',Georgia,'Times New Roman',serif",
  body: "-apple-system,'Segoe UI',Arial,sans-serif",
  tagline: "Tus finanzas, claras.",
  appUrl: "https://app.zepo.lynoia.com/pwa/",
};

const ELE: Theme = {
  name: "Elé",
  from: "Elé <ele@lynoia.com>",
  bg: "#F7F2E9",
  card: "#FFFFFF",
  ink: "#2A2520",
  muted: "rgba(42,37,32,0.72)",
  faint: "rgba(42,37,32,0.48)",
  border: "rgba(42,37,32,0.10)",
  accent: "#C06530",
  ctaText: "#FFFFFF",
  display: "'Inter',-apple-system,'Segoe UI',Arial,sans-serif",
  body: "'Inter',-apple-system,'Segoe UI',Arial,sans-serif",
  tagline: "Tu contenido, en automático.",
  appUrl: "https://app.ele.lynoia.com/",
};

type Copy = {
  subject: string;
  preheader: string;
  label: string;
  title: string;
  bodyHtml: string;
  cta: string | null;
  note: string;
};

function copyFor(t: Theme, action: string, token?: string): Copy {
  switch (action) {
    case "recovery":
      return {
        subject: `Crea una nueva contraseña para tu cuenta ${t.name}`,
        preheader: `Crea una nueva contraseña para tu cuenta ${t.name}. El enlace caduca en 1 hora.`,
        label: "Seguridad de tu cuenta",
        title: "¿Olvidaste tu contraseña?",
        bodyHtml: `Pasa, le sucede a todos. Toca el botón y crea una nueva en segundos. Por tu seguridad, este enlace caduca en <strong style="color:${t.ink};">1 hora</strong>.`,
        cta: "Crear nueva contraseña",
        note: "¿No fuiste tú? Ignora este correo con tranquilidad — tu cuenta sigue protegida y nada cambia.",
      };
    case "signup":
    case "invite":
      return {
        subject: `Te damos la bienvenida a ${t.name} — confirma tu correo`,
        preheader: `Solo falta un paso: confirma tu correo para activar tu cuenta.`,
        label: "Tu cuenta nueva",
        title: `¡Qué gusto tenerte en ${t.name}!`,
        bodyHtml: t.name === "Zepo"
          ? `Solo falta un paso: confirma tu correo para activar tu cuenta y empezar a registrar tus gastos en segundos.`
          : `Solo falta un paso: confirma tu correo para activar tu cuenta y empezar a crear contenido para tu negocio en automático.`,
        cta: "Confirmar mi correo",
        note: "Si no creaste esta cuenta, puedes ignorar este correo.",
      };
    case "magiclink":
      return {
        subject: `Tu enlace para entrar a ${t.name}`,
        preheader: `Entra a ${t.name} con un toque. El enlace caduca en 1 hora.`,
        label: "Acceso rápido",
        title: "Entra con un toque",
        bodyHtml: `Toca el botón para entrar a tu cuenta. El enlace caduca en <strong style="color:${t.ink};">1 hora</strong> y solo funciona una vez.`,
        cta: `Entrar a ${t.name}`,
        note: "¿No pediste este enlace? Ignóralo — nadie puede entrar a tu cuenta sin él.",
      };
    case "email_change":
      return {
        subject: `Confirma tu nuevo correo en ${t.name}`,
        preheader: `Confirma el cambio de correo de tu cuenta ${t.name}.`,
        label: "Seguridad de tu cuenta",
        title: "Confirma tu nuevo correo",
        bodyHtml: `Pediste cambiar el correo de tu cuenta. Toca el botón para confirmar esta nueva dirección.`,
        cta: "Confirmar cambio",
        note: "¿No fuiste tú? Ignora este correo y tu dirección actual seguirá activa.",
      };
    case "reauthentication":
      return {
        subject: `Tu código de verificación de ${t.name}`,
        preheader: `Tu código de verificación de ${t.name}.`,
        label: "Verificación",
        title: "Tu código de verificación",
        bodyHtml: `Escribe este código en la app para continuar:<br><br><span style="font-family:'SFMono-Regular',Consolas,monospace;font-size:28px;letter-spacing:6px;font-weight:700;color:${t.ink};">${token ?? ""}</span>`,
        cta: null,
        note: "¿No pediste este código? Ignora este correo.",
      };
    default:
      return {
        subject: `Aviso de tu cuenta ${t.name}`,
        preheader: `Aviso de tu cuenta ${t.name}.`,
        label: "Tu cuenta",
        title: "Confirma esta acción",
        bodyHtml: `Toca el botón para continuar. Si no pediste esto, ignora este correo.`,
        cta: "Continuar",
        note: "¿No fuiste tú? Ignora este correo con tranquilidad.",
      };
  }
}

function render(t: Theme, c: Copy, url: string): string {
  const cta = c.cta
    ? `<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 26px;">
        <tr><td align="center" style="background:${t.accent};border-radius:30px;">
          <a href="${url}" style="display:inline-block;padding:15px 36px;font-family:${t.body};font-size:16px;font-weight:700;color:${t.ctaText};text-decoration:none;border-radius:30px;">${c.cta}</a>
        </td></tr></table>
      <p style="margin:0 0 6px;font-family:${t.body};font-size:13px;line-height:1.5;color:${t.faint};">¿No funciona el botón? Copia y pega este enlace en tu navegador:</p>
      <p style="margin:0 0 28px;font-family:'SFMono-Regular',Consolas,monospace;font-size:12px;line-height:1.5;color:${t.accent};word-break:break-all;">${url}</p>`
    : "";
  return `<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${c.subject}</title></head>
<body style="margin:0;padding:0;background:${t.bg};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">${c.preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${t.bg};padding:32px 16px;">
  <tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;">
      <tr><td style="padding:8px 4px 22px;">
        <span style="font-family:${t.display};font-size:24px;font-weight:700;letter-spacing:-0.5px;color:${t.ink};">${t.name}</span>
        <span style="float:right;font-family:${t.body};font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:${t.accent};padding-top:9px;">Tu cuenta</span>
      </td></tr>
      <tr><td style="background:${t.card};border:1px solid ${t.border};border-radius:18px;padding:38px 34px;">
        <div style="font-family:${t.body};font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:${t.accent};margin-bottom:14px;">${c.label}</div>
        <h1 style="margin:0 0 14px;font-family:${t.display};font-size:27px;line-height:1.2;font-weight:700;color:${t.ink};">${c.title}</h1>
        <p style="margin:0 0 26px;font-family:${t.body};font-size:16px;line-height:1.62;color:${t.muted};">${c.bodyHtml}</p>
        ${cta}
        <div style="border-top:1px solid ${t.border};padding-top:20px;">
          <p style="margin:0;font-family:${t.body};font-size:14px;line-height:1.6;color:${t.muted};">${c.note}</p>
        </div>
      </td></tr>
      <tr><td style="padding:24px 6px 4px;text-align:center;">
        <p style="margin:0 0 4px;font-family:${t.display};font-size:14px;font-weight:700;color:${t.ink};">${t.name}</p>
        <p style="margin:0;font-family:${t.body};font-size:12px;line-height:1.6;color:${t.faint};">${t.tagline} · Un producto de Lynoia<br>Quito, Ecuador</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>`;
}

export function buildEmail(app: "zepo" | "ele", action: string, url: string, token?: string) {
  const t = app === "ele" ? ELE : ZEPO;
  const c = copyFor(t, action, token);
  return { from: t.from, subject: c.subject, html: render(t, c, url) };
}
