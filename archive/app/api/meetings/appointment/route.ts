import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type AppointmentPayload = Record<string, unknown> & {
  type?: string;
  id?: string;
  appointmentId?: string;
  locationId?: string;
  contactId?: string;
  startTime?: string;
  endTime?: string;
  title?: string;
  calendarId?: string;
  assignedUserId?: string;
  userId?: string;
  status?: string;
  clientSlug?: string;
  company?: string;
  companyName?: string;
  contactName?: string;
  name?: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  phone?: string;
  jobTitle?: string;
  title_contact?: string;
  industry?: string;
  country?: string;
  meetingUrl?: string;
  notes?: string;
};

const LOCATION_TO_SLUG: Record<string, string> = {
  "0GMcqNXmxVGaKoNVhIYS": "ecosmart",
  xdxoUl151dtIKFKIZt1p: "clickie",
  ZC4A2bNvo876Csmz4I9T: "just4u",
  DpvcxBw1Jfi4KUC232AT: "tiresias",
  FJ1YCwi4UVvwcBb8qlOb: "bambutech",
  u9b8KkJXhM8lqJfzxa7G: "gbs",
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
    if (typeof value === "string" && value.trim() && !["null", "undefined"].includes(value.trim().toLowerCase())) {
      return value.trim();
    }
  }
  return "";
}

function contactName(body: AppointmentPayload) {
  const full = firstText(body.contactName, body.name);
  if (full) return full;
  return [body.firstName, body.lastName].map((part) => firstText(part)).filter(Boolean).join(" ");
}

function normalizedStatus(status: string) {
  const value = status.toLowerCase();
  if (value === "booked" || value === "confirmed") return "confirmed";
  if (value === "cancelled" || value === "canceled") return "cancelled";
  if (value === "noshow" || value === "no_show") return "no_show";
  if (value === "completed") return "completed";
  return status || "confirmed";
}

function buildMeetingPayload(body: AppointmentPayload) {
  const appointmentId = firstText(body.id, body.appointmentId);
  const locationId = firstText(body.locationId);
  const clientSlug = firstText(body.clientSlug) || LOCATION_TO_SLUG[locationId] || "gbs";
  const startTime = firstText(body.startTime);
  const endTime = firstText(body.endTime);
  const meetingStatus = normalizedStatus(firstText(body.status) || "booked");
  const company = firstText(body.company, body.companyName, body.title);
  const contact = contactName(body);

  return Object.fromEntries(
    Object.entries({
      ghl_appointment_id: appointmentId,
      cliente_slug: clientSlug,
      location_id: locationId || undefined,
      ghl_contact_id: firstText(body.contactId) || undefined,
      ghl_calendar_id: firstText(body.calendarId) || undefined,
      ghl_owner_user_id: firstText(body.assignedUserId, body.userId) || undefined,
      titulo: firstText(body.title) || undefined,
      empresa: company || undefined,
      contacto: contact || undefined,
      email: firstText(body.email) || undefined,
      telefono: firstText(body.phone) || undefined,
      cargo: firstText(body.jobTitle, body.title_contact) || undefined,
      industria: firstText(body.industry) || undefined,
      pais: firstText(body.country) || undefined,
      fecha_agendada: startTime || new Date().toISOString(),
      fecha_reunion: startTime || undefined,
      starts_at: startTime || undefined,
      ends_at: endTime || undefined,
      estado_reunion: meetingStatus,
      estado_validacion: "pendiente_validacion",
      es_valida: null,
      pendiente_validacion: true,
      direccion_reunion: firstText(body.meetingUrl) || undefined,
      observacion: firstText(body.notes) || undefined,
      notas: firstText(body.notes) || undefined,
      raw_data: body,
      synced_at: new Date().toISOString(),
    }).filter(([, value]) => value !== undefined && value !== null)
  );
}

async function supabaseFetch(path: string, init: RequestInit = {}) {
  const config = getSupabaseConfig();
  const response = await fetch(`${config.restUrl}${path}`, {
    ...init,
    headers: {
      apikey: config.key,
      Authorization: `Bearer ${config.key}`,
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Supabase ${response.status}: ${text.slice(0, 400)}`);
  }

  if (response.status === 204) return null;
  return response.json();
}

function assertWebhookSecret(request: Request) {
  const expected = process.env.GHL_WEBHOOK_SECRET || process.env.WEBHOOK_SECRET;
  if (!expected) return;
  const received = request.headers.get("x-webhook-secret") || request.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (received !== expected) {
    throw new Error("Webhook no autorizado.");
  }
}

export async function GET() {
  return NextResponse.json({ status: "ok", endpoint: "appointment-webhook" });
}

export async function POST(request: Request) {
  try {
    assertWebhookSecret(request);
    const body = (await request.json()) as AppointmentPayload;
    const eventType = firstText(body.type);

    if (eventType && !["AppointmentCreate", "AppointmentUpdate", "appointment.created", "appointment.updated"].includes(eventType)) {
      return NextResponse.json({ ok: true, ignored: eventType });
    }

    const payload = buildMeetingPayload(body);
    const appointmentId = String(payload.ghl_appointment_id || "");

    if (!appointmentId) {
      return NextResponse.json({ ok: false, error: "Falta id de la cita (appointment)." }, { status: 400 });
    }

    const existing = await supabaseFetch(
      `/reuniones?select=id,ghl_appointment_id&ghl_appointment_id=eq.${encodeURIComponent(appointmentId)}&limit=1`
    );

    const rows = Array.isArray(existing) && existing.length
      ? await supabaseFetch(`/reuniones?id=eq.${existing[0].id}`, {
          method: "PATCH",
          headers: { Prefer: "return=representation" },
          body: JSON.stringify(payload),
        })
      : await supabaseFetch("/reuniones?on_conflict=ghl_appointment_id", {
          method: "POST",
          headers: { Prefer: "resolution=merge-duplicates,return=representation" },
          body: JSON.stringify(payload),
        });

    return NextResponse.json({
      ok: true,
      action: Array.isArray(existing) && existing.length ? "updated" : "created",
      appointmentId,
      clientSlug: payload.cliente_slug,
      meetingId: Array.isArray(rows) ? rows[0]?.id : undefined,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Error desconocido guardando cita.";
    return NextResponse.json({ ok: false, error: message }, { status: message.includes("autorizado") ? 401 : 500 });
  }
}
