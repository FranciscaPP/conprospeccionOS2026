import type {
  BANTCriteria,
  ClientDecision,
  ClientValidation,
  CommercialStatus,
  CPValidation,
  FinalValidation,
  Meeting,
  MeetingStatus,
} from "@/lib/types";
import { clientSlugFromName } from "@/lib/access-control";

export const MEETINGS_START_DATE = "2026-05-01";

const NO_DATA = "Sin dato";

export type SupabaseMeetingRow = {
  id?: number | string | null;
  ghl_appointment_id?: string | null;
  cliente_slug?: string | null;
  ghl_contact_id?: string | null;
  sdr_slug?: string | null;
  ghl_owner_user_id?: string | null;
  empresa?: string | null;
  contacto?: string | null;
  email?: string | null;
  telefono?: string | null;
  cargo?: string | null;
  industria?: string | null;
  pais?: string | null;
  fecha_agendada?: string | null;
  fecha_reunion?: string | null;
  hora_reunion?: string | null;
  starts_at?: string | null;
  estado_reunion?: string | null;
  estado_validacion?: string | null;
  es_valida?: boolean | null;
  motivo_no_valida?: string | null;
  motivo_rechazo?: string | null;
  observacion?: string | null;
  direccion_reunion?: string | null;
  notas?: string | null;
  comercial_estado?: string | null;
  comercial_proximo_paso?: string | null;
  raw_data?: Record<string, unknown> | null;
  synced_at?: string | null;
};

export type ClientRow = {
  slug?: string | null;
  nombre?: string | null;
  pais_prospeccion?: string | null;
};

export type SdrRow = {
  slug?: string | null;
  nombre?: string | null;
};

export type MeetingsPayload = {
  meetings: Meeting[];
  meta: {
    source: string;
    startDate: string;
    endDate: string;
    rowCount: number;
    rawRowCount: number;
    excludedInactiveCount: number;
    excludedTestCount: number;
    excludedIncompleteCount: number;
    dedupedCount: number;
    missing: Record<string, number>;
    syncHint: string;
  };
};

export function todayIsoDate(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

export function buildSupabaseMeetingSelect() {
  return [
    "id",
    "ghl_appointment_id",
    "cliente_slug",
    "ghl_contact_id",
    "sdr_slug",
    "ghl_owner_user_id",
    "empresa",
    "contacto",
    "email",
    "telefono",
    "cargo",
    "industria",
    "pais",
    "fecha_agendada",
    "fecha_reunion",
    "hora_reunion",
    "starts_at",
    "estado_reunion",
    "estado_validacion",
    "es_valida",
    "motivo_no_valida",
    "motivo_rechazo",
    "observacion",
    "direccion_reunion",
    "notas",
    "comercial_estado",
    "comercial_proximo_paso",
    "raw_data",
    "synced_at",
  ].join(",");
}

function clean(value: unknown) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function hasTestMarker(row: SupabaseMeetingRow) {
  return [
    row.empresa,
    row.contacto,
    row.email,
    row.telefono,
    row.cargo,
    row.industria,
    row.pais,
    row.estado_reunion,
    row.observacion,
    row.notas,
    JSON.stringify(row.raw_data ?? {}),
  ]
    .map(clean)
    .join(" ")
    .toLowerCase()
    .includes("test");
}

function hasRequiredMeetingData(row: SupabaseMeetingRow) {
  return Boolean(clean(row.empresa) && clean(row.contacto) && latestScheduledTimestamp(row));
}

function parseComparableDate(value: unknown) {
  const raw = clean(value);
  if (!raw) return 0;
  const normalized = raw.includes("T") ? raw : `${raw.slice(0, 10)}T00:00:00+00:00`;
  const timestamp = Date.parse(normalized);
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function latestScheduledTimestamp(row: SupabaseMeetingRow) {
  return (
    parseComparableDate(row.starts_at) ||
    parseComparableDate(row.fecha_reunion) ||
    parseComparableDate(row.fecha_agendada)
  );
}

function normalizeDedupeKey(value: unknown) {
  return clean(value).toLowerCase();
}

function removeTestAndDuplicateRows(rows: SupabaseMeetingRow[]) {
  const activeRows = rows.filter((row) => clientSlugFromName(normalizeDedupeKey(row.cliente_slug)));
  const withoutTest = activeRows.filter((row) => !hasTestMarker(row));
  const completeRows = withoutTest.filter(hasRequiredMeetingData);
  const seenCompanies = new Set<string>();
  const seenEmails = new Set<string>();
  const kept: SupabaseMeetingRow[] = [];
  let dedupedCount = 0;

  [...completeRows]
    .sort((a, b) => latestScheduledTimestamp(b) - latestScheduledTimestamp(a))
    .forEach((row) => {
      const company = normalizeDedupeKey(row.empresa);
      const email = normalizeDedupeKey(row.email);
      const duplicate = (company && seenCompanies.has(company)) || (email && seenEmails.has(email));

      if (duplicate) {
        dedupedCount += 1;
        return;
      }

      kept.push(row);
      if (company) seenCompanies.add(company);
      if (email) seenEmails.add(email);
    });

  return {
    rows: kept.sort((a, b) => latestScheduledTimestamp(a) - latestScheduledTimestamp(b)),
    excludedInactiveCount: rows.length - activeRows.length,
    excludedTestCount: activeRows.length - withoutTest.length,
    excludedIncompleteCount: withoutTest.length - completeRows.length,
    dedupedCount,
  };
}

function valueOrNoData(value: unknown) {
  return clean(value) || NO_DATA;
}

function titleFromSlug(slug: string) {
  return slug
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function normalizeCountry(country?: string | null) {
  const value = clean(country).toUpperCase();
  const map: Record<string, string> = {
    CL: "Chile",
    CHILE: "Chile",
    PE: "Peru",
    PERU: "Peru",
    MX: "Mexico",
    MEXICO: "Mexico",
    AR: "Argentina",
    ARGENTINA: "Argentina",
  };
  return map[value] || clean(country);
}

function splitContact(contact: string) {
  if (!contact || contact === NO_DATA) {
    return { firstName: NO_DATA, lastName: NO_DATA };
  }
  const parts = contact.split(/\s+/).filter(Boolean);
  return {
    firstName: parts[0] || NO_DATA,
    lastName: parts.slice(1).join(" ") || NO_DATA,
  };
}

function combineDateTime(row: SupabaseMeetingRow) {
  const startsAt = clean(row.starts_at);
  if (startsAt) return startsAt;

  const date = clean(row.fecha_reunion).slice(0, 10);
  const time = clean(row.hora_reunion) || "00:00:00";
  return date ? `${date}T${time}` : new Date(0).toISOString();
}

function mapMeetingStatus(rawStatus?: string | null): MeetingStatus {
  const status = clean(rawStatus).toLowerCase();
  if (status.includes("cancel")) return "cancelled";
  if (status.includes("no show") || status.includes("no_show") || status.includes("no asist")) return "no_show";
  if (status.includes("reagend") || status.includes("resched")) return "rescheduled";
  if (status.includes("complete") || status.includes("realizada")) return "completed";
  if (status.includes("confirm") || status.includes("agendada") || status.includes("booked")) return "scheduled";
  return "scheduled";
}

function validationFromRow(row: SupabaseMeetingRow): {
  cpValidation: CPValidation;
  clientValidation: ClientValidation;
  finalValidation: FinalValidation;
  clientDecision: ClientDecision;
  commercialStatus: CommercialStatus;
  cpBANT: BANTCriteria[];
} {
  const meetingStatus = mapMeetingStatus(row.estado_reunion);
  const validationStatus = clean(row.estado_validacion).toLowerCase();

  if (meetingStatus === "rescheduled" || validationStatus === "reagendar" || validationStatus === "reagendada") {
    return {
      cpValidation: "rescheduled",
      clientValidation: "rescheduled",
      finalValidation: "rescheduled",
      clientDecision: "pending",
      commercialStatus: "next_step_scheduled",
      cpBANT: [],
    };
  }

  if (meetingStatus === "no_show" || meetingStatus === "cancelled") {
    return {
      cpValidation: "not_completed",
      clientValidation: "not_completed",
      finalValidation: "final_not_valid",
      clientDecision: "rejected",
      commercialStatus: "not_commercially_qualified",
      cpBANT: [],
    };
  }

  if (row.es_valida === true || validationStatus === "valida" || validationStatus === "reunion_valida") {
    return {
      cpValidation: "valid_cp",
      clientValidation: "valid_client",
      finalValidation: "final_valid",
      clientDecision: "accepted",
      commercialStatus: "pending_followup",
      cpBANT: [],
    };
  }

  if (row.es_valida === false || validationStatus === "no_valida" || validationStatus === "reunion_no_valida") {
    return {
      cpValidation: "not_valid_cp",
      clientValidation: "not_valid_client",
      finalValidation: "final_not_valid",
      clientDecision: "rejected",
      commercialStatus: "not_commercially_qualified",
      cpBANT: [],
    };
  }

  if (validationStatus.includes("revision")) {
    return {
      cpValidation: "requires_review",
      clientValidation: "requires_review",
      finalValidation: "in_dispute",
      clientDecision: "review_requested",
      commercialStatus: "pending_followup",
      cpBANT: [],
    };
  }

  return {
    cpValidation: "waiting_validation",
    clientValidation: "waiting_client_validation",
    finalValidation: "pending",
    clientDecision: "pending",
    commercialStatus: "pending_followup",
    cpBANT: [],
  };
}

function firstUrl(...values: Array<string | null | undefined>) {
  for (const value of values) {
    const match = clean(value).match(/https?:\/\/[^\s)]+/i);
    if (match) return match[0];
  }
  return undefined;
}

function comments(row: SupabaseMeetingRow) {
  return [row.notas, row.observacion, row.motivo_no_valida, row.motivo_rechazo]
    .map(clean)
    .filter(Boolean)
    .join("\n\n");
}

export function mapSupabaseRowsToMeetings(
  rows: SupabaseMeetingRow[],
  clients: ClientRow[],
  sdrs: SdrRow[]
): MeetingsPayload {
  const cleanedRows = removeTestAndDuplicateRows(rows);
  const clientBySlug = new Map(clients.map((client) => [clean(client.slug), client]));
  const sdrBySlug = new Map(sdrs.map((sdr) => [clean(sdr.slug), sdr]));
  const missing: Record<string, number> = {
    company: 0,
    contact: 0,
    firstName: 0,
    lastName: 0,
    jobTitle: 0,
    country: 0,
    sdr: 0,
    meetingUrl: 0,
    comments: 0,
  };

  const meetings = cleanedRows.rows.map((row) => {
    const clientSlug = clean(row.cliente_slug);
    const client = clientBySlug.get(clientSlug);
    const clientName = clean(client?.nombre) || titleFromSlug(clientSlug) || NO_DATA;
    const sdrSlug = clean(row.sdr_slug);
    const sdrName = clean(sdrBySlug.get(sdrSlug)?.nombre) || (sdrSlug ? titleFromSlug(sdrSlug) : NO_DATA);
    const contact = valueOrNoData(row.contacto);
    const names = splitContact(contact);
    const country = normalizeCountry(row.pais) || normalizeCountry(client?.pais_prospeccion) || NO_DATA;
    const meetingUrl = firstUrl(row.direccion_reunion, row.observacion);
    const noteText = comments(row);
    const validation = validationFromRow(row);
    const meetingStatus = mapMeetingStatus(row.estado_reunion);

    if (!clean(row.empresa)) missing.company += 1;
    if (!clean(row.contacto)) missing.contact += 1;
    if (names.firstName === NO_DATA) missing.firstName += 1;
    if (names.lastName === NO_DATA) missing.lastName += 1;
    if (!clean(row.cargo)) missing.jobTitle += 1;
    if (!clean(country) || country === NO_DATA) missing.country += 1;
    if (sdrName === NO_DATA) missing.sdr += 1;
    if (!meetingUrl) missing.meetingUrl += 1;
    if (!noteText) missing.comments += 1;

    return {
      id: clean(row.ghl_appointment_id) || `SB-${row.id}`,
      client: clientName,
      sdrAssigned: sdrName,
      meetingDate: combineDateTime(row),
      company: valueOrNoData(row.empresa),
      contact,
      firstName: names.firstName,
      lastName: names.lastName,
      jobTitle: valueOrNoData(row.cargo),
      leadEmail: clean(row.email) || undefined,
      leadPhone: clean(row.telefono) || undefined,
      country,
      leadIndustry: clean(row.industria) || undefined,
      meetingUrl,
      meetingStatus,
      cpValidation: validation.cpValidation,
      cpBANT: validation.cpBANT,
      cpComment: clean(row.motivo_no_valida) || clean(row.motivo_rechazo) || clean(row.observacion) || "Sin dato",
      clientValidation: validation.clientValidation,
      clientBANT: [],
      clientComment: clean(row.motivo_no_valida) || clean(row.motivo_rechazo) || "",
      clientDecision: validation.clientDecision,
      finalValidation: validation.finalValidation,
      commercialStatus: validation.commercialStatus,
      commercialStatusLabel: clean(row.comercial_estado) || undefined,
      disputeFlag: validation.finalValidation === "in_dispute",
      pendingClientFlag: validation.clientDecision === "pending",
      meetingSummary: noteText || "Sin dato",
      preparationInfo: clean(row.observacion) || undefined,
      validityReason: clean(row.motivo_no_valida) || clean(row.motivo_rechazo) || undefined,
      prospectAttended: meetingStatus === "no_show" ? false : undefined,
      concretada: meetingStatus === "completed" ? true : undefined,
      nextStep: clean(row.comercial_proximo_paso) || (validation.clientDecision === "pending" ? "Validar reunión" : "Sin dato"),
      internalNotes: noteText || "Sin dato",
      ghlStageKey: clean(row.estado_reunion) || undefined,
    } satisfies Meeting;
  });

  const endDate = todayIsoDate();

  return {
    meetings,
    meta: {
      source: "Supabase public.reuniones sincronizada desde GoHighLevel",
      startDate: MEETINGS_START_DATE,
      endDate,
      rowCount: meetings.length,
      rawRowCount: rows.length,
      excludedInactiveCount: cleanedRows.excludedInactiveCount,
      excludedTestCount: cleanedRows.excludedTestCount,
      excludedIncompleteCount: cleanedRows.excludedIncompleteCount,
      dedupedCount: cleanedRows.dedupedCount,
      missing,
      syncHint:
        "Ejecutar sync/scripts/sync_ghl.py --entity all y luego sync/scripts/sync_meetings.py --start-date 2026-05-01 --end-date YYYY-MM-DD.",
    },
  };
}
