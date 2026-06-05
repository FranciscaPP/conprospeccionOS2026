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

export interface Meeting {
  id: string;
  client: string;
  sdrAssigned: string;
  meetingDate: string;
  company: string;
  contact: string;
  jobTitle: string;
  meetingStatus: MeetingStatus;
  cpValidation: CPValidation;
  cpBANT: BANTCriteria[];
  cpComment: string;
  clientValidation: ClientValidation;
  clientBANT: BANTCriteria[];
  clientComment: string;
  finalValidation: FinalValidation;
  commercialStatus: CommercialStatus;
  disputeFlag: boolean;
  pendingClientFlag: boolean;
  meetingSummary: string;
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
  budget: "Budget",
  authority: "Authority",
  need: "Need",
  timeline: "Timeline",
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

