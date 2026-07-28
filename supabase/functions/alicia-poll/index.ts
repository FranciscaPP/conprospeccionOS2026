// Alicia · poller automático (Supabase). Detección determinística SIN IA.
//
// Corre 2 veces al día (pg_cron). Lee las casillas GBS por Gmail API, clasifica
// por código (rebote/OOO/auto/spam/sistema), se queda con respuestas humanas
// reales, enriquece con Snov (cliente/campaña) cuando hay dato, y manda a
// Telegram un resumen + una tarjeta accionable por hilo. Idempotente a nivel de
// hilo: solo alerta hilos nuevos o con una respuesta más nueva que la última
// avisada (así también captura la continuación de una conversación).
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const SB_URL = Deno.env.get("SUPABASE_URL")!;
const SB_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SB = (p: string) => `${SB_URL}/rest/v1/${p}`;
const H = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json" };

async function sbGet(p: string): Promise<any[]> {
  const r = await fetch(SB(p), { headers: H });
  return r.ok ? await r.json() : [];
}
async function sbUpsert(table: string, body: unknown, onConflict: string) {
  await fetch(SB(`${table}?on_conflict=${onConflict}`), {
    method: "POST",
    headers: { ...H, Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify(body),
  });
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

async function gmailToken(secrets: Record<string, string>, tokenEnv: string): Promise<string> {
  const body = new URLSearchParams({
    client_id: secrets.GMAIL_OAUTH_CLIENT_ID,
    client_secret: secrets.GMAIL_OAUTH_CLIENT_SECRET,
    refresh_token: secrets[tokenEnv],
    grant_type: "refresh_token",
  });
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body,
  });
  const j = await r.json();
  if (!j.access_token) throw new Error("no access_token");
  return j.access_token;
}

async function gmailList(access: string, q: string): Promise<string[]> {
  const ids: string[] = [];
  let pageToken = "";
  do {
    const url = new URL("https://gmail.googleapis.com/gmail/v1/users/me/messages");
    url.searchParams.set("q", q);
    url.searchParams.set("maxResults", "50");
    if (pageToken) url.searchParams.set("pageToken", pageToken);
    const r = await fetch(url, { headers: { Authorization: `Bearer ${access}` } });
    const j = await r.json();
    (j.messages ?? []).forEach((m: any) => ids.push(m.id));
    pageToken = j.nextPageToken ?? "";
  } while (pageToken && ids.length < 150);
  return ids;
}

const META_HEADERS = ["From", "Subject", "Date", "Return-Path", "Content-Type", "Auto-Submitted",
  "Precedence", "In-Reply-To", "References", "X-Autoreply", "X-Autorespond", "X-Auto-Response-Suppress"];

async function gmailMeta(access: string, id: string): Promise<any> {
  const url = new URL(`https://gmail.googleapis.com/gmail/v1/users/me/messages/${id}`);
  url.searchParams.set("format", "metadata");
  META_HEADERS.forEach((h) => url.searchParams.append("metadataHeaders", h));
  const r = await fetch(url, { headers: { Authorization: `Bearer ${access}` } });
  return await r.json();
}

function hget(headers: any[], name: string): string {
  const f = (headers ?? []).find((h: any) => h.name.toLowerCase() === name.toLowerCase());
  return f ? String(f.value) : "";
}
function senderEmail(fromRaw: string): string {
  const m = fromRaw.match(/[\w.\-+']+@[\w.\-]+\.\w+/);
  return m ? m[0].toLowerCase() : "";
}
function dispName(fromRaw: string): string {
  const m = fromRaw.match(/^\s*"?([^"<]+?)"?\s*</);
  return m ? m[1].trim() : "";
}

const BOUNCE_SENDERS = ["mailer-daemon", "postmaster", "mail delivery subsystem"];
const BOUNCE_SUBJ = ["undelivered", "undeliverable", "delivery status notification", "returned mail", "failure notice", "no se pudo entregar", "correo no entregado", "mail delivery failed"];
const OOO = ["out of office", "automatic reply", "auto-reply", "autoreply", "respuesta automática", "respuesta automatica", "fuera de la oficina", "fuera de oficina", "de vacaciones", "on vacation"];
const SYS = ["no-reply", "noreply", "no_reply", "donotreply", "do-not-reply", "notify-noreply", "mailer-daemon", "postmaster", "dmarc", "abuse@", "bounce@", "bounces@", "notifications@", "mailer@"];

function classify(headers: any[], labels: string[]): string {
  if ((labels ?? []).map((x) => String(x).toUpperCase()).includes("SPAM")) return "spam";
  const from = hget(headers, "From").toLowerCase();
  const subj = hget(headers, "Subject").toLowerCase();
  const ct = hget(headers, "Content-Type").toLowerCase();
  const rp = hget(headers, "Return-Path").trim();
  if (BOUNCE_SENDERS.some((s) => from.includes(s)) || BOUNCE_SUBJ.some((s) => subj.includes(s)) ||
      (ct.includes("multipart/report") && ct.includes("delivery-status")) || rp === "<>") return "bounce";
  if (OOO.some((s) => subj.includes(s)) || hget(headers, "X-Auto-Response-Suppress")) return "out_of_office";
  const autoSub = hget(headers, "Auto-Submitted").toLowerCase();
  const prec = hget(headers, "Precedence").toLowerCase();
  if (["auto-replied", "auto-generated", "auto_replied", "auto_generated"].some((t) => autoSub.includes(t)) ||
      ["auto_reply", "bulk", "junk", "list"].some((t) => prec.includes(t)) ||
      hget(headers, "X-Autoreply") || hget(headers, "X-Autorespond")) return "auto_reply";
  return "genuine";
}
function isSystemSender(email: string): boolean {
  if (!email) return true;
  return SYS.some((t) => email.includes(t));
}
function isReply(headers: any[]): boolean {
  if (hget(headers, "In-Reply-To") || hget(headers, "References")) return true;
  return hget(headers, "Subject").trim().toLowerCase().startsWith("re:");
}
async function internalRef(threadId: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(threadId));
  const hex = [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  return "AL-" + hex.slice(0, 8).toUpperCase();
}
function fmtFecha(dateHeader: string): string {
  if (!dateHeader) return "";
  const d = new Date(dateHeader);
  if (isNaN(d.getTime())) return dateHeader;
  try {
    return new Intl.DateTimeFormat("es-CL", {
      timeZone: "America/Santiago", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(d);
  } catch {
    return d.toISOString().slice(0, 16).replace("T", " ");
  }
}

async function snovMatch(email: string): Promise<{ cliente?: string; campaign?: string; matched: boolean }> {
  const ev = await sbGet(`snov_email_events?select=snov_campaign_id,cliente_slug&prospect_email=eq.${encodeURIComponent(email)}&order=occurred_at.desc&limit=1`);
  if (!ev[0]) {
    const pr = await sbGet(`snov_prospects?select=cliente_slug&email=eq.${encodeURIComponent(email)}&limit=1`);
    if (pr[0]) return { cliente: pr[0].cliente_slug, matched: true };
    return { matched: false };
  }
  let campaign: string | undefined;
  const cid = ev[0].snov_campaign_id;
  if (cid) {
    const c = await sbGet(`snov_campaigns?select=nombre&snov_campaign_id=eq.${encodeURIComponent(cid)}&limit=1`);
    campaign = c[0]?.nombre ?? cid;
  }
  return { cliente: ev[0].cliente_slug, campaign, matched: true };
}

async function tgSend(token: string, chatId: string, text: string): Promise<any> {
  const r = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
  });
  return await r.json().catch(() => ({}));
}

serve(async (req) => {
  const secrets = await loadSecrets();
  const expected = secrets.ALICIA_POLL_SECRET ?? "";
  if (expected && req.headers.get("x-alicia-secret") !== expected) {
    return new Response("forbidden", { status: 401 });
  }
  const token = secrets.TELEGRAM_TOKEN;
  const chatId = secrets.TELEGRAM_CHAT_ID;
  const lookback = parseInt(secrets.ALICIA_LOOKBACK_HOURS ?? "22", 10) || 22;
  const accounts = await sbGet("alicia_accounts?select=account_id,email,token_env,cliente_slug&enabled=eq.true");

  const stats = { scanned: 0, nuevas: 0, filtradas: 0 };
  const cards: { thread: any; msgId: string }[] = [];

  for (const acct of accounts) {
    let access: string;
    try { access = await gmailToken(secrets, acct.token_env); } catch { continue; }
    const ids = await gmailList(access, `in:inbox newer_than:${lookback}h`);
    const seen = new Set<string>();
    for (const id of ids) {
      const meta = await gmailMeta(access, id);
      const threadId = String(meta.threadId ?? id);
      if (seen.has(threadId)) continue; // solo el más nuevo por hilo
      seen.add(threadId);
      stats.scanned++;
      const headers = meta.payload?.headers ?? [];
      const cls = classify(headers, meta.labelIds ?? []);
      const from = senderEmail(hget(headers, "From"));
      if (cls !== "genuine" || isSystemSender(from) || !isReply(headers)) { stats.filtradas++; continue; }

      const existing = (await sbGet(`alicia_email_threads?select=thread_id,last_gmail_message_id&thread_id=eq.${encodeURIComponent(threadId)}&limit=1`))[0];
      if (existing && existing.last_gmail_message_id === id) continue; // ya avisado

      const match = await snovMatch(from);
      const ref = await internalRef(threadId);
      const subject = hget(headers, "Subject").slice(0, 200);
      const snippet = String(meta.snippet ?? "").slice(0, 400);
      const row = {
        thread_id: threadId, internal_ref: ref, account_id: acct.account_id, account_email: acct.email,
        prospect_email: from, prospect_name: dispName(hget(headers, "From")) || from,
        snov_campaign_id: null, cliente_slug: match.cliente ?? acct.cliente_slug, subject,
        last_message_snippet: snippet, last_gmail_message_id: id,
        classification: "genuine", estado: "alertada", dry_run: true,
        last_seen_at: new Date().toISOString(),
      };
      await sbUpsert("alicia_email_threads", row, "thread_id");
      stats.nuevas++;
      cards.push({ thread: { ...row, fecha: fmtFecha(hget(headers, "Date")), campaign: match.campaign, empresa: from.split("@")[1] }, msgId: id });
    }
  }

  if (token && chatId && cards.length > 0) {
    await tgSend(token, chatId, `🔔 Alicia · ${cards.length} respuesta(s) nueva(s) de campañas GBS:`);
    for (const c of cards) {
      const t = c.thread;
      const camp = t.campaign ? `Campaña: ${t.campaign}` : "Campaña: (por identificar)";
      const txt = `🟢 [${t.internal_ref}] ${t.prospect_name} · ${t.empresa}\n` +
        `Cuenta: ${t.account_email}\n${camp}\nFecha respuesta: ${t.fecha}\n` +
        `Asunto: ${t.subject}\nMensaje: ${String(t.last_message_snippet).slice(0, 280)}\n\n` +
        `↩️ Para responder: responde a ESTE mensaje con el texto que quieres enviar.`;
      const sent = await tgSend(token, chatId, txt);
      const mid = sent?.result?.message_id;
      if (mid) {
        await sbInsert("alicia_telegram_links", { telegram_message_id: mid, telegram_chat_id: Number(chatId), thread_id: t.thread_id, account_id: t.account_id, kind: "alert" });
      }
    }
  }

  await sbInsert("alicia_runs", {
    finished_at: new Date().toISOString(), accounts_checked: accounts.length,
    messages_scanned: stats.scanned, replies_detected: stats.nuevas,
    filtered_out: { filtradas: stats.filtradas }, status: "success", dry_run: true,
  });

  return new Response(JSON.stringify({ ok: true, ...stats }), { status: 200, headers: { "Content-Type": "application/json" } });
});
