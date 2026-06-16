import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { TextDecoder } from "node:util";

const {
  GHL_API_KEY,
  GHL_LOCATION_ID,
  GHL_CALENDAR_ID,
  GHL_USER_ID,
  GHL_START = "2026-06-01T00:00:00-04:00",
  GHL_END = "2026-06-30T23:59:59-04:00",
  GHL_OUTPUT = "docs/data/gbs-meetings.json",
} = process.env;

if (!GHL_API_KEY || !GHL_LOCATION_ID || (!GHL_CALENDAR_ID && !GHL_USER_ID)) {
  console.error(
    "Missing required env. Set GHL_API_KEY, GHL_LOCATION_ID, and GHL_CALENDAR_ID or GHL_USER_ID.",
  );
  process.exit(1);
}

const headers = {
  Authorization: `Bearer ${GHL_API_KEY}`,
  Accept: "application/json",
};

async function ghlFetch(url, version = "2021-07-28") {
  const response = await fetch(url, {
    headers: { ...headers, Version: version },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }

  const bytes = new Uint8Array(await response.arrayBuffer());
  const text = new TextDecoder("utf-8").decode(bytes);
  return JSON.parse(text);
}

function toMillis(value) {
  return new Date(value).getTime();
}

function formatDateLabel(value) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("es-CL", {
    day: "numeric",
    month: "short",
    timeZone: "America/Santiago",
  })
    .format(date)
    .replace(".", "");
}

function formatTimeLabel(value) {
  return new Intl.DateTimeFormat("es-CL", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "America/Santiago",
  }).format(new Date(value));
}

function countryFor(contact) {
  const phone = String(contact.phone || "").replace(/\s+/g, "");
  if (phone.startsWith("+51")) return "Peru";
  if (phone.startsWith("+56")) return "Chile";
  return contact.country || "Chile";
}

function customFieldValues(contact) {
  return (contact.customFields || [])
    .map((field) => String(field?.value || "").trim())
    .filter(Boolean);
}

function meetingPreparation(appointment, contact) {
  const meetingInfo = (contact.customFields || []).find((field) => field?.id === "mwCPOKdikR3VfS7Xf9bm")?.value;
  if (typeof meetingInfo === "string" && meetingInfo.trim()) return meetingInfo.trim();

  const values = customFieldValues(contact);
  const ignored = new Set([
    String(contact.website || "").trim(),
    String(contact.email || "").trim(),
    String(contact.phone || "").trim(),
  ]);
  const candidates = values.filter((value) => {
    const lower = value.toLowerCase();
    if (ignored.has(value)) return false;
    if (/^https?:\/\//i.test(value)) return false;
    if (/^\d+([.,]\d+)?$/.test(value)) return false;
    if (["whatsapp", "llamada", "reunion agendada", "reuniÃ³n agendada", "no contesta", "coordinando reuniÃ³n"].includes(lower)) return false;
    if (lower.length < 24) return false;
    return true;
  });

  return candidates[0] || appointment.description || appointment.notes || "";
}

function initialsFor(companyName = "") {
  const clean = companyName.replace(/[^a-zA-ZÁÉÍÓÚÜÑáéíóúüñ0-9 ]/g, " ").trim();
  const words = clean.split(/\s+/).filter(Boolean);
  return (words[0]?.[0] || "?").toUpperCase() + (words[1]?.[0] || "").toUpperCase();
}

function statusFor(appointment) {
  if (appointment.appointmentStatus === "cancelled") {
    return { status: "Reagendada", filter: "reagendada", cpAgenda: "Reagenda pendiente" };
  }

  return { status: "Pendiente validación", filter: "pendiente", cpAgenda: "Agenda sin cambios" };
}

function inferCpValidation(appointment, contact) {
  if (appointment.appointmentStatus === "cancelled") return "Reagendar reunión";
  const tags = (contact.tags || []).map((tag) => tag.toLowerCase());
  if (tags.some((tag) => tag.includes("no califica"))) return "Reunión no válida";
  return "Reunión válida";
}

function appointmentStatusLabel(status = "") {
  if (status === "confirmed") return "Cita confirmada";
  if (status === "cancelled") return "Cita cancelada";
  return "Estado por revisar";
}

function evidenceSummaryFor(status, tags) {
  if (status.filter === "reagendada") {
    return "La cita figura cancelada en GHL. No hay evidencia de reunión efectiva; corresponde confirmar motivo, reagendar o excluir de meta.";
  }

  const hasNoQualify = tags.some((tag) => tag.toLowerCase().includes("no califica"));
  if (hasNoQualify) {
    return "La preparación indica que el lead no califica. Si la grabación confirma reunión efectiva, revisar ICP y variables BANT antes de contarla para meta.";
  }

  return "Resumen esperado de evidencia: confirmar reunión efectiva, ICP acordado, al menos 2 variables BANT detectadas y próximos pasos comerciales.";
}

async function readContact(contactId) {
  if (!contactId) return {};
  const data = await ghlFetch(`https://services.leadconnectorhq.com/contacts/${contactId}`);
  return data.contact || {};
}

const params = new URLSearchParams({
  locationId: GHL_LOCATION_ID,
  startTime: String(toMillis(GHL_START)),
  endTime: String(toMillis(GHL_END)),
});

if (GHL_CALENDAR_ID) params.set("calendarId", GHL_CALENDAR_ID);
if (GHL_USER_ID) params.set("userId", GHL_USER_ID);

const appointmentsPayload = await ghlFetch(
  `https://services.leadconnectorhq.com/calendars/events?${params}`,
  "2021-04-15",
);

const appointments = appointmentsPayload.events || [];
const meetings = [];

for (const appointment of appointments) {
  const contact = await readContact(appointment.contactId);
  const company = contact.companyName || appointment.title?.replace(" - GBS Logistics", "").trim() || "Sin empresa";
  const status = statusFor(appointment);
  const tags = contact.tags || [];
  const prep = meetingPreparation(appointment, contact);

  meetings.push({
    id: appointment.id,
    source: "ghl",
    calendarId: appointment.calendarId,
    contactId: appointment.contactId,
    assignedUserId: appointment.assignedUserId,
    date: formatDateLabel(appointment.startTime),
    dateIso: appointment.startTime.slice(0, 10),
    time: formatTimeLabel(appointment.startTime),
    startTime: appointment.startTime,
    endTime: appointment.endTime,
    company,
    initials: initialsFor(company),
    color: status.filter === "reagendada" ? "#76786f" : "#0e9f6e",
    person: contact.name || contact.firstName || "Contacto sin nombre",
    role: contact.title || "Contacto comercial",
    status: status.status,
    filter: status.filter,
    prep: prep || "",
    evaluation:
      status.filter === "reagendada"
        ? "La cita aparece cancelada/reagendada en GHL; revisar si corresponde mantenerla fuera de meta o reagendar."
        : "Cita confirmada en GHL. Requiere validación con evidencia, ICP y variables BANT.",
    chips: [
      appointmentStatusLabel(appointment.appointmentStatus),
      tags.includes("reunión agendada") ? "Reunión agendada" : "Agenda por revisar",
      tags.includes("no califica") ? "No califica ICP" : "ICP por validar",
    ],
    transcriptSummary:
      "Pendiente de transcripción. La IA debe completar este resumen cuando exista grabación o notas de reunión.",
    evidenceSummary: evidenceSummaryFor(status, tags),
    commercialStatus: tags.includes("no califica") ? "Sin respuesta" : "Reunión agendada",
    nextStep:
      status.filter === "reagendada"
        ? "Confirmar motivo de cancelación/reagenda y definir nueva fecha."
        : "Validar evidencia de reunión y completar evaluación comercial.",
    meetingUrl: appointment.address || "",
    email: contact.email || "",
    phone: contact.phone || "",
    country: countryFor(contact),
    contactLinkedin: contact.linkedIn || "",
    industry: contact.businessType || "",
    companySize: "",
    website: contact.website || "",
    companyLinkedin: "",
    cpValidation: inferCpValidation(appointment, contact),
    cpAgenda: status.cpAgenda,
    tags,
    raw: { appointment, contact },
  });
}

const output = {
  generatedAt: new Date().toISOString(),
  source: "ghl",
  locationId: GHL_LOCATION_ID,
  calendarId: GHL_CALENDAR_ID || null,
  userId: GHL_USER_ID || null,
  range: { start: GHL_START, end: GHL_END },
  meetings,
};

const outputPath = path.resolve(GHL_OUTPUT);
await mkdir(path.dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");

console.log(`Wrote ${meetings.length} meetings to ${outputPath}`);
