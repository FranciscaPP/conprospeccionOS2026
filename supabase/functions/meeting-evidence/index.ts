// Evidencia/IA de reuniones → Supabase.
// Endpoint genérico para tl;dv/Google Meet/Fathom/manual: actualiza la misma
// reunión que ya leen el panel interno y los portales de GBS/BambuTech.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const SB = (path: string) => `${SUPABASE_URL}/rest/v1/${path}`;
const SB_HEADERS = {
  apikey: SUPABASE_SERVICE_KEY,
  Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
  "Content-Type": "application/json",
};
const ACTIVE_CLIENTS = new Set(["gbs", "bambutech"]);

function text(...values: unknown[]): string {
  for (const value of values) {
    const candidate = String(value ?? "").trim();
    if (candidate) return candidate;
  }
  return "";
}

function clientSlug(value: unknown): string {
  const slug = String(value ?? "").trim().toLowerCase();
  if (slug === "bambootech") return "bambutech";
  if (slug === "gbs_logistics") return "gbs";
  return slug;
}

function firstArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function evidencePayload(input: Record<string, unknown>) {
  const summary = text(
    input.ai_summary,
    input.summary,
    input.meeting_summary,
    input.transcript_summary,
    input.analysis,
  );
  const evidence = text(
    input.ai_evidence,
    input.evidence,
    input.validation_summary,
    input.notes,
  );
  const recording = text(
    input.recording_url,
    input.recordingUrl,
    input.recording,
    input.video_url,
    input.videoUrl,
  );
  const transcript = text(
    input.transcript_url,
    input.transcriptUrl,
    input.transcript,
    input.transcript_link,
  );
  const recommendation = text(
    input.ai_recommendation,
    input.recommendation,
    input.next_step,
    input.nextStep,
  );
  const confidenceRaw = text(input.ai_confidence, input.confidence);
  const confidence = confidenceRaw ? Number(confidenceRaw) : undefined;
  const bant = firstArray(input.ai_bant_detected ?? input.bant_detected ?? input.bant);

  const row: Record<string, unknown> = {};
  if (recording) row.recording_url = recording;
  if (transcript) row.transcript_url = transcript;
  if (summary) row.ai_summary = summary;
  if (evidence) row.ai_evidence = evidence;
  if (bant.length) row.ai_bant_detected = bant;
  if (recommendation) row.ai_recommendation = recommendation;
  if (Number.isFinite(confidence)) row.ai_confidence = confidence;
  row.synced_at = new Date().toISOString();
  return row;
}

async function rows(path: string): Promise<Record<string, unknown>[]> {
  const response = await fetch(SB(path), { headers: SB_HEADERS });
  if (!response.ok) return [];
  const data = await response.json();
  return Array.isArray(data) ? data : [];
}

async function findMeeting(payload: Record<string, unknown>) {
  const reunionId = text(payload.reunion_id, payload.meeting_id, payload.id);
  if (reunionId && /^\d+$/.test(reunionId)) {
    const found = await rows(`reuniones?select=id,cliente_slug&id=eq.${reunionId}&limit=1`);
    if (found[0]) return found[0];
  }

  const appointmentId = text(
    payload.ghl_appointment_id,
    payload.appointment_id,
    payload.appointmentId,
    payload.calendar_event_id,
    payload.event_id,
    payload.eventId,
  );
  if (appointmentId) {
    const found = await rows(
      `reuniones?select=id,cliente_slug&ghl_appointment_id=eq.${encodeURIComponent(appointmentId)}&limit=1`,
    );
    if (found[0]) return found[0];
  }

  const email = text(payload.email, payload.contact_email, payload.contactEmail).toLowerCase();
  const slug = clientSlug(payload.cliente_slug ?? payload.client_slug ?? payload.client);
  if (email && slug) {
    const found = await rows(
      `reuniones?select=id,cliente_slug&cliente_slug=eq.${encodeURIComponent(slug)}` +
        `&email=ilike.${encodeURIComponent(email)}&order=fecha_reunion.desc&limit=1`,
    );
    if (found[0]) return found[0];
  }
  return null;
}

async function patchTable(path: string, body: Record<string, unknown>) {
  return await fetch(SB(path), {
    method: "PATCH",
    headers: { ...SB_HEADERS, Prefer: "return=minimal" },
    body: JSON.stringify(body),
  });
}

serve(async (req) => {
  if (req.method === "GET") {
    return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
  }
  if (req.method !== "POST") {
    return new Response("method not allowed", { status: 405 });
  }

  let payload: Record<string, unknown>;
  try {
    payload = await req.json();
  } catch {
    return new Response("bad json", { status: 400 });
  }

  const meeting = await findMeeting(payload);
  if (!meeting?.id) {
    return new Response(JSON.stringify({ error: "meeting not found" }), { status: 404 });
  }
  const slug = clientSlug(meeting.cliente_slug);
  if (!ACTIVE_CLIENTS.has(slug)) {
    return new Response(JSON.stringify({ ignored: `inactive client ${slug}` }), { status: 200 });
  }

  const evidence = evidencePayload(payload);
  const usefulKeys = Object.keys(evidence).filter((key) => key !== "synced_at");
  if (!usefulKeys.length) {
    return new Response(JSON.stringify({ error: "no evidence fields" }), { status: 400 });
  }

  const reunionId = Number(meeting.id);
  const meetingResponse = await patchTable(`reuniones?id=eq.${reunionId}`, evidence);
  if (!meetingResponse.ok) {
    return new Response(JSON.stringify({ error: await meetingResponse.text() }), { status: 500 });
  }

  const trackingPayload = {
    reunion_id: reunionId,
    cliente_slug: slug,
    recording_url: evidence.recording_url,
    transcript_url: evidence.transcript_url,
    ai_summary: evidence.ai_summary,
    ai_evidence: evidence.ai_evidence,
    ai_bant_detected: evidence.ai_bant_detected,
    ai_confidence: evidence.ai_confidence,
    updated_at: new Date().toISOString(),
  };
  const cleanedTracking = Object.fromEntries(
    Object.entries(trackingPayload).filter(([, value]) => value !== undefined && value !== ""),
  );
  const trackingResponse = await fetch(SB("seguimiento_reuniones?on_conflict=reunion_id"), {
    method: "POST",
    headers: { ...SB_HEADERS, Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify(cleanedTracking),
  });
  if (!trackingResponse.ok) {
    return new Response(JSON.stringify({ error: await trackingResponse.text() }), { status: 500 });
  }

  return new Response(
    JSON.stringify({ ok: true, cliente: slug, reunion_id: reunionId, updated: usefulKeys }),
    { status: 200 },
  );
});
