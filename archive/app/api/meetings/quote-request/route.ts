import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type QuoteRequestPayload = {
  externalId?: string;
  contactId?: string;
  clientSlug?: string;
  company?: string;
  companyName?: string;
  businessName?: string;
  contactName?: string;
  name?: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  phone?: string;
  jobTitle?: string;
  title?: string;
  industry?: string;
  country?: string;
  website?: string;
  companyLinkedin?: string;
  contactLinkedin?: string;
  companySize?: string;
  meetingInfo?: string;
  preparationInfo?: string;
  quoteNotes?: string;
  requestedAt?: string;
  source?: string;
  statusInterest?: string;
  statusMeeting?: string;
  meetingComment?: string;
  canalContacto?: string;
  tipoBbdd?: string;
  segmentoGeneral?: string;
  opportunityName?: string;
  opportunityStatus?: string;
  opportunityValue?: string;
  opportunityStageId?: string;
  opportunityPipelineId?: string;
  raw?: Record<string, unknown>;
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

function countryFromPhone(phone = "") {
  const compact = phone.replace(/\s+/g, "");
  if (compact.startsWith("+51")) return "Peru";
  if (compact.startsWith("+56")) return "Chile";
  return "";
}

function contactName(body: QuoteRequestPayload) {
  const full = firstText(body.contactName, body.name);
  if (full) return full;
  return [body.firstName, body.lastName].map((part) => firstText(part)).filter(Boolean).join(" ");
}

function normalizedBody(body: QuoteRequestPayload & Record<string, unknown>) {
  return {
    ...body,
    externalId: firstText(body.externalId, body["externalId"], body["contact.id"]),
    contactId: firstText(body.contactId, body["contact.id"]),
    clientSlug: firstText(body.clientSlug),
    company: firstText(body.company, body.companyName, body.businessName, body["contact.company_name"], body["business.name"]),
    contactName: firstText(body.contactName, body.name, body["contact.name"]),
    firstName: firstText(body.firstName, body["contact.first_name"]),
    lastName: firstText(body.lastName, body["contact.last_name"]),
    email: firstText(body.email, body["contact.email"], body["business.email"]),
    phone: firstText(body.phone, body["contact.phone"], body["business.phone"]),
    jobTitle: firstText(body.jobTitle, body.title, body["contact.cargo"]),
    industry: firstText(body.industry, body["contact.industria"]),
    country: firstText(body.country, body["contact.country"], body["business.country"]),
    website: firstText(body.website, body["contact.website"], body["business.website"]),
    companyLinkedin: firstText(body.companyLinkedin, body["contact.linkedin_empresa"]),
    contactLinkedin: firstText(body.contactLinkedin, body["contact.linkedin_personal"]),
    companySize: firstText(body.companySize, body["contact.tamao_empresa"], body["contact.tamano_empresa"]),
    meetingInfo: firstText(body.meetingInfo, body.preparationInfo, body.quoteNotes, body["contact.informacin_de_preparacin_para_la_reunin"]),
    statusInterest: firstText(body.statusInterest, body["contact.status_inters"]),
    statusMeeting: firstText(body.statusMeeting, body["contact.status_reunin"]),
    meetingComment: firstText(body.meetingComment, body["contact.comentario_reunin"]),
    canalContacto: firstText(body.canalContacto, body["contact.canal_de_contacto"]),
    tipoBbdd: firstText(body.tipoBbdd, body["contact.tipo_bbdd"]),
    segmentoGeneral: firstText(body.segmentoGeneral, body["contact.segmento_general"]),
    opportunityName: firstText(body.opportunityName, body["opportunity.name"]),
    opportunityStatus: firstText(body.opportunityStatus, body["opportunity.status"]),
    opportunityValue: firstText(body.opportunityValue, body["opportunity.monetary_value"]),
    opportunityStageId: firstText(body.opportunityStageId, body["opportunity.pipeline_stage_id"]),
    opportunityPipelineId: firstText(body.opportunityPipelineId, body["opportunity.pipeline_id"]),
  };
}

function quoteId(body: QuoteRequestPayload) {
  const base = firstText(body.externalId, body.contactId, body.email, body.phone, body.company, body.companyName);
  return `quote-${base.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || Date.now()}`;
}

function buildMeetingPayload(body: QuoteRequestPayload) {
  const normalized = normalizedBody(body);
  const phone = firstText(normalized.phone);
  const requestedAt = firstText(body.requestedAt) || new Date().toISOString();
  const company = firstText(normalized.company);
  const contact = contactName(normalized);
  const prep = firstText(normalized.meetingInfo, normalized.meetingComment);
  const country = firstText(normalized.country) || countryFromPhone(phone);
  const raw = {
    ...body.raw,
    source: firstText(body.source) || "quote-request-webhook",
    tipo_gestion_gbs: "Solo cotizacion",
    website: firstText(normalized.website),
    companyLinkedin: firstText(normalized.companyLinkedin),
    contactLinkedin: firstText(normalized.contactLinkedin),
    companySize: firstText(normalized.companySize),
    statusInterest: firstText(normalized.statusInterest),
    statusMeeting: firstText(normalized.statusMeeting),
    meetingComment: firstText(normalized.meetingComment),
    canalContacto: firstText(normalized.canalContacto),
    tipoBbdd: firstText(normalized.tipoBbdd),
    segmentoGeneral: firstText(normalized.segmentoGeneral),
    opportunity: {
      name: firstText(normalized.opportunityName),
      status: firstText(normalized.opportunityStatus),
      value: firstText(normalized.opportunityValue),
      stageId: firstText(normalized.opportunityStageId),
      pipelineId: firstText(normalized.opportunityPipelineId),
    },
  };

  return Object.fromEntries(
    Object.entries({
      ghl_appointment_id: quoteId(normalized),
      cliente_slug: firstText(normalized.clientSlug) || "gbs",
      ghl_contact_id: firstText(normalized.contactId) || undefined,
      empresa: company || undefined,
      contacto: contact || undefined,
      email: firstText(normalized.email) || undefined,
      telefono: phone || undefined,
      cargo: firstText(normalized.jobTitle) || undefined,
      industria: firstText(normalized.industry) || undefined,
      pais: country || undefined,
      fecha_agendada: requestedAt,
      fecha_reunion: requestedAt,
      starts_at: requestedAt,
      estado_reunion: "solicita_cotizacion",
      estado_validacion: "pendiente_validacion",
      es_valida: undefined,
      observacion: prep || "Solicitud directa de cotizacion. Para GBS puede contar como oportunidad equivalente a reunion si el cliente la valida.",
      notas: "Solo cotizacion",
      direccion_reunion: "",
      raw_data: raw,
      synced_at: new Date().toISOString(),
    }).filter(([, value]) => value !== undefined)
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

async function findExisting(body: QuoteRequestPayload, generatedId: string) {
  const byId = await supabaseFetch(`/reuniones?select=id,ghl_appointment_id&ghl_appointment_id=eq.${encodeURIComponent(generatedId)}&limit=1`);
  if (Array.isArray(byId) && byId.length) return byId[0] as { id: string | number };

  const contactId = firstText(body.contactId);
  if (contactId) {
    const byContact = await supabaseFetch(
      `/reuniones?select=id,ghl_appointment_id&cliente_slug=eq.${encodeURIComponent(firstText(body.clientSlug) || "gbs")}&ghl_contact_id=eq.${encodeURIComponent(contactId)}&estado_reunion=eq.solicita_cotizacion&limit=1`
    );
    if (Array.isArray(byContact) && byContact.length) return byContact[0] as { id: string | number };
  }

  return null;
}

function assertWebhookSecret(request: Request) {
  const expected = process.env.GHL_WEBHOOK_SECRET || process.env.WEBHOOK_SECRET;
  if (!expected) return;
  const received = request.headers.get("x-webhook-secret") || request.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (received !== expected) {
    throw new Error("Webhook no autorizado.");
  }
}

export async function POST(request: Request) {
  try {
    assertWebhookSecret(request);
    const body = (await request.json()) as QuoteRequestPayload;
    const payload = buildMeetingPayload(body);

    if (!payload.empresa || !payload.contacto) {
      return NextResponse.json(
        { ok: false, error: "Faltan empresa/contacto para crear la solicitud de cotizacion." },
        { status: 400 }
      );
    }

    const existing = await findExisting(body, String(payload.ghl_appointment_id));
    const rows = existing
      ? await supabaseFetch(`/reuniones?id=eq.${existing.id}`, {
          method: "PATCH",
          headers: { Prefer: "return=representation" },
          body: JSON.stringify(payload),
        })
      : await supabaseFetch("/reuniones", {
          method: "POST",
          headers: { Prefer: "return=representation" },
          body: JSON.stringify(payload),
        });

    return NextResponse.json({
      ok: true,
      action: existing ? "updated" : "created",
      type: "Solo cotizacion",
      meetingId: Array.isArray(rows) ? rows[0]?.id : undefined,
      externalId: payload.ghl_appointment_id,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Error desconocido guardando cotizacion.";
    return NextResponse.json({ ok: false, error: message }, { status: message.includes("autorizado") ? 401 : 500 });
  }
}
