import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type TldvWebhookPayload = {
  appointmentId?: string;
  ghlAppointmentId?: string;
  meetingId?: string;
  title?: string;
  meetingTitle?: string;
  meetingUrl?: string;
  googleMeetUrl?: string;
  recordingUrl?: string;
  videoUrl?: string;
  transcriptUrl?: string;
  transcript?: string;
  summary?: string;
  aiSummary?: string;
  aiRecommendation?: string;
  bantDetected?: string[] | string;
  aiConfidence?: number;
};

function getSupabaseConfig() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key =
    process.env.SUPABASE_SECRET_KEY ||
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    process.env.SUPABASE_SERVICE_KEY ||
    process.env.SUPABASE_KEY;

  if (!url || !key) {
    throw new Error("Faltan SUPABASE_URL y SUPABASE_SECRET_KEY/SUPABASE_SERVICE_ROLE_KEY en el entorno.");
  }

  return {
    restUrl: `${url.replace(/\/$/, "").replace(/\/rest\/v1$/, "")}/rest/v1`,
    key,
  };
}

function firstText(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

function meetCode(value = "") {
  return value.match(/[a-z]{3}-[a-z]{4}-[a-z]{3}/i)?.[0]?.toLowerCase() || "";
}

function normalizeBant(value: TldvWebhookPayload["bantDetected"]) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string" && value.trim()) {
    return value
      .split(/[,;|]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function buildPatch(body: TldvWebhookPayload) {
  const recordingUrl = firstText(body.recordingUrl, body.videoUrl);
  const transcriptUrl = firstText(body.transcriptUrl);
  const transcript = firstText(body.transcript);
  const summary = firstText(body.aiSummary, body.summary);
  const bantDetected = normalizeBant(body.bantDetected);

  return Object.fromEntries(
    Object.entries({
      recording_url: recordingUrl || undefined,
      transcript_url: transcriptUrl || undefined,
      ai_summary: summary || transcript.slice(0, 1200) || undefined,
      ai_evidence: transcript || summary || undefined,
      ai_bant_detected: bantDetected.length ? bantDetected : undefined,
      ai_recommendation: firstText(body.aiRecommendation) || undefined,
      ai_confidence: typeof body.aiConfidence === "number" ? body.aiConfidence : undefined,
      ai_dispute_flag: false,
      synced_at: new Date().toISOString(),
    }).filter(([, value]) => value !== undefined)
  );
}

async function patchMeeting(search: URLSearchParams, payload: Record<string, unknown>) {
  const config = getSupabaseConfig();
  const response = await fetch(`${config.restUrl}/reuniones?${search.toString()}`, {
    method: "PATCH",
    headers: {
      apikey: config.key,
      Authorization: `Bearer ${config.key}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Supabase reuniones ${response.status}: ${body.slice(0, 300)}`);
  }

  return (await response.json()) as unknown[];
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as TldvWebhookPayload;
    const appointmentId = firstText(body.appointmentId, body.ghlAppointmentId, body.meetingId);
    const meetingUrl = firstText(body.meetingUrl, body.googleMeetUrl);
    const code = meetCode(meetingUrl);
    const payload = buildPatch(body);

    if (Object.keys(payload).length === 0) {
      return NextResponse.json({ error: "No hay evidencia para guardar." }, { status: 400 });
    }

    let rows: unknown[] = [];
    let matchedBy = "";

    if (appointmentId) {
      rows = await patchMeeting(new URLSearchParams({ ghl_appointment_id: `eq.${appointmentId}` }), payload);
      matchedBy = "ghl_appointment_id";
    }

    if (!rows.length && code) {
      rows = await patchMeeting(new URLSearchParams({ direccion_reunion: `ilike.*${code}*` }), payload);
      matchedBy = "meeting_url";
    }

    if (!rows.length) {
      return NextResponse.json(
        {
          ok: false,
          error: "No se encontro reunion para actualizar.",
          hint: "Envia appointmentId/ghlAppointmentId desde GHL o meetingUrl/googleMeetUrl desde tl;dv/Zapier.",
        },
        { status: 404 }
      );
    }

    return NextResponse.json({ ok: true, matchedBy, updated: rows.length });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Error desconocido guardando evidencia." },
      { status: 500 }
    );
  }
}
