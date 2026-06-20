// GHL Webhook → Supabase: sincroniza reuniones al instante cuando un SDR agenda en GHL
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const SB = (path: string) => `${SUPABASE_URL}/rest/v1/${path}`;
const SB_HEADERS = {
  apikey: SUPABASE_SERVICE_KEY,
  Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
  "Content-Type": "application/json",
  Prefer: "resolution=merge-duplicates,return=minimal",
};
const ACTIVE_WEBHOOK_CLIENTS = new Set(["clickie", "gbs", "bambutech"]);

// GHL location_id → datos del cliente en Supabase
const LOCATION_MAP: Record<string, { slug: string; cliente_id: number }> = {
  "0GMcqNXmxVGaKoNVhIYS": { slug: "ecosmart",      cliente_id: 1 },
  "xdxoUl151dtIKFKIZt1p": { slug: "clickie",       cliente_id: 2 },
  "ZC4A2bNvo876Csmz4I9T": { slug: "just4u",        cliente_id: 3 },
  "DpvcxBw1Jfi4KUC232AT": { slug: "tiresias",      cliente_id: 4 },
  "FJ1YCwi4UVvwcBb8qlOb": { slug: "bambutech",     cliente_id: 5 },
  "u9b8KkJXhM8lqJfzxa7G": { slug: "gbs", cliente_id: 7 },
};

// GHL userId → SDR en Supabase
const GHL_USER_TO_SDR: Record<string, { sdr_slug: string; sdr_id: number }> = {
  "7Dlz7PxcplLMDTLOaUcA": { sdr_slug: "eugenia_maranon",   sdr_id: 1  },
  "GhfpP0OwrmsXbHWwe1fS": { sdr_slug: "florencia_navarro", sdr_id: 2  },
  "INzQmMq7Gog0sTaT6uqS": { sdr_slug: "mariana_figueroa",  sdr_id: 5  },
  "UXSdUpEiInF8biAwCHS7": { sdr_slug: "zoe_olmedo",        sdr_id: 10 },
  "iuxCYXNnVTgNwRHmzNbS": { sdr_slug: "florencia_ravizza", sdr_id: 3  },
  "MvSt2wrpSqO8Qq7vSAdY": { sdr_slug: "julia_martin",      sdr_id: 4  },
  "22igpq17vXRIbAQG31Sx": { sdr_slug: "sandra",            sdr_id: 8  },
  "Ezoe5QSTzlreWww5MtRg": { sdr_slug: "mariela_tello",     sdr_id: 6  },
  "KvL91aKurBRAjMmnTpG8": { sdr_slug: "mariana_figueroa",  sdr_id: 5  },
  "dovg9RCZxtMQYzsWiDq6": { sdr_slug: "sandra",            sdr_id: 8  },
  "Qc97tMOrpAlqCs6paSXe": { sdr_slug: "yanina",            sdr_id: 9  },
  "CGSR1tJxUrENueEOx6vK": { sdr_slug: "zoe_olmedo",        sdr_id: 10 },
  "XPps05IhyCDj2bF93xxy": { sdr_slug: "julia_martin",      sdr_id: 4  },
  "W6j96YRKHu3zwO2GcuhB": { sdr_slug: "yanina",            sdr_id: 9  },
  "jBEKf5z5KdqjdyZlyW04": { sdr_slug: "mariela_tello",     sdr_id: 6  },
  "AdJolwIozb7J3MVWbVcl": { sdr_slug: "florencia_navarro", sdr_id: 2  },
  "utMSaAEzKGKZ28hims76": { sdr_slug: "eugenia_maranon",   sdr_id: 1  },
  "rTuQbq9oiZ5EFrTzzbcQ": { sdr_slug: "florencia_ravizza", sdr_id: 3  },
  "C1suTbyBg4JYYeUkkPe1": { sdr_slug: "luciana_acuna",     sdr_id: 12 },
};

async function getContactInfo(contactId: string, token: string) {
  try {
    const r = await fetch(
      `https://services.leadconnectorhq.com/contacts/${contactId}`,
      { headers: { Authorization: `Bearer ${token}`, Version: "2021-07-28" } }
    );
    if (!r.ok) return null;
    const d = await r.json();
    return d.contact ?? d;
  } catch {
    return null;
  }
}

async function getRows(path: string): Promise<Record<string, unknown>[]> {
  const response = await fetch(SB(path), { headers: SB_HEADERS });
  if (!response.ok) return [];
  const data = await response.json();
  return Array.isArray(data) ? data : [];
}

async function resolveSdr(clienteSlug: string, ownerUserId: string) {
  if (!ownerUserId) return null;

  const mappings = await getRows(
    `sdr_cliente?select=sdr_slug&cliente_slug=eq.${encodeURIComponent(clienteSlug)}` +
    `&ghl_user_id=eq.${encodeURIComponent(ownerUserId)}&activo=eq.true&limit=1`
  );
  const sdrSlug = String(mappings[0]?.sdr_slug ?? "");
  if (sdrSlug) {
    const sdrs = await getRows(
      `sdrs?select=id,slug&slug=eq.${encodeURIComponent(sdrSlug)}&limit=1`
    );
    if (sdrs[0]) {
      return { sdr_slug: String(sdrs[0].slug), sdr_id: Number(sdrs[0].id) };
    }
  }
  return GHL_USER_TO_SDR[ownerUserId] ?? null;
}

function stringValue(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text) return text;
  }
  return "";
}

function normalizedMeetingStatus(status: string): string {
  const normalized = status.toLowerCase();
  if (["booked", "confirmed", "new"].includes(normalized)) return "reunion_agendada";
  if (["showed", "completed"].includes(normalized)) return "realizada";
  if (["noshow", "no_show", "no-show"].includes(normalized)) return "no_show";
  if (["cancelled", "canceled"].includes(normalized)) return "cancelada";
  return normalized || "reunion_agendada";
}

async function getClientToken(slug: string): Promise<string> {
  const tokens: Record<string, string> = {
    ecosmart: Deno.env.get("GHL_TOKEN_ECOSMART") ?? "",
    clickie: Deno.env.get("GHL_TOKEN_CLICKIE") ?? "",
    just4u: Deno.env.get("GHL_TOKEN_JUST4U") ?? "",
    tiresias: Deno.env.get("GHL_TOKEN_TIRESIAS") ?? "",
    bambutech: Deno.env.get("GHL_TOKEN_BAMBUTECH") ?? "",
    gbs: Deno.env.get("GHL_TOKEN_GBS_LOGISTICS") ?? "",
  };
  return tokens[slug] ?? "";
}

function normalizedFieldToken(value: unknown): string {
  return String(value ?? "").toLowerCase().replace(/[^a-z0-9áéíóúüñ]/g, "");
}

function customFieldValue(contact: Record<string, unknown>, aliases: string[]): string | null {
  const targets = new Set(aliases.map(normalizedFieldToken));
  const fields = Array.isArray(contact.customFields) ? contact.customFields as Record<string, unknown>[] : [];
  for (const field of fields) {
    const tokens = ["name", "fieldName", "fieldKey", "key"]
      .map((key) => normalizedFieldToken(field[key]));
    if (tokens.some((token) => targets.has(token))) {
      const value = String(field.value ?? "").trim();
      if (value) return value;
    }
  }
  return null;
}

serve(async (req) => {
  // GHL envía GET para verificar el webhook — responder 200 siempre
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

  const appointment = (
    payload.appointment && typeof payload.appointment === "object"
      ? payload.appointment
      : payload
  ) as Record<string, unknown>;
  const type = stringValue(payload.type, appointment.type);

  // Solo procesar eventos de citas
  if (!["AppointmentCreate", "AppointmentUpdate"].includes(type)) {
    return new Response(JSON.stringify({ ignored: type }), { status: 200 });
  }

  const locationId = stringValue(payload.locationId, appointment.locationId);
  const appointmentId = stringValue(
    appointment.id, appointment.appointmentId, payload.appointmentId, payload.id
  );
  const contactId = stringValue(appointment.contactId, payload.contactId);
  const startTime = stringValue(
    appointment.startTime, appointment.start, payload.startTime, payload.start
  );
  const endTime = stringValue(
    appointment.endTime, appointment.end, payload.endTime, payload.end
  );
  const title = stringValue(appointment.title, payload.title);
  const calendarId = stringValue(appointment.calendarId, payload.calendarId);
  const assignedUserId = stringValue(
    appointment.assignedUserId, appointment.userId,
    payload.assignedUserId, payload.userId
  );
  const status = stringValue(
    appointment.appointmentStatus, appointment.status,
    payload.appointmentStatus, payload.status, "booked"
  );

  if (!appointmentId || !startTime) {
    return new Response(
      JSON.stringify({ error: "appointmentId and startTime are required" }),
      { status: 400 }
    );
  }

  const cliente = LOCATION_MAP[locationId];
  if (!cliente) {
    return new Response(JSON.stringify({ ignored: `unknown location ${locationId}` }), { status: 200 });
  }
  if (!ACTIVE_WEBHOOK_CLIENTS.has(cliente.slug)) {
    return new Response(JSON.stringify({ ignored: `inactive client ${cliente.slug}` }), { status: 200 });
  }

  // Filtrar citas de dominios internos (clickie.io)
  if (cliente.slug === "clickie") {
    const emailRaw = stringValue(payload.email, appointment.email);
    if (emailRaw.toLowerCase().endsWith("@clickie.io")) {
      return new Response(JSON.stringify({ ignored: "internal clickie domain" }), { status: 200 });
    }
  }

  // Obtener datos del contacto desde GHL
  const token   = await getClientToken(cliente.slug);
  const contact = contactId && token ? await getContactInfo(contactId, token) : null;
  const ownerUserId = stringValue(contact?.assignedTo, contact?.assignedUserId, assignedUserId);
  const sdrInfo = await resolveSdr(cliente.slug, ownerUserId);

  if (
    cliente.slug === "clickie" &&
    stringValue(contact?.email).toLowerCase().endsWith("@clickie.io")
  ) {
    return new Response(JSON.stringify({ ignored: "internal clickie domain" }), { status: 200 });
  }

  // Filtrar "llevenes" (Clickie)
  if (cliente.slug === "clickie") {
    const cname = ((contact?.name ?? contact?.firstName ?? "") as string).toLowerCase();
    if (cname.includes("llevenes")) {
      return new Response(JSON.stringify({ ignored: "llevenes filter" }), { status: 200 });
    }
  }

  const existing = await getRows(
    `reuniones?select=id,estado_validacion,excluida` +
    `&ghl_appointment_id=eq.${encodeURIComponent(appointmentId)}&limit=1`
  );
  const isNewMeeting = existing.length === 0;
  const now = new Date().toISOString();
  const meetingStatus = normalizedMeetingStatus(status);

  const row: Record<string, unknown> = {
    ghl_appointment_id: appointmentId,
    cliente_slug:       cliente.slug,
    cliente_id:         cliente.cliente_id,
    location_id:        locationId,
    ghl_contact_id:     contactId || null,
    ghl_calendar_id:    calendarId || null,
    appointment_at:     startTime,
    starts_at:          startTime,
    fecha_reunion:      startTime,
    fecha_agendada:     now,
    hora_reunion:       startTime.slice(11, 19) || null,
    ends_at:            endTime || null,
    titulo:             title || null,
    estado_reunion:     meetingStatus,
    pendiente_validacion: meetingStatus === "reunion_agendada",
    ghl_owner_user_id:  ownerUserId || null,
    synced_at:          now,
  };

  if (isNewMeeting) {
    row.estado_validacion = "pendiente_validacion";
    row.excluida = false;
  }

  if (sdrInfo) {
    row.sdr_slug = sdrInfo.sdr_slug;
    row.sdr_id   = sdrInfo.sdr_id;
  }

  if (contact) {
    row.contacto   = `${contact.firstName ?? ""} ${contact.lastName ?? ""}`.trim() || null;
    row.email      = contact.email ?? null;
    row.telefono   = contact.phone ?? null;
    row.empresa    = contact.companyName ?? null;
    row.cargo      = contact.title ?? null;
    row.industria  = contact.customFields?.find((f: Record<string,string>) => f.key === "industry")?.value ?? null;
    row.pais       = contact.country ?? null;
    row.informacion_reunion = customFieldValue(contact, [
      "informacin_de_preparacin_para_la_reunin",
      "informacion_de_preparacion_para_la_reunion",
      "información de preparación para la reunión",
      "informacion para reunion",
    ]);
    row.bant_sdr = customFieldValue(contact, [
      "validacin_sdr_bant",
      "validacion_sdr_bant",
      "validación_sdr_bant",
      "validacion sdr bant",
    ]);
  }
  row.raw_data = { appointment: payload, contact: contact ?? {} };

  // Upsert — no sobreescribir excluida=true ni el estado_validacion si ya fue validado
  const resp = await fetch(
    SB("reuniones?on_conflict=ghl_appointment_id&select=id"),
    {
      method: "POST",
      headers: {
        ...SB_HEADERS,
        Prefer: "resolution=merge-duplicates,return=representation",
      },
      body: JSON.stringify(row),
    }
  );

  if (!resp.ok) {
    const err = await resp.text();
    console.error("Supabase upsert error:", err);
    return new Response(JSON.stringify({ error: err }), { status: 500 });
  }

  const savedRows = await resp.json();
  const reunionId = Number(savedRows?.[0]?.id ?? existing[0]?.id ?? 0);
  if (reunionId) {
    if (isNewMeeting) {
      const trackingResponse = await fetch(
        SB("seguimiento_reuniones?on_conflict=reunion_id"),
        {
          method: "POST",
          headers: SB_HEADERS,
          body: JSON.stringify({
            reunion_id: reunionId,
            cliente_slug: cliente.slug,
            val_estado_cp: "espera",
            val_estado_cli: "espera",
            val_estado_final: "pendiente",
            status_reunion: meetingStatus,
            final_override: false,
            flag_meta_countable: false,
            flag_disputa: false,
            flag_cliente_pendiente: false,
            updated_at: now,
          }),
        }
      );
      if (!trackingResponse.ok) {
        console.error("Seguimiento insert error:", await trackingResponse.text());
      }
    } else {
      const trackingResponse = await fetch(
        SB(`seguimiento_reuniones?reunion_id=eq.${reunionId}`),
        {
          method: "PATCH",
          headers: SB_HEADERS,
          body: JSON.stringify({ status_reunion: meetingStatus, updated_at: now }),
        }
      );
      if (!trackingResponse.ok) {
        console.error("Seguimiento update error:", await trackingResponse.text());
      }
    }
  }

  console.log(`[ghl-webhook] ${type} | ${cliente.slug} | ${title} | sdr=${sdrInfo?.sdr_slug ?? "unknown"}`);
  return new Response(
    JSON.stringify({
      ok: true,
      cliente: cliente.slug,
      reunion_id: reunionId || null,
      sdr: sdrInfo?.sdr_slug ?? null,
    }),
    { status: 200 }
  );
});
