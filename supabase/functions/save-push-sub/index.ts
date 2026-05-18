// save-push-sub · Guarda o actualiza la suscripción Web Push del usuario
// POST { endpoint, p256dh, auth } — requiere Authorization: Bearer <jwt>
import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL     = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info",
  "Access-Control-Allow-Methods": "POST, DELETE, OPTIONS",
};

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });

  const jwt = req.headers.get("Authorization")?.replace("Bearer ", "");
  if (!jwt) return new Response("Unauthorized", { status: 401, headers: cors });

  const sb = createClient(SUPABASE_URL, SUPABASE_SERVICE, {
    auth: { persistSession: false },
  });

  // Verificar usuario desde JWT
  const { data: { user }, error: authErr } = await sb.auth.getUser(jwt);
  if (authErr || !user) return new Response("Unauthorized", { status: 401, headers: cors });

  // DELETE: eliminar suscripción al desactivar notificaciones
  if (req.method === "DELETE") {
    await sb.from("push_subscriptions").delete().eq("user_id", user.id);
    return new Response(JSON.stringify({ ok: true }), { headers: { ...cors, "Content-Type": "application/json" } });
  }

  const body = await req.json().catch(() => ({}));
  const { endpoint, p256dh, auth: authKey, settings } = body;

  if (!endpoint || !p256dh || !authKey) {
    return new Response("Missing fields", { status: 400, headers: cors });
  }

  // Upsert suscripción
  const { error } = await sb.from("push_subscriptions").upsert(
    { user_id: user.id, endpoint, p256dh, auth_key: authKey },
    { onConflict: "user_id,endpoint" }
  );
  if (error) return new Response(JSON.stringify({ error: error.message }), { status: 500, headers: cors });

  // Guardar preferencias si vienen en el mismo request
  if (settings) {
    await sb.from("user_settings").upsert(
      { user_id: user.id, ...settings },
      { onConflict: "user_id" }
    );
  }

  return new Response(JSON.stringify({ ok: true }), {
    headers: { ...cors, "Content-Type": "application/json" },
  });
});
