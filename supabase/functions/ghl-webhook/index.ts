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

// GHL location_id → datos del cliente en Supabase
const LOCATION_MAP: Record<string, { slug: string; cliente_id: number }> = {
  "0GMcqNXmxVGaKoNVhIYS": { slug: "ecosmart",      cliente_id: 1 },
  "xdxoUl151dtIKFKIZt1p": { slug: "clickie",       cliente_id: 2 },
  "ZC4A2bNvo876Csmz4I9T": { slug: "just4u",        cliente_id: 3 },
  "DpvcxBw1Jfi4KUC232AT": { slug: "tiresias",      cliente_id: 4 },
  "FJ1YCwi4UVvwcBb8qlOb": { slug: "bambutech",     cliente_id: 5 },
  "u9b8KkJXhM8lqJfzxa7G": { slug: "gbs", cliente_id: 6 },
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

async function getContactInfo(locationId: string, contactId: string, token: string) {
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

  const type = (payload.type as string) ?? "";

  // Solo procesar eventos de citas
  if (!["AppointmentCreate", "AppointmentUpdate"].includes(type)) {
    return new Response(JSON.stringify({ ignored: type }), { status: 200 });
  }

  const locationId    = (payload.locationId as string) ?? "";
  const appointmentId = (payload.id as string) ?? (payload.appointmentId as string) ?? "";
  const contactId     = (payload.contactId as string) ?? "";
  const startTime     = (payload.startTime as string) ?? "";
  const endTime       = (payload.endTime as string) ?? "";
  const title         = (payload.title as string) ?? "";
  const calendarId    = (payload.calendarId as string) ?? "";
  const assignedUserId = (payload.assignedUserId as string) ?? (payload.userId as string) ?? "";
  const status        = (payload.status as string) ?? "booked";

  const cliente = LOCATION_MAP[locationId];
  if (!cliente) {
    return new Response(JSON.stringify({ ignored: `unknown location ${locationId}` }), { status: 200 });
  }

  // Filtrar citas de dominios internos (clickie.io)
  if (cliente.slug === "clickie") {
    const emailRaw = (payload.email as string) ?? "";
    if (emailRaw.toLowerCase().endsWith("@clickie.io")) {
      return new Response(JSON.stringify({ ignored: "internal clickie domain" }), { status: 200 });
    }
  }

  // Resolver SDR
  const sdrInfo = GHL_USER_TO_SDR[assignedUserId] ?? null;

  // Obtener datos del contacto desde GHL
  const token   = await getClientToken(cliente.slug);
  const contact = contactId ? await getContactInfo(locationId, contactId, token) : null;

  // Filtrar "llevenes" (Clickie)
  if (cliente.slug === "clickie") {
    const cname = ((contact?.name ?? contact?.firstName ?? "") as string).toLowerCase();
    if (cname.includes("llevenes")) {
      return new Response(JSON.stringify({ ignored: "llevenes filter" }), { status: 200 });
    }
  }

  const row: Record<string, unknown> = {
    ghl_appointment_id: appointmentId,
    cliente_slug:       cliente.slug,
    cliente_id:         cliente.cliente_id,
    location_id:        locationId,
    ghl_contact_id:     contactId || null,
    ghl_calendar_id:    calendarId || null,
    appointment_at:     startTime || null,
    ends_at:            endTime || null,
    titulo:             title || null,
    estado_reunion:     status === "booked" ? "reunion_agendada" : status,
    estado_validacion:  "pendiente_validacion",
    ghl_owner_user_id:  assignedUserId || null,
  };

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
    SB("reuniones?on_conflict=ghl_appointment_id"),
    {
      method: "POST",
      headers: SB_HEADERS,
      body: JSON.stringify(row),
    }
  );

  if (!resp.ok) {
    const err = await resp.text();
    console.error("Supabase upsert error:", err);
    return new Response(JSON.stringify({ error: err }), { status: 500 });
  }

  console.log(`[ghl-webhook] ${type} | ${cliente.slug} | ${title} | sdr=${sdrInfo?.sdr_slug ?? "unknown"}`);
  return new Response(JSON.stringify({ ok: true, cliente: cliente.slug, sdr: sdrInfo?.sdr_slug }), { status: 200 });
});
