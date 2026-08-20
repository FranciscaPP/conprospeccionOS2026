// Alicia · poller automático (Supabase). Multi-cliente. Detección determinística SIN IA.
//
// Corre 2 veces al día (pg_cron). Por cada cuenta habilitada (alicia_accounts),
// usa el permiso de Google de SU cliente (alicia_clients), lee su casilla, filtra
// determinísticamente, enriquece (Snov + GoHighLevel solo si el cliente tiene GHL)
// y envía las tarjetas al bot de Telegram de ESE cliente (aislado). Idempotente
// a nivel de hilo.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const SB_URL = Deno.env.get("SUPABASE_URL")!;
const SB_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SB = (p: string) => `${SB_URL}/rest/v1/${p}`;
const H = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json" };
const GHL = "https://services.leadconnectorhq.com";
const GMAIL = "https://gmail.googleapis.com/gmail/v1";

const CF = { cargo: "c60cJqsxNT5Srdiv7wV3", tamano: "3uQfRamZN2ruaNg367XL", liPer: "iimkT4RjJWRONU2HcwbN", liEmp: "SnRP2tiJlYfQOHBM3adE", industria: "p2CZgSN3D0kvNPo9wBeq" };
const MEETING = ["reunion", "reunión", "reunir", "meeting", "agendar", "agenda", "disponib", "horario", "cuando podemos", "cuándo", "llamada", " call", "zoom", "teams", "meet", "conversar", "coordinar"];

async function sbGet(p: string): Promise<any[]> { const r = await fetch(SB(p), { headers: H }); return r.ok ? await r.json() : []; }
async function sbUpsert(t: string, b: unknown, c: string) { await fetch(SB(`${t}?on_conflict=${c}`), { method: "POST", headers: { ...H, Prefer: "resolution=merge-duplicates,return=minimal" }, body: JSON.stringify(b) }); }
async function sbInsert(t: string, b: unknown) { await fetch(SB(t), { method: "POST", headers: { ...H, Prefer: "return=minimal" }, body: JSON.stringify(b) }); }
async function loadSecrets(): Promise<Record<string, string>> { const rows = await sbGet("alicia_secrets?select=name,value"); const m: Record<string, string> = {}; for (const r of rows) m[r.name] = r.value; return m; }

async function gmailToken(clientId: string, clientSecret: string, refresh: string): Promise<string> {
  const body = new URLSearchParams({ client_id: clientId, client_secret: clientSecret, refresh_token: refresh, grant_type: "refresh_token" });
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
  const j = await r.json(); if (!j.access_token) throw new Error("no token"); return j.access_token;
}
async function gmailList(a: string, q: string): Promise<string[]> {
  const ids: string[] = []; let pt = "";
  do { const u = new URL(`${GMAIL}/users/me/messages`); u.searchParams.set("q", q); u.searchParams.set("maxResults", "50"); if (pt) u.searchParams.set("pageToken", pt);
    const r = await fetch(u, { headers: { Authorization: `Bearer ${a}` } }); const j = await r.json(); (j.messages ?? []).forEach((m: any) => ids.push(m.id)); pt = j.nextPageToken ?? "";
  } while (pt && ids.length < 150); return ids;
}
const MH = ["From", "Subject", "Date", "Return-Path", "Content-Type", "Auto-Submitted", "Precedence", "In-Reply-To", "References", "X-Autoreply", "X-Autorespond", "X-Auto-Response-Suppress"];
async function gmailMeta(a: string, id: string): Promise<any> { const u = new URL(`${GMAIL}/users/me/messages/${id}`); u.searchParams.set("format", "metadata"); MH.forEach(h => u.searchParams.append("metadataHeaders", h)); const r = await fetch(u, { headers: { Authorization: `Bearer ${a}` } }); return await r.json(); }

function hget(hs: any[], n: string): string { const f = (hs ?? []).find((h: any) => h.name.toLowerCase() === n.toLowerCase()); return f ? String(f.value) : ""; }
function senderEmail(x: string): string { const m = x.match(/[\w.\-+']+@[\w.\-]+\.\w+/); return m ? m[0].toLowerCase() : ""; }
function dispName(x: string): string { const m = x.match(/^\s*"?([^"<]+?)"?\s*</); return m ? m[1].trim() : ""; }
const BOUNCE_S = ["mailer-daemon", "postmaster", "mail delivery subsystem"];
const BOUNCE_J = ["undelivered", "undeliverable", "delivery status notification", "returned mail", "failure notice", "no se pudo entregar", "correo no entregado", "mail delivery failed"];
const OOO = ["out of office", "automatic reply", "auto-reply", "autoreply", "respuesta automática", "respuesta automatica", "fuera de la oficina", "fuera de oficina", "de vacaciones", "on vacation"];
const SYS = ["no-reply", "noreply", "no_reply", "donotreply", "do-not-reply", "notify-noreply", "mailer-daemon", "postmaster", "dmarc", "abuse@", "bounce@", "bounces@", "notifications@", "mailer@"];
function classify(hs: any[], labels: string[]): string {
  if ((labels ?? []).map(x => String(x).toUpperCase()).includes("SPAM")) return "spam";
  const from = hget(hs, "From").toLowerCase(), subj = hget(hs, "Subject").toLowerCase(), ct = hget(hs, "Content-Type").toLowerCase(), rp = hget(hs, "Return-Path").trim();
  if (BOUNCE_S.some(s => from.includes(s)) || BOUNCE_J.some(s => subj.includes(s)) || (ct.includes("multipart/report") && ct.includes("delivery-status")) || rp === "<>") return "bounce";
  if (OOO.some(s => subj.includes(s)) || hget(hs, "X-Auto-Response-Suppress")) return "out_of_office";
  const au = hget(hs, "Auto-Submitted").toLowerCase(), pr = hget(hs, "Precedence").toLowerCase();
  if (["auto-replied", "auto-generated", "auto_replied", "auto_generated"].some(t => au.includes(t)) || ["auto_reply", "bulk", "junk", "list"].some(t => pr.includes(t)) || hget(hs, "X-Autoreply") || hget(hs, "X-Autorespond")) return "auto_reply";
  return "genuine";
}
function isSystemSender(e: string): boolean { if (!e) return true; return SYS.some(t => e.includes(t)); }
function isReply(hs: any[]): boolean { if (hget(hs, "In-Reply-To") || hget(hs, "References")) return true; return hget(hs, "Subject").trim().toLowerCase().startsWith("re:"); }
async function internalRef(t: string): Promise<string> { const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t)); return "AL-" + [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("").slice(0, 8).toUpperCase(); }
function fmtFecha(d: string): string { if (!d) return ""; const x = new Date(d); if (isNaN(x.getTime())) return d; try { return new Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(x); } catch { return x.toISOString().slice(0, 16).replace("T", " "); } }
function esc(x: unknown): string { return String(x ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

async function snovMatch(email: string): Promise<{ cliente?: string; campaign?: string }> {
  const ev = await sbGet(`snov_email_events?select=snov_campaign_id,cliente_slug&prospect_email=eq.${encodeURIComponent(email)}&order=occurred_at.desc&limit=1`);
  if (!ev[0]) { const pr = await sbGet(`snov_prospects?select=cliente_slug&email=eq.${encodeURIComponent(email)}&limit=1`); return pr[0] ? { cliente: pr[0].cliente_slug } : {}; }
  let campaign: string | undefined; const cid = ev[0].snov_campaign_id;
  if (cid) { const c = await sbGet(`snov_campaigns?select=nombre&snov_campaign_id=eq.${encodeURIComponent(cid)}&limit=1`); campaign = c[0]?.nombre ?? cid; }
  return { cliente: ev[0].cliente_slug, campaign };
}

// ---- GoHighLevel (solo clientes con GHL, hoy gbs) ----
function ghlH(t: string) { return { Authorization: `Bearer ${t}`, Version: "2021-07-28", Accept: "application/json" }; }
async function ghlContact(token: string, loc: string, email: string): Promise<any | null> {
  const r = await fetch(`${GHL}/contacts/?locationId=${loc}&query=${encodeURIComponent(email)}&limit=5`, { headers: ghlH(token) });
  const d = await r.json().catch(() => ({})); const cs = d.contacts ?? [];
  const hit = cs.find((c: any) => (c.email ?? "").toLowerCase() === email.toLowerCase()) ?? cs[0]; if (!hit) return null;
  const rf = await fetch(`${GHL}/contacts/${hit.id}`, { headers: ghlH(token) }); const df = await rf.json().catch(() => ({})); return df.contact ?? hit;
}
function cfVal(contact: any, id: string): string { const f = (contact?.customFields ?? []).find((x: any) => x.id === id); const v = f?.value; return Array.isArray(v) ? v.join(", ") : String(v ?? ""); }
async function ghlSlots(token: string, calId: string): Promise<string[]> {
  const start = Date.now(), end = start + 7 * 864e5;
  const r = await fetch(`${GHL}/calendars/${calId}/free-slots?startDate=${start}&endDate=${end}&timezone=America/Santiago`, { headers: ghlH(token) });
  const d = await r.json().catch(() => ({})); const out: string[] = [];
  for (const k of Object.keys(d)) { if (!/^\d{4}-\d{2}-\d{2}$/.test(k)) continue; for (const sl of (d[k]?.slots ?? []).slice(0, 2)) { const dt = new Date(sl); if (!isNaN(dt.getTime())) out.push(new Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago", weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(dt)); } if (out.length >= 6) break; }
  return out;
}

async function tgSend(token: string, chatId: string, text: string): Promise<any> {
  const r = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: chatId, text, parse_mode: "HTML", disable_web_page_preview: true }) });
  return await r.json().catch(() => ({}));
}

function cardText(c: any): string {
  const cli = (c.cliente_slug || "").toUpperCase();
  const camp = c.campaign ? esc(c.campaign) : "(por identificar)";
  let txt = `<b>${esc(cli)}</b>\n\n`;
  txt += `🟢 [${c.internal_ref}] ${esc(c.prospect_name)} · ${esc(c.empresa)}\n`;
  txt += `Cuenta: ${esc(c.account_email)}\nCampaña: ${camp}\nFecha respuesta: ${esc(c.fecha)}\n`;
  txt += `Asunto: ${esc(c.subject)}\nMensaje: ${esc(String(c.last_message_snippet).slice(0, 280))}\n`;
  const ct = c.contact;
  if (ct) {
    txt += `\n<b>Contacto (GoHighLevel):</b>\n`;
    txt += `Correo: ${esc(ct.email ?? c.prospect_email)} · Tel: ${esc(ct.phone ?? "—")}\n`;
    txt += `Cargo: ${esc(cfVal(ct, CF.cargo) || ct.title || "—")} · Industria: ${esc(cfVal(ct, CF.industria) || "—")}\n`;
    txt += `Empresa: ${esc(ct.companyName ?? c.empresa)} · Tamaño: ${esc(cfVal(ct, CF.tamano) || "—")}\n`;
    txt += `Web: ${esc(ct.website ?? "—")}\n`;
    txt += `LinkedIn persona: ${esc(cfVal(ct, CF.liPer) || "—")}\nLinkedIn empresa: ${esc(cfVal(ct, CF.liEmp) || "—")}\n`;
  }
  if (c.slots?.length) txt += `\n📅 <b>Horarios disponibles:</b> ${esc(c.slots.join(" · "))}\n`;
  txt += `\n↩️ Para responder: responde a ESTE mensaje con el texto que quieres enviar.`;
  return txt;
}

serve(async (req) => {
  const s = await loadSecrets();
  if ((s.ALICIA_POLL_SECRET ?? "") && req.headers.get("x-alicia-secret") !== s.ALICIA_POLL_SECRET) return new Response("forbidden", { status: 401 });
  const lookback = parseInt(s.ALICIA_LOOKBACK_HOURS ?? "22", 10) || 22;

  // Config por cliente (bot + permiso Google).
  const clientRows = await sbGet("alicia_clients?select=cliente_slug,telegram_token,telegram_chat_id,gmail_client_id,gmail_client_secret&activo=eq.true");
  const clients: Record<string, any> = {}; for (const c of clientRows) clients[c.cliente_slug] = c;
  const ghlToken = s.GHL_TOKEN_GBS, ghlLoc = s.GHL_LOCATION_GBS, ghlCal = s.GHL_CALENDAR_GBS;

  const accounts = await sbGet("alicia_accounts?select=account_id,email,token_env,cliente_slug&enabled=eq.true");
  const stats = { scanned: 0, nuevas: 0, filtradas: 0 };
  const cardsByClient: Record<string, any[]> = {};

  for (const acct of accounts) {
    const cli = acct.cliente_slug; const cc = clients[cli];
    if (!cc || !cc.gmail_client_id) continue;
    let access: string; try { access = await gmailToken(cc.gmail_client_id, cc.gmail_client_secret, s[acct.token_env]); } catch { continue; }
    const ids = await gmailList(access, `in:inbox newer_than:${lookback}h`); const seen = new Set<string>();
    for (const id of ids) {
      const meta = await gmailMeta(access, id); const threadId = String(meta.threadId ?? id);
      if (seen.has(threadId)) continue; seen.add(threadId); stats.scanned++;
      const hs = meta.payload?.headers ?? []; const from = senderEmail(hget(hs, "From"));
      if (classify(hs, meta.labelIds ?? []) !== "genuine" || isSystemSender(from) || !isReply(hs)) { stats.filtradas++; continue; }
      const existing = (await sbGet(`alicia_email_threads?select=thread_id,last_gmail_message_id&thread_id=eq.${encodeURIComponent(threadId)}&limit=1`))[0];
      if (existing && existing.last_gmail_message_id === id) continue;

      const match = await snovMatch(from); const ref = await internalRef(threadId);
      const subject = hget(hs, "Subject").slice(0, 200); const snippet = String(meta.snippet ?? "").slice(0, 400);
      const cliente = match.cliente ?? cli;
      const row = { thread_id: threadId, internal_ref: ref, account_id: acct.account_id, account_email: acct.email, prospect_email: from, prospect_name: dispName(hget(hs, "From")) || from, cliente_slug: cliente, subject, last_message_snippet: snippet, last_gmail_message_id: id, classification: "genuine", estado: "alertada", dry_run: true, last_seen_at: new Date().toISOString() };
      await sbUpsert("alicia_email_threads", row, "thread_id"); stats.nuevas++;

      // GoHighLevel + calendario solo para clientes con GHL (hoy gbs).
      let contact: any = null, slots: string[] = [];
      if (cli === "gbs" && ghlToken && ghlLoc) {
        try { contact = await ghlContact(ghlToken, ghlLoc, from); } catch { contact = null; }
        if (ghlCal && MEETING.some(k => (subject + " " + snippet).toLowerCase().includes(k))) { try { slots = await ghlSlots(ghlToken, ghlCal); } catch { slots = []; } }
      }
      (cardsByClient[cli] ||= []).push({ ...row, fecha: fmtFecha(hget(hs, "Date")), campaign: match.campaign, empresa: from.split("@")[1], contact, slots });
    }
  }

  // Enviar cada cliente a SU bot (aislado).
  for (const [cli, cards] of Object.entries(cardsByClient)) {
    const cc = clients[cli]; if (!cc?.telegram_token || !cc?.telegram_chat_id || !cards.length) continue;
    await tgSend(cc.telegram_token, cc.telegram_chat_id, `🔔 <b>Alicia</b> · ${cards.length} respuesta(s) nueva(s):`);
    for (const c of cards) {
      const sent = await tgSend(cc.telegram_token, cc.telegram_chat_id, cardText(c)); const mid = sent?.result?.message_id;
      if (mid) await sbInsert("alicia_telegram_links", { telegram_message_id: mid, telegram_chat_id: Number(cc.telegram_chat_id), thread_id: c.thread_id, account_id: c.account_id, kind: "alert" });
    }
  }

  await sbInsert("alicia_runs", { finished_at: new Date().toISOString(), accounts_checked: accounts.length, messages_scanned: stats.scanned, replies_detected: stats.nuevas, filtered_out: { filtradas: stats.filtradas }, status: "success", dry_run: true });
  return new Response(JSON.stringify({ ok: true, ...stats }), { status: 200, headers: { "Content-Type": "application/json" } });
});
