// Alicia · webhook de Telegram para responder campañas Snov desde el chat.
//
// Flujo: respondes (con "Responder" de Telegram) al mensaje de un prospecto con
// el texto a enviar → Alicia muestra el borrador y pregunta el OBJETIVO BREVE DE
// LA REUNIÓN → escribes el objetivo (o "aprobar") → "aprobar" envía el correo en
// el mismo hilo y desde la misma casilla, crea/actualiza el contacto en GHL y
// guarda el objetivo. "no responder" descarta; "cancelar" borra el borrador.
// "mover a <etapa>" mueve la oportunidad en GHL (a pedido, no automático).
//
// Sin IA: el texto dictado se envía tal cual. Modo prueba: si ALICIA_DRY_RUN !=
// 'false', al "aprobar" se muestra el correo/acciones SIN ejecutarlos de verdad.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const SB_URL = Deno.env.get("SUPABASE_URL")!;
const SB_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SB = (p: string) => `${SB_URL}/rest/v1/${p}`;
const H = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json" };
const GHL = "https://services.leadconnectorhq.com";

async function sbGet(p: string): Promise<any[]> {
  const r = await fetch(SB(p), { headers: H });
  return r.ok ? await r.json() : [];
}
async function sbPatch(p: string, body: unknown) {
  await fetch(SB(p), { method: "PATCH", headers: { ...H, Prefer: "return=minimal" }, body: JSON.stringify(body) });
}
async function sbInsert(table: string, body: unknown) {
  await fetch(SB(table), { method: "POST", headers: { ...H, Prefer: "return=minimal" }, body: JSON.stringify(body) });
}
async function loadSecrets(): Promise<Record<string, string>> {
  const rows = await sbGet("alicia_secrets?select=name,value");
  const m: Record<string, string> = {};
  for (const r of rows) m[r.name] = r.value;
  return m;
}
async function tgSend(token: string, chatId: number | string, text: string): Promise<any> {
  const r = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
  });
  return await r.json().catch(() => ({}));
}

// ---- Gmail ----
async function gmailToken(clientId: string, clientSecret: string, refresh: string): Promise<string> {
  const body = new URLSearchParams({
    client_id: clientId, client_secret: clientSecret,
    refresh_token: refresh, grant_type: "refresh_token",
  });
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body,
  });
  const j = await r.json();
  if (!j.access_token) throw new Error("no gmail access_token");
  return j.access_token;
}
async function gmailOrig(access: string, msgId: string) {
  const url = `${"https://gmail.googleapis.com/gmail/v1"}/users/me/messages/${msgId}?format=metadata&metadataHeaders=Message-ID&metadataHeaders=References&metadataHeaders=Subject`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${access}` } });
  const j = await r.json();
  const hs = j.payload?.headers ?? [];
  const get = (n: string) => (hs.find((h: any) => h.name.toLowerCase() === n.toLowerCase())?.value ?? "");
  return { messageId: get("Message-ID"), references: get("References"), subject: get("Subject") };
}
function b64url(x: string): string {
  return btoa(unescape(encodeURIComponent(x))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function encHeader(x: string): string {
  // deno-lint-ignore no-control-regex
  return /[^\x00-\x7F]/.test(x) ? `=?UTF-8?B?${btoa(unescape(encodeURIComponent(x)))}?=` : x;
}
function buildRaw(o: any): string {
  const subj = (o.subject || "").toLowerCase().startsWith("re:") ? o.subject : `Re: ${o.subject}`;
  const lines = [`From: ${o.from}`, `To: ${o.to}`, `Subject: ${encHeader(subj)}`, "MIME-Version: 1.0", 'Content-Type: text/plain; charset="UTF-8"'];
  if (o.inReplyTo) { lines.push(`In-Reply-To: ${o.inReplyTo}`); lines.push(`References: ${o.references ? o.references + " " + o.inReplyTo : o.inReplyTo}`); }
  lines.push(""); lines.push(o.body);
  return b64url(lines.join("\r\n"));
}

// ---- GoHighLevel ----
function ghlH(token: string) { return { Authorization: `Bearer ${token}`, Version: "2021-07-28", "Content-Type": "application/json", Accept: "application/json" }; }
async function ghlFindContact(token: string, loc: string, email: string): Promise<any | null> {
  const r = await fetch(`${GHL}/contacts/?locationId=${loc}&query=${encodeURIComponent(email)}&limit=5`, { headers: ghlH(token) });
  const d = await r.json().catch(() => ({}));
  const cs = d.contacts ?? [];
  return cs.find((c: any) => (c.email ?? "").toLowerCase() === email.toLowerCase()) ?? cs[0] ?? null;
}
async function ghlUpsertContact(token: string, loc: string, thread: any, objetivo: string, fieldId: string): Promise<{ id: string; created: boolean } | null> {
  const cf = objetivo ? [{ id: fieldId, value: objetivo }] : [];
  const existing = await ghlFindContact(token, loc, thread.prospect_email);
  if (existing) {
    if (cf.length) {
      await fetch(`${GHL}/contacts/${existing.id}`, { method: "PUT", headers: ghlH(token), body: JSON.stringify({ customFields: cf }) });
    }
    return { id: existing.id, created: false };
  }
  const parts = (thread.prospect_name ?? "").trim().split(/\s+/);
  const body: any = {
    locationId: loc, email: thread.prospect_email,
    firstName: parts[0] || thread.prospect_email, lastName: parts.slice(1).join(" "),
    name: thread.prospect_name || thread.prospect_email, companyName: thread.empresa ?? "",
    customFields: cf,
  };
  const r = await fetch(`${GHL}/contacts/`, { method: "POST", headers: ghlH(token), body: JSON.stringify(body) });
  const d = await r.json().catch(() => ({}));
  const id = d.contact?.id ?? d.id;
  return id ? { id, created: true } : null;
}
async function ghlMoveStage(token: string, loc: string, pipelineId: string, contactId: string, stageId: string, name: string): Promise<boolean> {
  const r = await fetch(`${GHL}/opportunities/search?location_id=${loc}&contact_id=${contactId}`, { headers: ghlH(token) });
  const d = await r.json().catch(() => ({}));
  const opp = (d.opportunities ?? []).find((o: any) => o.pipelineId === pipelineId) ?? (d.opportunities ?? [])[0];
  if (opp) {
    const rr = await fetch(`${GHL}/opportunities/${opp.id}`, { method: "PUT", headers: ghlH(token), body: JSON.stringify({ pipelineStageId: stageId }) });
    return rr.ok;
  }
  const rr = await fetch(`${GHL}/opportunities/`, { method: "POST", headers: ghlH(token), body: JSON.stringify({ locationId: loc, pipelineId, pipelineStageId: stageId, contactId, name: name || "Oportunidad", status: "open" }) });
  return rr.ok;
}

// Etapas del pipeline Sales de GBS (nombre → id).
const STAGES: Record<string, string> = {
  "RESPONDE WHATSAPP / CORREO": "deb37e6a-d9e0-4aa4-b014-6710508f26bb",
  "NO CONTESTA": "799c2bb1-409e-43b2-871a-137be2ee3021",
  "INFORMACION ADICIONAL": "5570d595-054a-41cf-ba72-2c7a6d7e8de0",
  "COORDINANDO REUNION": "ccdcba13-b840-4055-ba31-bd54c2c547c5",
  "REUNION AGENDADA": "5ae6c741-27bc-4195-8847-2718fe350cb6",
  "COTIZACION": "5ac23ab7-4377-44d6-91b7-f6dcae9b35c3",
  "REAGENDAR REUNION": "3ed4a01b-071c-41ac-8d2c-36afee4c8304",
  "ESPERA VALIDACION REUNION": "3f26afaa-68e6-4adb-aba2-31f7a812240b",
  "REUNION VALIDA": "6c7491de-e217-44d9-9832-acfeb1d08fe9",
  "REUNION NO VALIDA": "2db03faa-c9e0-484b-b697-eb0223c0caee",
  "DERIVA REFIERE SEGUIMIENTO": "105ddcd5-7093-4678-867b-4331837c8a8c",
  "DERIVA REFIERE DIRECTO": "e11dec87-655f-4430-a3af-c066411fd2f2",
  "TELEFONO WHATSAPP NO EXISTEN": "b46b64c0-3dd9-4c90-8d9e-0ef0e1535ae3",
  "NO INTERESADO": "878ac8ab-6eb9-42cf-8a8d-77f490122d09",
  "NO CALIFICA": "7dcec797-750c-4575-9a6b-f18fbc581329",
  "TRABAJAR MAS ADELANTE": "9b95cc98-5bd7-444f-8368-a826cb13ccbf",
};
function norm(x: string): string { return x.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().trim(); }
function matchStage(query: string): { name: string; id: string } | null {
  const q = norm(query);
  if (!q) return null;
  for (const [name, id] of Object.entries(STAGES)) {
    const n = norm(name);
    if (n === q || n.includes(q) || q.includes(n)) return { name, id };
  }
  return null;
}

const NOREPLY = ["no responder", "no contestar", "no responderle", "ignorar", "descartar"];
const APPROVE = ["aprobar", "aprobado", "aprueba", "enviar", "envialo", "envíalo", "ok enviar"];
const CANCEL = ["cancelar", "cancela", "borrar", "descartar borrador"];
function clean(s: string): string { return s.toLowerCase().replace(/[.!¡¿?]/g, "").trim(); }

serve(async (req) => {
  if (req.method !== "POST") return new Response(JSON.stringify({ ok: true }), { status: 200 });
  const s = await loadSecrets();
  const expected = s.TELEGRAM_WEBHOOK_SECRET ?? "";
  if (expected && req.headers.get("x-telegram-bot-api-secret-token") !== expected) return new Response("forbidden", { status: 401 });
  const clientRows = await sbGet("alicia_clients?select=cliente_slug,telegram_token,telegram_chat_id,gmail_client_id,gmail_client_secret");
  const clients: Record<string, any> = {}; for (const c of clientRows) clients[c.cliente_slug] = c;
  const defaultCliente = new URL(req.url).searchParams.get("cliente") ?? "gbs";
  let token = clients[defaultCliente]?.telegram_token ?? s.TELEGRAM_TOKEN;
  if (!token) return new Response("no token", { status: 200 });

  let update: any;
  try { update = await req.json(); } catch { return new Response("ok", { status: 200 }); }
  const msg = update.message ?? update.edited_message;
  if (!msg || !msg.text) return new Response(JSON.stringify({ ok: true }), { status: 200 });
  const chatId = msg.chat.id;
  const text = String(msg.text).trim();

  // Resolver hilo (por "Responder" a un mensaje o por código AL-XXXX).
  let thread: any = null;
  if (msg.reply_to_message) {
    const links = await sbGet(`alicia_telegram_links?select=thread_id&telegram_message_id=eq.${msg.reply_to_message.message_id}&limit=1`);
    if (links[0]) thread = (await sbGet(`alicia_email_threads?select=*&thread_id=eq.${encodeURIComponent(links[0].thread_id)}&limit=1`))[0];
  }
  if (!thread) {
    const m = text.match(/AL-[A-Z0-9]{8}/i);
    if (m) thread = (await sbGet(`alicia_email_threads?select=*&internal_ref=eq.${m[0].toUpperCase()}&limit=1`))[0];
  }
  if (!thread) {
    await tgSend(token, chatId, "No supe a qué respuesta te refieres. Usa Responder de Telegram sobre el mensaje del prospecto, o incluye su código AL-XXXX.");
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }

  const cmd = text.replace(/AL-[A-Z0-9]{8}/i, "").trim();
  const low = clean(cmd);
  const who = thread.prospect_name || thread.prospect_email;
  const sel = `alicia_email_threads?thread_id=eq.${encodeURIComponent(thread.thread_id)}`;

  // Bot y credenciales del cliente de este hilo (aislamiento multi-cliente).
  const cc = clients[thread.cliente_slug] ?? {};
  if (cc.telegram_token) token = cc.telegram_token;
  const tieneGhl = thread.cliente_slug === "gbs";

  // --- Comando: mover a <etapa> (a pedido; solo clientes con GoHighLevel) ---
  if (low.startsWith("mover a ") || low.startsWith("mueve a ") || low.startsWith("mover ") || low.startsWith("etapa ")) {
    if (!tieneGhl) { await tgSend(token, chatId, "Esta cuenta no tiene GoHighLevel conectado, así que no hay etapas que mover."); return new Response("ok"); }
    const query = cmd.replace(/^(mover a|mueve a|mover|etapa)/i, "").trim();
    const stage = matchStage(query);
    if (!stage) { await tgSend(token, chatId, `No reconocí la etapa "${query}". Ejemplos: información adicional, coordinando reunión, cotización…`); return new Response("ok"); }
    const ghlToken = s.GHL_TOKEN_GBS, loc = s.GHL_LOCATION_GBS, pipe = s.GHL_PIPELINE_GBS;
    const dryRun = (s.ALICIA_DRY_RUN ?? "true").toLowerCase() !== "false";
    if (dryRun) { await tgSend(token, chatId, `🧪 [PRUEBA] Movería a ${who} a la etapa «${stage.name}» (no se aplicó).`); return new Response("ok"); }
    let contactId = thread.ghl_contact_id;
    if (!contactId) { const c = await ghlFindContact(ghlToken, loc, thread.prospect_email); contactId = c?.id; }
    if (!contactId) { await tgSend(token, chatId, "No encontré el contacto en GoHighLevel para mover de etapa."); return new Response("ok"); }
    const ok = await ghlMoveStage(ghlToken, loc, pipe, contactId, stage.id, who);
    await sbInsert("alicia_actions_log", { thread_id: thread.thread_id, action: "ghl_stage", status: ok ? "ok" : "error", detail: { stage: stage.name }, dry_run: false });
    await tgSend(token, chatId, ok ? `✅ ${who} movido a «${stage.name}» en GoHighLevel.` : "❌ No se pudo mover la etapa.");
    return new Response("ok");
  }

  if (NOREPLY.includes(low)) {
    await sbPatch(sel, { estado: "no_responder", pending_draft: null });
    await tgSend(token, chatId, `Ok, no respondo a ${who}. 👍`);
    return new Response("ok");
  }
  if (CANCEL.includes(low)) {
    await sbPatch(sel, { estado: "alertada", pending_draft: null, pending_objetivo: null });
    await tgSend(token, chatId, "Borrador cancelado. Escríbeme de nuevo qué responder cuando quieras.");
    return new Response("ok");
  }

  if (APPROVE.includes(low)) {
    if (!thread.pending_draft) { await tgSend(token, chatId, "No hay borrador pendiente. Respóndele al prospecto con el texto a enviar."); return new Response("ok"); }
    const dryRun = (s.ALICIA_DRY_RUN ?? "true").toLowerCase() !== "false";
    const acct = (await sbGet(`alicia_accounts?select=email,token_env&account_id=eq.${encodeURIComponent(thread.account_id)}&limit=1`))[0];
    if (!acct) { await tgSend(token, chatId, "No encuentro la casilla de esta conversación."); return new Response("ok"); }
    const objetivo = thread.pending_objetivo ?? "";

    if (dryRun) {
      const extra = tieneGhl ? (objetivo ? `\n\nEn GoHighLevel se guardaría el objetivo «${objetivo}» en el contacto ${thread.prospect_email}.` : `\n\n(Sin objetivo; en GoHighLevel solo se buscaría/crearía el contacto.)`) : "";
      await tgSend(token, chatId, `🧪 [PRUEBA] Así se enviaría (NO se envió):\n\nDe: ${acct.email}\nPara: ${thread.prospect_email}\nAsunto: Re: ${thread.subject ?? ""}\n\n${thread.pending_draft}${extra}\n\n(Activa el envío real cuando quieras.)`);
      await sbPatch(sel, { estado: "aprobada" });
      await sbInsert("alicia_actions_log", { thread_id: thread.thread_id, action: "email_sent", status: "skipped_dry_run", detail: { to: thread.prospect_email, objetivo }, dry_run: true });
      return new Response("ok");
    }

    // Envío real
    let sentOk = false;
    try {
      const access = await gmailToken(cc.gmail_client_id, cc.gmail_client_secret, s[acct.token_env]);
      const orig = thread.last_gmail_message_id ? await gmailOrig(access, thread.last_gmail_message_id) : { messageId: "", references: "", subject: thread.subject ?? "" };
      const raw = buildRaw({ from: acct.email, to: thread.prospect_email, subject: thread.subject || orig.subject || "", body: thread.pending_draft, inReplyTo: orig.messageId, references: orig.references });
      const r = await fetch("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", { method: "POST", headers: { Authorization: `Bearer ${access}`, "Content-Type": "application/json" }, body: JSON.stringify({ raw, threadId: thread.thread_id }) });
      sentOk = r.ok;
      await sbInsert("alicia_actions_log", { thread_id: thread.thread_id, action: "email_sent", status: sentOk ? "ok" : "error", detail: { to: thread.prospect_email, http: r.status }, dry_run: false });
    } catch (e) {
      await tgSend(token, chatId, `❌ Error al enviar el correo: ${e}. El borrador quedó guardado.`);
      return new Response("ok");
    }
    if (!sentOk) { await tgSend(token, chatId, "❌ No se pudo enviar el correo. El borrador quedó guardado; reintenta con aprobar."); return new Response("ok"); }

    // GoHighLevel: crear/actualizar contacto + objetivo (solo clientes con GHL).
    let ghlMsg = "";
    if (tieneGhl) {
      try {
        const up = await ghlUpsertContact(s.GHL_TOKEN_GBS, s.GHL_LOCATION_GBS, thread, objetivo, s.GHL_FIELD_OBJETIVO);
        if (up) {
          await sbPatch(sel, { ghl_contact_id: up.id });
          ghlMsg = up.created ? " Contacto creado en GoHighLevel." : " Contacto actualizado en GoHighLevel.";
          if (objetivo) ghlMsg += " Objetivo guardado.";
          await sbInsert("alicia_actions_log", { thread_id: thread.thread_id, action: "ghl_upserted", status: "ok", detail: { contact: up.id, created: up.created, objetivo }, dry_run: false });
        }
      } catch (e) {
        ghlMsg = " (Correo enviado, pero hubo un problema al actualizar GoHighLevel.)";
        await sbInsert("alicia_actions_log", { thread_id: thread.thread_id, action: "ghl_upserted", status: "error", detail: { err: String(e) }, dry_run: false });
      }
    }
    await sbPatch(sel, { estado: "enviada", pending_draft: null, pending_objetivo: null });
    await tgSend(token, chatId, `✅ Enviado a ${who} (${thread.prospect_email}), mismo hilo, desde ${acct.email}.${ghlMsg}`);
    return new Response("ok");
  }

  // Texto libre según el estado del hilo.
  if (thread.estado === "esperando_objetivo") {
    await sbPatch(sel, { estado: "esperando_aprobacion", pending_objetivo: cmd });
    await tgSend(token, chatId, `Objetivo guardado: «${cmd}».\n\nResponde *aprobar* para enviar y sincronizar con GoHighLevel, o *cancelar*.`);
    return new Response("ok");
  }
  if (thread.estado === "esperando_aprobacion") {
    await sbPatch(sel, { pending_objetivo: cmd });
    await tgSend(token, chatId, `Objetivo actualizado: «${cmd}». Responde *aprobar* para enviar, o *cancelar*.`);
    return new Response("ok");
  }
  // Nuevo borrador
  await sbPatch(sel, { estado: "esperando_objetivo", pending_draft: cmd, pending_draft_at: new Date().toISOString(), pending_objetivo: null });
  const sent = await tgSend(token, chatId, `📝 Borrador para ${who} (${thread.account_email}):\n\n«${cmd}»\n\n¿*Objetivo breve de la reunión*? Escríbelo para guardarlo en GoHighLevel, o responde *aprobar* para enviar sin él.`);
  const mid = sent?.result?.message_id;
  if (mid) await sbInsert("alicia_telegram_links", { telegram_message_id: mid, telegram_chat_id: chatId, thread_id: thread.thread_id, account_id: thread.account_id, kind: "draft" });
  return new Response(JSON.stringify({ ok: true }), { status: 200 });
});
