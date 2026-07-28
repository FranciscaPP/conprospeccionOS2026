// Alicia · webhook de Telegram para responder campañas Snov desde el chat.
//
// Flujo: respondes (con "Responder" de Telegram) al mensaje de un prospecto con
// el texto que quieres enviar → Alicia muestra el borrador → escribes "aprobar"
// → envía el correo DESDE la misma casilla, en el MISMO hilo. "no responder"
// descarta; "cancelar" borra el borrador.
//
// Sin IA: el texto que dictas se envía tal cual. La IA (redactar desde una
// instrucción) queda para una etapa posterior, opcional y bajo interruptor.
//
// Modo prueba: si alicia_secrets.ALICIA_DRY_RUN != 'false', al "aprobar" se
// muestra el correo que se enviaría SIN enviarlo de verdad.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const SB_URL = Deno.env.get("SUPABASE_URL")!;
const SB_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SB = (p: string) => `${SB_URL}/rest/v1/${p}`;
const H = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json" };

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
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
  });
  return await r.json().catch(() => ({}));
}

async function gmailAccessToken(secrets: Record<string, string>, tokenEnv: string): Promise<string> {
  const body = new URLSearchParams({
    client_id: secrets.GMAIL_OAUTH_CLIENT_ID,
    client_secret: secrets.GMAIL_OAUTH_CLIENT_SECRET,
    refresh_token: secrets[tokenEnv],
    grant_type: "refresh_token",
  });
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const j = await r.json();
  if (!j.access_token) throw new Error("no access_token: " + JSON.stringify(j));
  return j.access_token;
}

async function getOriginalHeaders(access: string, msgId: string) {
  const url = `https://gmail.googleapis.com/gmail/v1/users/me/messages/${msgId}` +
    `?format=metadata&metadataHeaders=Message-ID&metadataHeaders=References&metadataHeaders=Subject`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${access}` } });
  const j = await r.json();
  const hs = j.payload?.headers ?? [];
  const get = (n: string) => (hs.find((h: any) => h.name.toLowerCase() === n.toLowerCase())?.value ?? "");
  return { messageId: get("Message-ID"), references: get("References"), subject: get("Subject") };
}

function b64url(s: string): string {
  return btoa(unescape(encodeURIComponent(s))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function encHeader(s: string): string {
  // Codifica en MIME encoded-word si hay caracteres no ASCII (acentos, ñ...).
  // deno-lint-ignore no-control-regex
  if (/[^\x00-\x7F]/.test(s)) return `=?UTF-8?B?${btoa(unescape(encodeURIComponent(s)))}?=`;
  return s;
}
function buildRawReply(o: { from: string; to: string; subject: string; body: string; inReplyTo: string; references: string }): string {
  const subj = o.subject.toLowerCase().startsWith("re:") ? o.subject : `Re: ${o.subject}`;
  const lines = [
    `From: ${o.from}`,
    `To: ${o.to}`,
    `Subject: ${encHeader(subj)}`,
    "MIME-Version: 1.0",
    'Content-Type: text/plain; charset="UTF-8"',
  ];
  if (o.inReplyTo) {
    lines.push(`In-Reply-To: ${o.inReplyTo}`);
    lines.push(`References: ${o.references ? o.references + " " + o.inReplyTo : o.inReplyTo}`);
  }
  lines.push("");
  lines.push(o.body);
  return b64url(lines.join("\r\n"));
}

const NOREPLY = ["no responder", "no contestar", "no responderle", "ignorar", "descartar"];
const APPROVE = ["aprobar", "aprobado", "aprueba", "enviar", "envialo", "envíalo", "ok", "ok enviar", "si", "sí"];
const CANCEL = ["cancelar", "cancela", "borrar", "descartar borrador"];

function clean(s: string): string {
  return s.toLowerCase().replace(/[.!¡¿?]/g, "").trim();
}

serve(async (req) => {
  if (req.method !== "POST") return new Response(JSON.stringify({ ok: true }), { status: 200 });

  const secrets = await loadSecrets();
  const expected = secrets.TELEGRAM_WEBHOOK_SECRET ?? "";
  if (expected && req.headers.get("x-telegram-bot-api-secret-token") !== expected) {
    return new Response("forbidden", { status: 401 });
  }
  const token = secrets.TELEGRAM_TOKEN;
  if (!token) return new Response("no token", { status: 200 });

  let update: any;
  try { update = await req.json(); } catch { return new Response("ok", { status: 200 }); }
  const msg = update.message ?? update.edited_message;
  if (!msg || !msg.text) return new Response(JSON.stringify({ ok: true }), { status: 200 });

  const chatId = msg.chat.id;
  const text = String(msg.text).trim();

  // Resolver a qué hilo se refiere: por "Responder" a un mensaje, o por código AL-XXXX.
  let thread: any = null;
  if (msg.reply_to_message) {
    const links = await sbGet(
      `alicia_telegram_links?select=thread_id&telegram_message_id=eq.${msg.reply_to_message.message_id}&limit=1`,
    );
    if (links[0]) {
      const t = await sbGet(`alicia_email_threads?select=*&thread_id=eq.${encodeURIComponent(links[0].thread_id)}&limit=1`);
      thread = t[0];
    }
  }
  if (!thread) {
    const m = text.match(/AL-[A-Z0-9]{8}/i);
    if (m) {
      const t = await sbGet(`alicia_email_threads?select=*&internal_ref=eq.${m[0].toUpperCase()}&limit=1`);
      thread = t[0];
    }
  }
  if (!thread) {
    await tgSend(token, chatId,
      "No supe a qué respuesta te refieres. Usa la función *Responder* de Telegram sobre el mensaje del prospecto, o incluye su código AL-XXXX.");
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }

  const cmd = text.replace(/AL-[A-Z0-9]{8}/i, "").trim();
  const low = clean(cmd);
  const who = thread.prospect_name || thread.prospect_email;
  const threadSel = `alicia_email_threads?thread_id=eq.${encodeURIComponent(thread.thread_id)}`;

  if (NOREPLY.includes(low)) {
    await sbPatch(threadSel, { estado: "no_responder", pending_draft: null });
    await tgSend(token, chatId, `Ok, no respondo a ${who}. 👍`);
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }
  if (CANCEL.includes(low)) {
    await sbPatch(threadSel, { estado: "alertada", pending_draft: null });
    await tgSend(token, chatId, "Borrador cancelado. Escríbeme de nuevo qué responder cuando quieras.");
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }

  if (APPROVE.includes(low)) {
    if (!thread.pending_draft) {
      await tgSend(token, chatId, "No hay borrador pendiente. Respóndele al prospecto con el texto que quieres enviar y te lo muestro antes.");
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }
    const dryRun = (secrets.ALICIA_DRY_RUN ?? "true").toLowerCase() !== "false";
    const acct = (await sbGet(`alicia_accounts?select=email,token_env&account_id=eq.${encodeURIComponent(thread.account_id)}&limit=1`))[0];
    if (!acct) { await tgSend(token, chatId, "No encuentro la casilla de esta conversación."); return new Response("ok"); }

    if (dryRun) {
      await tgSend(token, chatId,
        `🧪 [PRUEBA] Así se enviaría (NO se envió):\n\nDe: ${acct.email}\nPara: ${thread.prospect_email}\nAsunto: Re: ${thread.subject ?? ""}\n\n${thread.pending_draft}\n\n(Cuando confirmes que se ve bien, activo el envío real.)`);
      await sbPatch(threadSel, { estado: "aprobada" });
      await sbInsert("alicia_actions_log", { thread_id: thread.thread_id, action: "email_sent", status: "skipped_dry_run", detail: { to: thread.prospect_email }, dry_run: true });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }

    try {
      const access = await gmailAccessToken(secrets, acct.token_env);
      const orig = thread.last_gmail_message_id ? await getOriginalHeaders(access, thread.last_gmail_message_id) : { messageId: "", references: "", subject: thread.subject ?? "" };
      const raw = buildRawReply({
        from: acct.email, to: thread.prospect_email, subject: thread.subject || orig.subject || "",
        body: thread.pending_draft, inReplyTo: orig.messageId, references: orig.references,
      });
      const r = await fetch("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", {
        method: "POST",
        headers: { Authorization: `Bearer ${access}`, "Content-Type": "application/json" },
        body: JSON.stringify({ raw, threadId: thread.thread_id }),
      });
      const ok = r.ok;
      await sbPatch(threadSel, { estado: ok ? "enviada" : "error", pending_draft: ok ? null : thread.pending_draft });
      await sbInsert("alicia_actions_log", { thread_id: thread.thread_id, action: "email_sent", status: ok ? "ok" : "error", detail: { to: thread.prospect_email, http: r.status }, dry_run: false });
      await tgSend(token, chatId, ok
        ? `✅ Enviado a ${who} (${thread.prospect_email}), en el mismo hilo, desde ${acct.email}.`
        : `❌ Error al enviar (código ${r.status}). El borrador quedó guardado; puedes reintentar con "aprobar".`);
    } catch (e) {
      await tgSend(token, chatId, `❌ Error técnico al enviar: ${e}. El borrador quedó guardado.`);
    }
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  }

  // Cualquier otro texto = el borrador dictado por ti (sin IA).
  await sbPatch(threadSel, { estado: "borrador", pending_draft: cmd, pending_draft_at: new Date().toISOString() });
  const sent = await tgSend(token, chatId,
    `📝 Borrador para ${who} (${thread.account_email}):\n\n«${cmd}»\n\nResponde *aprobar* para enviarlo, o *cancelar*.`);
  const mid = sent?.result?.message_id;
  if (mid) {
    await sbInsert("alicia_telegram_links", { telegram_message_id: mid, telegram_chat_id: chatId, thread_id: thread.thread_id, account_id: thread.account_id, kind: "draft" });
  }
  return new Response(JSON.stringify({ ok: true }), { status: 200 });
});
