// Validation Types
export type CPValidation =
  | "waiting_validation"
  | "valid_cp"
  | "not_valid_cp"
  | "requires_review"
  | "rescheduled"
  | "not_completed";

export type ClientValidation =
  | "waiting_client_validation"
  | "valid_client"
  | "not_valid_client"
  | "requires_review"
  | "rescheduled"
  | "not_completed";

export type FinalValidation =
  | "pending"
  | "final_valid"
  | "final_not_valid"
  | "in_dispute"
  | "rescheduled"
  | "excluded_by_agreement";

export type CommercialStatus =
  | "pending_followup"
  | "next_step_scheduled"
  | "requested_proposal"
  | "proposal_sent"
  | "proposal_followup"
  | "negotiation"
  | "no_response"
  | "client_won"
  | "client_lost"
  | "not_commercially_qualified";

export type MeetingStatus =
  | "scheduled"
  | "completed"
  | "rescheduled"
  | "cancelled"
  | "no_show";

export type BANTCriteria = "budget" | "authority" | "need" | "timeline";

export type MeetingAction = "count" | "reschedule" | "escalate" | "manual_review";

export type ClientDecision = "pending" | "accepted" | "rejected" | "review_requested";

export type RejectionReason =
  | "wrong_role"
  | "outside_profile"
  | "prospect_no_show"
  | "no_real_interest"
  | "duplicate_meeting"
  | "existing_client_or_contact"
  | "other";

export type CompanyValidationStatus =
  | "none"
  | "previous_valid_meeting"
  | "temporarily_blocked"
  | "open_opportunity"
  | "existing_client_or_contact";

export interface BANTEvidence {
  criteria: BANTCriteria;
  met: boolean;
  quote: string;
  note: string;
}

export interface MeetingEvidence {
  aiSummary: string;
  aiRecommendation: "valid" | "review" | "not_valid";
  aiConfidence: number;
  transcriptUrl?: string;
  recordingUrl?: string;
  assistantNote?: string;
}

export interface Meeting {
  id: string;
  client: string;
  sdrAssigned: string;
  meetingDate: string;
  company: string;
  contact: string;
  firstName?: string;
  lastName?: string;
  jobTitle: string;
  country?: string;
  leadIndustry?: string;
  companyWebsite?: string;
  contactLinkedinUrl?: string;
  companyLinkedinUrl?: string;
  meetingUrl?: string;
  regionValid?: boolean;
  prospectAttended?: boolean;
  clientAttended?: boolean;
  personAreaCorrect?: boolean;
  escalatedToCorrectArea?: boolean;
  concretada?: boolean;
  meetingStatus: MeetingStatus;
  cpValidation: CPValidation;
  cpBANT: BANTCriteria[];
  bantEvidence?: BANTEvidence[];
  bantScore?: number;
  cpComment: string;
  clientValidation: ClientValidation;
  clientBANT: BANTCriteria[];
  clientComment: string;
  clientDecision?: ClientDecision;
  clientDecisionAt?: string;
  rejectionReason?: RejectionReason;
  finalValidation: FinalValidation;
  commercialStatus: CommercialStatus;
  disputeFlag: boolean;
  pendingClientFlag: boolean;
  meetingSummary: string;
  preparationInfo?: string;
  validityReason?: string;
  recommendedAction?: MeetingAction;
  evidence?: MeetingEvidence;
  companyValidationStatus?: CompanyValidationStatus;
  ghlStageKey?: string;
  nextStep: string;
  internalNotes: string;
}

export type UserRole = "client" | "internal";

// Display labels
export const cpValidationLabels: Record<CPValidation, string> = {
  waiting_validation: "En espera",
  valid_cp: "Válida CP",
  not_valid_cp: "No válida CP",
  requires_review: "Requiere revisión",
  rescheduled: "Reagendada",
  not_completed: "No realizada",
};

export const clientValidationLabels: Record<ClientValidation, string> = {
  waiting_client_validation: "En espera cliente",
  valid_client: "Válida cliente",
  not_valid_client: "No válida cliente",
  requires_review: "Requiere revisión",
  rescheduled: "Reagendada",
  not_completed: "No realizada",
};

export const finalValidationLabels: Record<FinalValidation, string> = {
  pending: "Pendiente",
  final_valid: "Válida final",
  final_not_valid: "No válida final",
  in_dispute: "En disputa",
  rescheduled: "Reagendada",
  excluded_by_agreement: "Excluida por acuerdo",
};

export const commercialStatusLabels: Record<CommercialStatus, string> = {
  pending_followup: "Seguimiento pendiente",
  next_step_scheduled: "Próximo paso agendado",
  requested_proposal: "Solicita propuesta",
  proposal_sent: "Propuesta enviada",
  proposal_followup: "Seguimiento propuesta",
  negotiation: "Negociación",
  no_response: "Sin respuesta",
  client_won: "Cliente ganado",
  client_lost: "Cliente perdido",
  not_commercially_qualified: "No califica comercialmente",
};

export const meetingStatusLabels: Record<MeetingStatus, string> = {
  scheduled: "Agendada",
  completed: "Realizada",
  rescheduled: "Reagendada",
  cancelled: "Cancelada",
  no_show: "No asistió",
};

export const bantLabels: Record<BANTCriteria, string> = {
  budget: "Presupuesto",
  authority: "Autoridad",
  need: "Necesidad",
  timeline: "Timing",
};

export const rejectionReasonLabels: Record<RejectionReason, string> = {
  wrong_role: "Cargo incorrecto",
  outside_profile: "Empresa fuera del perfil acordado",
  prospect_no_show: "No asistió el prospecto",
  no_real_interest: "No hubo interés real",
  duplicate_meeting: "Reunión duplicada",
  existing_client_or_contact: "Ya era cliente/contacto existente",
  other: "Otro motivo",
};

export const clientDecisionLabels: Record<ClientDecision, string> = {
  pending: "Pendiente de validación",
  accepted: "Validada por cliente",
  rejected: "Objetada por cliente",
  review_requested: "Revisión solicitada",
};

export const meetingActionLabels: Record<MeetingAction, string> = {
  count: "Contar para meta",
  reschedule: "Reagendar",
  escalate: "Escalar contacto",
  manual_review: "Revisión manual",
};

// Extended types for new dashboards
export interface ClientContract {
  clientId: string;
  clientName: string;
  activeProspectingStartDate: string;
  contractStartDate: string;
  contractEndDate: string;
  contractGoal: number;
  currentPeriod: string;
}

export interface SDR {
  id: string;
  name: string;
  email: string;
  baseSalary: number;
  variableRate: number;
  bonusThreshold: number;
  bonusAmount: number;
  assignedClients: string[];
}

export interface Campaign {
  id: string;
  clientId: string;
  name: string;
  country: string;
  industry: string;
  channel: string;
  startDate: string;
  endDate: string;
  status: "active" | "paused" | "completed";
  contactsReached: number;
  replies: number;
  meetings: number;
  validMeetings: number;
}

export interface Alert {
  id: string;
  type: "warning" | "danger" | "info" | "success";
  title: string;
  description: string;
  clientId?: string;
  sdrId?: string;
  timestamp: string;
}

export interface SDRActivity {
  sdrId: string;
  date: string;
  callsMade: number;
  callMinutes: number;
  emailsSent: number;
  whatsappMessages: number;
  linkedinMessages: number;
  meetingsBooked: number;
  meetingsCompleted: number;
}

