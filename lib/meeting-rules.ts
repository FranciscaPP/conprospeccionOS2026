import { bantLabels } from "@/lib/types";
import type {
  BANTCriteria,
  ClientDecision,
  CPValidation,
  FinalValidation,
  Meeting,
  MeetingAction,
  MeetingStatus,
} from "@/lib/types";

export const MONTHLY_GOAL_BY_CLIENT: Record<string, number> = {
  "GBS LOGISTICS": 10,
  "GBS Logistics": 10,
  "GBS": 10,
  "CLICKIE": 6,
  "Clickie": 6,
  "BAMBUTECH": 12,
  "BambuTech": 12,
};

export function titleCase(value: string) {
  return value
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function splitContactName(contact: string) {
  const parts = contact.trim().split(/\s+/).filter(Boolean);
  return {
    firstName: parts[0] || contact,
    lastName: parts.slice(1).join(" ") || "",
  };
}

function toSlug(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function toEmailSlug(value: string) {
  return toSlug(value).replace(/-/g, ".");
}

function translateDemoNextStep(value: string) {
  const translations: Record<string, string> = {
    "Send proposal by June 10": "Enviar propuesta antes del 10 de junio",
    "Waiting for client validation": "Esperar validación del cliente",
    "Schedule review call": "Agendar llamada de revisión",
    "Waiting for client feedback": "Esperar feedback del cliente",
    "New meeting June 12": "Nueva reunión el 12 de junio",
    "Contract negotiation call June 15": "Llamada de negociación de contrato el 15 de junio",
    "Send cold chain proposal": "Enviar propuesta de cadena de frío",
    "Find correct contact": "Buscar contacto correcto",
    "Contract signing June 20": "Firma de contrato el 20 de junio",
    "Waiting validation": "Esperar validación",
    "Finance meeting June 18": "Reunión con finanzas el 18 de junio",
    "Proposal review June 16": "Revisión de propuesta el 16 de junio",
    "Attempt to reschedule": "Intentar reagendar",
    "Verify decision maker": "Verificar decisor",
    "Post-mortem analysis": "Análisis de pérdida",
    "Prepare comprehensive proposal": "Preparar propuesta completa",
    "Complete meeting": "Completar reunión",
  };

  return translations[value] || value;
}

function cleanOptional(value?: string) {
  const cleaned = value?.trim();
  return cleaned && cleaned !== "Sin dato" ? cleaned : undefined;
}

export function isProspectNoShow(meeting: Meeting) {
  return meeting.prospectAttended === false || meeting.meetingStatus === "no_show";
}

export function isHeld(meeting: Meeting) {
  if (typeof meeting.concretada === "boolean") return meeting.concretada;
  return meeting.prospectAttended !== false && meeting.meetingStatus === "completed";
}

export function getBANTScore(meeting: Meeting) {
  if (typeof meeting.bantScore === "number") return meeting.bantScore;
  if (meeting.bantEvidence?.length) {
    return meeting.bantEvidence.filter((item) => item.met).length;
  }
  return meeting.cpBANT.length;
}

export function isContractuallyValid(meeting: Meeting) {
  return (
    isHeld(meeting) &&
    getBANTScore(meeting) >= 2 &&
    meeting.regionValid !== false &&
    (meeting.personAreaCorrect !== false || meeting.escalatedToCorrectArea === true)
  );
}

export function deriveCPValidation(meeting: Meeting): CPValidation {
  if (meeting.meetingStatus === "rescheduled") return "rescheduled";
  if (isProspectNoShow(meeting)) return "not_completed";
  if (meeting.evidence?.aiRecommendation === "review") return "requires_review";
  return isContractuallyValid(meeting) ? "valid_cp" : "not_valid_cp";
}

export function deriveAction(meeting: Meeting): MeetingAction {
  if (isProspectNoShow(meeting)) return "reschedule";
  if (meeting.personAreaCorrect === false && !meeting.escalatedToCorrectArea) return "escalate";
  if ((meeting.evidence?.aiConfidence ?? 1) < 0.7 || meeting.cpValidation === "requires_review") {
    return "manual_review";
  }
  return isContractuallyValid(meeting) ? "count" : "manual_review";
}

export function deriveFinalValidation(meeting: Meeting): FinalValidation {
  if (meeting.meetingStatus === "rescheduled") return "rescheduled";
  if (isProspectNoShow(meeting)) return "final_not_valid";
  if (meeting.clientDecision === "accepted" || meeting.clientValidation === "valid_client") {
    return isContractuallyValid(meeting) ? "final_valid" : "in_dispute";
  }
  if (meeting.clientDecision === "rejected" || meeting.clientValidation === "not_valid_client") {
    return meeting.cpValidation === "valid_cp" ? "in_dispute" : "final_not_valid";
  }
  if (meeting.clientDecision === "review_requested" || meeting.clientValidation === "requires_review") {
    return "in_dispute";
  }
  return "pending";
}

export function getClientDecision(meeting: Meeting): ClientDecision {
  if (meeting.clientDecision) return meeting.clientDecision;
  if (meeting.clientValidation === "valid_client") return "accepted";
  if (meeting.clientValidation === "not_valid_client") return "rejected";
  if (meeting.clientValidation === "requires_review") return "review_requested";
  return "pending";
}

export function isClientLocked(meeting: Meeting) {
  const decision = getClientDecision(meeting);
  return decision === "accepted" || decision === "rejected" || decision === "review_requested";
}

export function getSimpleClientStatus(meeting: Meeting) {
  const decision = getClientDecision(meeting);
  if (meeting.meetingStatus === "rescheduled" || meeting.finalValidation === "rescheduled") return "Reagendada";
  if (isProspectNoShow(meeting) || meeting.clientValidation === "not_completed") return "No realizada";
  if (decision === "accepted") return "Validada";
  if (decision === "rejected") return "No validada";
  if (decision === "review_requested" || meeting.finalValidation === "in_dispute") return "En revisión";
  return "Pendiente";
}

export function getValidationResultLabel(meeting: Meeting) {
  if (meeting.finalValidation === "final_valid") return "Validada";
  if (meeting.finalValidation === "final_not_valid") return "No válida";
  if (meeting.finalValidation === "in_dispute") return "En revisión";
  if (meeting.finalValidation === "rescheduled") return "Reagendada";
  if (meeting.cpValidation === "valid_cp") return "Validada";
  if (meeting.cpValidation === "not_valid_cp") return "No válida";
  return "Pendiente";
}

export function getValidationTooltip(meeting: Meeting) {
  const variables = meeting.cpBANT.map((criteria) => bantLabels[criteria]).join(", ");
  const variableText = variables || "sin variables comerciales registradas";
  const evidenceText = meeting.evidence?.recordingUrl || meeting.evidence?.transcriptUrl
    ? "Reunión grabada/transcrita para análisis."
    : "Grabación pendiente o no conectada.";
  const interestText = meeting.preparationInfo || meeting.meetingSummary || meeting.validityReason;

  return [
    `Criterios detectados: ${variableText}.`,
    `ICP: ${meeting.regionValid === false || meeting.personAreaCorrect === false ? "requiere revisión" : "compatible con el perfil acordado"}.`,
    evidenceText,
    interestText ? `Contexto: ${interestText}` : "",
  ]
    .filter(Boolean)
    .join(" ");
}

export function normalizeMeeting(meeting: Meeting): Meeting {
  const names = splitContactName(meeting.contact);
  const next: Meeting = {
    ...meeting,
    firstName: titleCase(meeting.firstName || names.firstName),
    lastName: titleCase(meeting.lastName || names.lastName),
    leadEmail: cleanOptional(meeting.leadEmail),
    leadPhone: cleanOptional(meeting.leadPhone),
    country: meeting.country || "Sin dato",
    leadIndustry: cleanOptional(meeting.leadIndustry),
    companyWebsite: cleanOptional(meeting.companyWebsite),
    contactLinkedinUrl: cleanOptional(meeting.contactLinkedinUrl),
    companyLinkedinUrl: cleanOptional(meeting.companyLinkedinUrl),
    meetingUrl: cleanOptional(meeting.meetingUrl),
    regionValid: meeting.regionValid ?? true,
    prospectAttended:
      meeting.prospectAttended ?? (meeting.meetingStatus === "no_show" ? false : true),
    clientAttended: meeting.clientAttended ?? true,
    personAreaCorrect: meeting.personAreaCorrect ?? true,
    escalatedToCorrectArea: meeting.escalatedToCorrectArea ?? false,
    concretada: meeting.concretada ?? meeting.meetingStatus === "completed",
    bantScore: meeting.bantScore ?? meeting.cpBANT.length,
    clientDecision: getClientDecision(meeting),
    preparationInfo: meeting.preparationInfo || meeting.meetingSummary,
    nextStep: translateDemoNextStep(meeting.nextStep),
    companyValidationStatus: meeting.companyValidationStatus ?? "none",
  };
  next.recommendedAction = next.recommendedAction ?? deriveAction(next);
  next.cpValidation = next.cpValidation === "waiting_validation" ? deriveCPValidation(next) : next.cpValidation;
  next.finalValidation = deriveFinalValidation(next);
  next.disputeFlag = next.finalValidation === "in_dispute";
  next.pendingClientFlag = getClientDecision(next) === "pending";
  next.ghlStageKey = mapToGHLStage(next);
  return next;
}

export function mapToGHLStage(meeting: Meeting) {
  if (meeting.meetingStatus === "scheduled") return "agendada";
  if (meeting.meetingStatus === "completed" && meeting.finalValidation === "pending") return "pendiente_validacion";
  if (meeting.meetingStatus === "completed") return "realizada";
  if (meeting.finalValidation === "final_valid") return "reunion_valida";
  if (meeting.finalValidation === "final_not_valid") return "reunion_no_valida";
  if (meeting.meetingStatus === "rescheduled") return "reagendada";
  if (meeting.meetingStatus === "no_show") return "no_show";
  return "pendiente_validacion";
}

export function updateMeetingWithRules(meeting: Meeting, updates: Partial<Meeting>) {
  return normalizeMeeting({ ...meeting, ...updates });
}

export function getDaysRemainingInMonth(date = new Date()) {
  const end = new Date(date.getFullYear(), date.getMonth() + 1, 0);
  return Math.max(0, end.getDate() - date.getDate());
}

export function getClientPriority(validated: number, pending: number, goal: number, daysRemaining: number) {
  const projected = validated + pending;
  const gap = Math.max(goal - validated, 0);
  if (gap === 0) return "Baja";
  if (goal - projected > 0 || (gap >= 4 && daysRemaining <= 10)) return "Alta";
  if (gap >= 2) return "Media";
  return "Baja";
}

export function getPriorityTone(priority: string) {
  if (priority === "Alta") return "danger";
  if (priority === "Media") return "warning";
  return "success";
}

export function isFinalValid(meeting: Meeting) {
  return meeting.finalValidation === "final_valid";
}

export function getClientSearchText(meeting: Meeting) {
  return [
    meeting.company,
    meeting.contact,
    meeting.firstName,
    meeting.lastName,
    meeting.jobTitle,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function getInternalSearchText(meeting: Meeting) {
  return [
    meeting.client,
    meeting.company,
    meeting.contact,
    meeting.firstName,
    meeting.lastName,
    meeting.jobTitle,
    meeting.sdrAssigned,
    meeting.country,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function meetingStatusToCP(status: MeetingStatus): Partial<Meeting> {
  if (status === "completed") return { prospectAttended: true, concretada: true };
  if (status === "no_show") return { prospectAttended: false, concretada: false };
  if (status === "rescheduled") return { concretada: false };
  return {};
}
