"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { format } from "date-fns";
import {
  BookOpen,
  Building2,
  Calendar,
  Check,
  CheckCircle2,
  ExternalLink,
  FileText,
  History,
  Lock,
  MessageSquare,
  PlayCircle,
  RotateCcw,
  ShieldCheck,
  User,
  XCircle,
} from "lucide-react";
import { useApp } from "@/lib/app-context";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StatusBadge } from "@/components/status-badge";
import type {
  BANTCriteria,
  ClientDecision,
  CommercialStatus,
  CPValidation,
  FinalValidation,
  Meeting,
  MeetingStatus,
  RejectionReason,
} from "@/lib/types";
import {
  bantLabels,
  clientDecisionLabels,
  commercialStatusLabels,
  cpValidationLabels,
  finalValidationLabels,
  meetingActionLabels,
  meetingStatusLabels,
  rejectionReasonLabels,
} from "@/lib/types";
import {
  deriveFinalValidation,
  getClientDecision,
  getValidationResultLabel,
  isClientLocked,
  meetingStatusToCP,
} from "@/lib/meeting-rules";

interface MeetingDrawerProps {
  meeting: Meeting | null;
  open: boolean;
  onClose: () => void;
  mode: "client" | "internal";
}

type ClientDrawerTab = "validation" | "contact" | "evaluation";

const bantOptions: BANTCriteria[] = ["budget", "authority", "need", "timeline"];
const clientBantOrder: BANTCriteria[] = ["need", "authority", "timeline", "budget"];
const leadFieldClass = "min-w-0 space-y-1";
const leadValueClass = "min-w-0 break-words text-sm font-medium text-foreground [overflow-wrap:anywhere]";
const leadLinkClass = "min-w-0 break-words text-sm font-medium text-[#333] underline-offset-2 hover:underline [overflow-wrap:anywhere]";

function safeFormatDate(value?: string, pattern = "d MMM yyyy") {
  if (!value) return "";
  try {
    return format(new Date(value), pattern);
  } catch {
    return "";
  }
}

function displayContactName(meeting: Meeting) {
  return [meeting.firstName, meeting.lastName].filter(Boolean).join(" ") || meeting.contact || "";
}

function clientIcpStatus(meeting: Meeting) {
  if (meeting.cpValidation === "valid_cp") return true;
  if (meeting.cpValidation === "not_valid_cp" || meeting.cpValidation === "not_completed") return false;
  if (meeting.personAreaCorrect === false || meeting.regionValid === false) return false;
  return meeting.personAreaCorrect === true || meeting.regionValid === true ? true : null;
}

function clientCpJustification(meeting: Meeting) {
  return meeting.validityReason || meeting.cpComment || "";
}

function ClientSectionTitle({
  icon,
  number,
  title,
}: {
  icon: ReactNode;
  number: number;
  title: string;
}) {
  return (
    <h3 className="flex items-center gap-2 text-[13px] font-semibold text-foreground">
      <span className="text-[#1d4ed8]">{icon}</span>
      <span className="font-semibold text-[var(--ink-3)]">{number}.</span>
      <span>{title}</span>
    </h3>
  );
}

function ClientField({ label, value }: { label: string; value?: ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-medium text-muted-foreground">{label}</p>
      <div className="min-h-[20px] break-words text-sm font-medium leading-5 text-foreground [overflow-wrap:anywhere]">
        {value || ""}
      </div>
    </div>
  );
}

function ClientExternalLink({ href, children }: { href?: string; children: ReactNode }) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 text-sm font-semibold text-[#1d4ed8] underline-offset-2 hover:underline"
    >
      {children}
      <ExternalLink className="h-3 w-3 shrink-0" />
    </a>
  );
}

function ClientEvidenceButton({
  icon,
  label,
  href,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  href?: string;
  onClick?: () => void;
}) {
  const className =
    "inline-flex h-9 items-center justify-center gap-2 rounded-[9px] border border-border bg-white px-4 text-sm font-semibold text-[#1d4ed8] transition hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:text-muted-foreground disabled:hover:bg-white";

  if (href) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={className}>
        {icon}
        {label}
      </a>
    );
  }

  return (
    <button type="button" className={className} onClick={onClick} disabled={!onClick}>
      {icon}
      {label}
    </button>
  );
}

function EvidenceChecklist({ meeting }: { meeting: Meeting }) {
  const evidence = meeting.bantEvidence?.length
    ? meeting.bantEvidence
    : bantOptions.map((criteria) => ({
        criteria,
        met: meeting.cpBANT.includes(criteria),
        quote: meeting.cpBANT.includes(criteria)
          ? "Evidencia pendiente de la transcripción."
          : "",
        note: meeting.cpBANT.includes(criteria) ? "Criterio detectado por Conprospección." : "Sin evidencia suficiente.",
      }));

  return (
    <div className="space-y-2">
      {evidence.map((item) => (
        <div key={item.criteria} className="rounded-lg border border-border bg-muted/30 p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className={item.met ? "text-emerald-600" : "text-muted-foreground"}>
                {item.met ? <Check className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
              </span>
              <span className="text-sm font-medium text-foreground">{bantLabels[item.criteria]}</span>
            </div>
            <span className="text-xs text-muted-foreground">{item.met ? "Cumple" : "No cumple"}</span>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.note}</p>
          {item.quote && (
            <p className="mt-2 rounded-md bg-background p-2 text-xs leading-5 text-foreground">
              "{item.quote}"
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function BantSelector({
  value,
  onChange,
  tone = "violet",
}: {
  value: BANTCriteria[];
  onChange: (value: BANTCriteria[]) => void;
  tone?: "violet" | "amber";
}) {
  const active = tone === "violet"
    ? "bg-[#f0f0ee] text-[#333] border-[#333]"
    : "bg-amber-100 text-amber-700 border-amber-300";
  return (
    <div className="flex flex-wrap gap-2">
      {bantOptions.map((criteria) => {
        const selected = value.includes(criteria);
        return (
          <button
            type="button"
            key={criteria}
            onClick={() =>
              onChange(selected ? value.filter((item) => item !== criteria) : [...value, criteria])
            }
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
              selected ? active : "bg-muted text-muted-foreground border-border hover:bg-muted/80"
            }`}
          >
            {bantLabels[criteria].charAt(0)} - {bantLabels[criteria]}
          </button>
        );
      })}
    </div>
  );
}

export function MeetingDrawer({ meeting, open, onClose, mode }: MeetingDrawerProps) {
  const { refreshMeetings, updateMeeting } = useApp();
  const [formData, setFormData] = useState<Partial<Meeting>>({});
  const [rejectionReason, setRejectionReason] = useState<RejectionReason>("icp_mismatch");
  const [clientComment, setClientComment] = useState("");
  const [clientAction, setClientAction] = useState<Exclude<ClientDecision, "pending">>("accepted");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [showReviewRequest, setShowReviewRequest] = useState(false);
  const [showAiSummary, setShowAiSummary] = useState(false);

  useEffect(() => {
    if (!meeting) return;
    setFormData(meeting);
    setRejectionReason(meeting.rejectionReason || "icp_mismatch");
    setClientComment(meeting.clientComment || "");
    setClientAction(meeting.clientDecision && meeting.clientDecision !== "pending" ? meeting.clientDecision : "accepted");
    setSaveError(null);
    setShowReviewRequest(false);
    setShowAiSummary(false);
  }, [meeting]);

  const previewFinal = useMemo(() => {
    if (!meeting) return "pending" as FinalValidation;
    return deriveFinalValidation({ ...meeting, ...formData });
  }, [meeting, formData]);

  if (!meeting) return null;

  const clientDecision = getClientDecision(meeting);
  const locked = isClientLocked(meeting);
  const isClientMode = mode === "client";
  const showClientSection = (_tab: ClientDrawerTab) => true;

  const saveInternal = () => {
    updateMeeting(meeting.id, {
      ...formData,
      ...meetingStatusToCP((formData.meetingStatus || meeting.meetingStatus) as MeetingStatus),
      finalValidation: (formData.finalValidation || previewFinal) as FinalValidation,
      bantScore: (formData.cpBANT as BANTCriteria[] | undefined)?.length ?? meeting.bantScore,
    });
    onClose();
  };

  const acceptMeeting = async () => {
    const finalValidation = deriveFinalValidation({
      ...meeting,
      clientValidation: "valid_client",
      clientDecision: "accepted",
    });
    const updates: Partial<Meeting> = {
      clientValidation: "valid_client",
      clientDecision: "accepted",
      clientDecisionAt: new Date().toISOString(),
      clientComment,
      finalValidation,
    };
    updateMeeting(meeting.id, updates);
    const ok = await persistClientValidation(meeting.id, updates);
    if (ok) onClose();
  };

  const rejectMeeting = async () => {
    const finalValidation = deriveFinalValidation({
      ...meeting,
      clientValidation: "not_valid_client",
      clientDecision: "rejected",
    });
    const updates: Partial<Meeting> = {
      clientValidation: "not_valid_client",
      clientDecision: "rejected",
      clientDecisionAt: new Date().toISOString(),
      rejectionReason,
      clientComment,
      finalValidation,
    };
    updateMeeting(meeting.id, updates);
    const ok = await persistClientValidation(meeting.id, updates);
    if (ok) onClose();
  };

  const requestReview = async () => {
    const finalValidation = deriveFinalValidation({
      ...meeting,
      clientValidation: "requires_review",
      clientDecision: "review_requested",
    });
    const updates: Partial<Meeting> = {
      clientValidation: "requires_review",
      clientDecision: "review_requested",
      clientDecisionAt: new Date().toISOString(),
      rejectionReason,
      clientComment,
      finalValidation,
    };
    updateMeeting(meeting.id, updates);
    const ok = await persistClientValidation(meeting.id, updates);
    if (ok) onClose();
  };

  const persistClientValidation = async (id: string, updates: Partial<Meeting>): Promise<boolean> => {
    try {
      const response = await fetch("/api/internal/meetings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id,
          finalValidation: updates.finalValidation,
          comment: updates.clientComment,
          reasons: updates.rejectionReason ? [rejectionReasonLabels[updates.rejectionReason]] : undefined,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "No se pudo guardar la validación.");
      return true;
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "No se pudo guardar la validación. Reintenta en unos segundos.");
      return false;
    } finally {
      await refreshMeetings();
    }
  };

  const saveClientDecision = () => {
    setSaveError(null);
    if (clientAction !== "accepted" && (!rejectionReason || clientComment.trim().length === 0)) {
      setSaveError("Para observar o disputar la validez, selecciona un motivo y agrega un comentario.");
      return;
    }
    if (clientAction === "accepted") {
      void acceptMeeting();
      return;
    }
    if (clientAction === "review_requested") {
      void requestReview();
      return;
    }
    void rejectMeeting();
  };

  const submitReviewRequest = () => {
    setSaveError(null);
    if (!rejectionReason || clientComment.trim().length === 0) {
      setSaveError("Para solicitar revisión, selecciona un motivo y agrega un comentario.");
      return;
    }
    void requestReview();
  };

  if (isClientMode) {
    const icpStatus = clientIcpStatus(meeting);
    const cpBant = meeting.cpBANT || [];
    const cpJustification = clientCpJustification(meeting);
    const meetingSummary = meeting.meetingSummary || meeting.preparationInfo || "";
    const aiSummary = meeting.evidence?.aiSummary || "";
    const meetingDate = safeFormatDate(meeting.meetingDate);
    const meetingTime = safeFormatDate(meeting.meetingDate, "HH:mm");
    const fullMeetingDate = safeFormatDate(meeting.meetingDate, "d MMM yyyy - HH:mm");
    const timeline: Array<{ title: string; date?: string; detail?: string; tone?: "ok" | "warn" | "bad" | "info" }> = [
      {
        title: "Reunión agendada",
        date: fullMeetingDate,
        tone: "info",
      },
    ];

    if (meeting.meetingStatus !== "scheduled") {
      timeline.push({
        title: `Reunión ${meetingStatusLabels[meeting.meetingStatus].toLowerCase()}`,
        date: fullMeetingDate,
        tone: meeting.meetingStatus === "completed" ? "ok" : meeting.meetingStatus === "no_show" || meeting.meetingStatus === "cancelled" ? "bad" : "warn",
      });
    }

    if (meeting.cpValidation !== "waiting_validation") {
      timeline.push({
        title: "Evaluación Conprospección emitida",
        detail: cpValidationLabels[meeting.cpValidation],
        tone: meeting.cpValidation === "valid_cp" ? "ok" : meeting.cpValidation === "not_valid_cp" || meeting.cpValidation === "not_completed" ? "bad" : "warn",
      });
    }

    if (clientDecision !== "pending") {
      timeline.push({
        title: clientDecision === "accepted" ? "Cliente confirmó reunión" : "Cliente solicitó revisión",
        date: safeFormatDate(meeting.clientDecisionAt, "d MMM yyyy - HH:mm"),
        detail: meeting.clientComment || (meeting.rejectionReason ? rejectionReasonLabels[meeting.rejectionReason] : ""),
        tone: clientDecision === "accepted" ? "ok" : "warn",
      });
    }

    if (meeting.finalValidation === "final_valid" || meeting.finalValidation === "final_not_valid" || meeting.finalValidation === "under_review" || meeting.finalValidation === "in_dispute") {
      timeline.push({
        title: finalValidationLabels[meeting.finalValidation],
        detail: getValidationResultLabel(meeting),
        tone: meeting.finalValidation === "final_valid" ? "ok" : meeting.finalValidation === "final_not_valid" ? "bad" : "warn",
      });
    }

    return (
      <Sheet open={open} onOpenChange={onClose}>
        <SheetContent className="w-[calc(100vw-32px)] overflow-hidden border-l border-[var(--line)] p-0 shadow-[0_16px_45px_rgba(20,20,20,.16)] sm:max-w-[560px]">
          <SheetHeader className="border-b border-border px-5 py-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <SheetTitle className="text-lg font-semibold leading-tight text-[var(--ink)]">
                  Detalle de reunión
                </SheetTitle>
                <div className="mt-2 flex items-center gap-2 text-[13px] font-medium text-muted-foreground">
                  <span className={`h-2.5 w-2.5 rounded-full ${meeting.meetingStatus === "completed" ? "bg-emerald-500" : meeting.meetingStatus === "no_show" || meeting.meetingStatus === "cancelled" ? "bg-red-500" : "bg-amber-500"}`} />
                  <span>
                    {meetingStatusLabels[meeting.meetingStatus]} {fullMeetingDate ? `el ${fullMeetingDate}` : ""}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar detalle"
                className="rounded-md p-1 text-muted-foreground transition hover:bg-muted hover:text-foreground"
              >
                <XCircle className="h-4 w-4" />
              </button>
            </div>
          </SheetHeader>

          <ScrollArea className="h-[calc(100dvh-9rem)] sm:h-[calc(100vh-9rem)]">
            <div className="space-y-5 px-5 py-5">
              <section className="space-y-3">
                <ClientSectionTitle icon={<User className="h-4 w-4" />} number={1} title="Contacto y empresa" />
                <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                  <ClientField label="Empresa" value={meeting.company} />
                  <ClientField label="País" value={meeting.country} />
                  <ClientField label="Contacto" value={displayContactName(meeting)} />
                  <ClientField
                    label="Website"
                    value={
                      <ClientExternalLink href={meeting.companyWebsite}>
                        {meeting.companyWebsite?.replace(/^https?:\/\//, "")}
                      </ClientExternalLink>
                    }
                  />
                  <ClientField label="Cargo" value={meeting.jobTitle} />
                  <ClientField
                    label="LinkedIn empresa"
                    value={<ClientExternalLink href={meeting.companyLinkedinUrl}>Ver empresa</ClientExternalLink>}
                  />
                  <ClientField label="Email" value={meeting.leadEmail} />
                  <ClientField
                    label="LinkedIn contacto"
                    value={<ClientExternalLink href={meeting.contactLinkedinUrl}>Ver perfil</ClientExternalLink>}
                  />
                  <ClientField label="Teléfono" value={meeting.leadPhone} />
                  <ClientField
                    label="Link reunión"
                    value={<ClientExternalLink href={meeting.meetingUrl}>Unirse a la reunión</ClientExternalLink>}
                  />
                  <ClientField label="Fecha reunión" value={meetingDate} />
                  <ClientField label="Hora reunión" value={meetingTime} />
                </div>
              </section>

              <Separator />

              <section className="space-y-2">
                <ClientSectionTitle icon={<MessageSquare className="h-4 w-4" />} number={2} title="Resumen de reunión" />
                <p className="line-clamp-6 text-sm leading-6 text-muted-foreground">
                  {meetingSummary}
                </p>
              </section>

              <Separator />

              <section className="space-y-3">
                <ClientSectionTitle icon={<ShieldCheck className="h-4 w-4" />} number={3} title="Evaluación Conprospección" />
                <div className="grid gap-3 sm:grid-cols-[0.9fr_1.1fr]">
                  <div className="rounded-[12px] border border-border bg-white p-3 shadow-sm">
                    <p className="text-[11px] font-semibold uppercase tracking-[.05em] text-muted-foreground">ICP</p>
                    <div className={`mt-2 flex items-center gap-2 text-sm font-bold ${icpStatus === false ? "text-red-600" : "text-emerald-600"}`}>
                      {icpStatus === false ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                      {icpStatus === false ? "No cumple" : "Cumple"}
                    </div>
                    <p className="mt-2 text-xs leading-5 text-muted-foreground">
                      ICP trabajado desde base/campaña y revisado por Conprospección.
                    </p>
                  </div>

                  <div className="rounded-[12px] border border-border bg-white p-3 shadow-sm">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[.05em] text-muted-foreground">BANT</p>
                      <p className="text-sm font-bold text-foreground">{cpBant.length} de 4 variables</p>
                    </div>
                    <div className="mt-2 space-y-1.5">
                      {clientBantOrder.map((criteria) => {
                        const detected = cpBant.includes(criteria);
                        return (
                          <div key={criteria} className="flex items-center justify-between gap-3 text-xs text-foreground">
                            <span>{bantLabels[criteria]}</span>
                            <span className={detected ? "text-emerald-600" : "text-muted-foreground/50"}>
                              {detected ? <CheckCircle2 className="h-4 w-4" /> : "—"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
                <div className="rounded-[12px] border border-[#dbeafe] bg-[#eff6ff] px-3.5 py-2.5 text-xs leading-5 text-[#1e40af]">
                  La IA aporta evidencia y señales de la conversación. La decisión de validez la emite Conprospección.
                </div>
              </section>

              <Separator />

              <section className="space-y-2">
                <ClientSectionTitle icon={<BookOpen className="h-4 w-4" />} number={4} title="Justificación Conprospección" />
                <p className="rounded-[12px] border border-border bg-white p-3 text-sm leading-6 text-foreground shadow-sm">
                  {cpJustification}
                </p>
              </section>

              <Separator />

              <section className="space-y-3">
                <ClientSectionTitle icon={<FileText className="h-4 w-4" />} number={5} title="Evidencia" />
                <div className="grid gap-2 sm:grid-cols-3">
                  <ClientEvidenceButton
                    icon={<PlayCircle className="h-4 w-4" />}
                    label="Ver grabación"
                    href={meeting.evidence?.recordingUrl}
                  />
                  <ClientEvidenceButton
                    icon={<FileText className="h-4 w-4" />}
                    label="Ver transcripción"
                    href={meeting.evidence?.transcriptUrl}
                  />
                  <ClientEvidenceButton
                    icon={<BookOpen className="h-4 w-4" />}
                    label="Ver resumen IA"
                    onClick={aiSummary ? () => setShowAiSummary((value) => !value) : undefined}
                  />
                </div>
                {showAiSummary && aiSummary && (
                  <p className="rounded-[10px] border border-border bg-[#f8f8f6] p-3 text-xs leading-6 text-muted-foreground">
                    {aiSummary}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  {clientBantOrder.map((criteria) => (
                    <span
                      key={criteria}
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${
                        cpBant.includes(criteria)
                          ? "border-[#c7ebde] bg-[var(--ok-bg)] text-[var(--ok-ink)]"
                          : "border-border bg-white text-muted-foreground"
                      }`}
                    >
                      {bantLabels[criteria]}
                    </span>
                  ))}
                </div>
              </section>

              <Separator />

              <section className="space-y-3">
                <ClientSectionTitle icon={<CheckCircle2 className="h-4 w-4" />} number={6} title="Acción cliente" />
                {locked ? (
                  <div className="rounded-[11px] border border-border bg-[#f8f8f6] p-3 text-sm leading-6 text-muted-foreground">
                    <div className="mb-1 flex items-center gap-2 font-semibold text-foreground">
                      <Lock className="h-4 w-4" />
                      {clientDecisionLabels[clientDecision]}
                    </div>
                    {clientDecision === "accepted"
                      ? "Confirmación registrada. La reunión quedó bloqueada para nuevas acciones."
                      : "Solicitud de revisión registrada. Conprospección revisará la evidencia y el motivo informado."}
                  </div>
                ) : (
                  <>
                    <p className="text-sm leading-5 text-muted-foreground">
                      Confirma la evaluación realizada por Conprospección o solicita revisión.
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Button onClick={() => void acceptMeeting()} className="h-10 gap-2 bg-emerald-600 text-white hover:bg-emerald-700">
                        <CheckCircle2 className="h-4 w-4" />
                        Confirmar reunión
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setShowReviewRequest((value) => !value)}
                        className="h-10 gap-2 border-orange-400 text-orange-600 hover:bg-orange-50"
                      >
                        <RotateCcw className="h-4 w-4" />
                        Solicitar revisión
                      </Button>
                    </div>
                    {showReviewRequest && (
                      <div className="space-y-2 rounded-[11px] border border-orange-200 bg-orange-50/50 p-3">
                        <Label className="text-xs text-muted-foreground">Motivo</Label>
                        <select
                          aria-label="Motivo de revisión"
                          className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50"
                          value={rejectionReason}
                          onChange={(event) => setRejectionReason(event.target.value as RejectionReason)}
                        >
                          {Object.entries(rejectionReasonLabels).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <Label className="text-xs text-muted-foreground">Comentario obligatorio</Label>
                        <Textarea
                          value={clientComment}
                          onChange={(event) => setClientComment(event.target.value)}
                          placeholder="Describe el motivo de la revisión."
                          rows={3}
                        />
                        <Button onClick={submitReviewRequest} className="bg-orange-600 text-white hover:bg-orange-700">
                          Enviar solicitud de revisión
                        </Button>
                      </div>
                    )}
                  </>
                )}
                {saveError && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm leading-6 text-red-700">
                    {saveError}
                  </div>
                )}
              </section>

              <Separator />

              <section className="space-y-3">
                <ClientSectionTitle icon={<History className="h-4 w-4" />} number={7} title="Historial" />
                <ol className="relative space-y-4 border-l border-border pl-5">
                  {timeline.map((item, index) => {
                    const dotClass =
                      item.tone === "ok"
                        ? "bg-emerald-500"
                        : item.tone === "bad"
                          ? "bg-red-500"
                          : item.tone === "warn"
                            ? "bg-orange-500"
                            : "bg-[#1d4ed8]";
                    return (
                      <li key={`${item.title}-${index}`} className="relative">
                        <span className={`absolute -left-[23px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white ${dotClass}`} />
                        {item.date && <p className="font-display tnum text-[11px] font-medium text-muted-foreground">{item.date}</p>}
                        <p className="text-sm font-semibold text-foreground">{item.title}</p>
                        {item.detail && <p className="text-xs leading-5 text-muted-foreground">{item.detail}</p>}
                      </li>
                    );
                  })}
                </ol>
              </section>
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[calc(100vw-36px)] overflow-hidden border border-[var(--line)] p-0 shadow-[0_16px_45px_rgba(20,20,20,.16)] sm:max-w-[560px]">
        <SheetHeader className="border-b border-border p-4 pb-3 sm:p-[18px]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <SheetTitle className="text-xl font-medium leading-tight">{meeting.company}</SheetTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {meeting.firstName} {meeting.lastName} · {meeting.jobTitle}
              </p>
            </div>
            <StatusBadge status={meeting.finalValidation} label={getValidationResultLabel(meeting)} />
          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100dvh-8rem)] sm:h-[calc(100vh-180px)]">
          <div className="space-y-3 p-4 sm:p-[18px]">
            {isClientMode && (
              <section className="rounded-[11px] border border-[var(--line)] bg-[#f8f8f6] p-3 text-sm leading-5 text-muted-foreground">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <StatusBadge status={meeting.finalValidation} label={getValidationResultLabel(meeting)} size="sm" />
                  <StatusBadge status={meeting.cpValidation} label={cpValidationLabels[meeting.cpValidation]} size="sm" />
                </div>
                <p>
                  Flujo de validación: reunión realizada, ICP trabajado desde base/campaña, mínimo 2/4 variables BANT detectadas por IA/CP y evidencia suficiente.
                </p>
              </section>
            )}
            {showClientSection("contact") && (
            <section className="space-y-3 rounded-[12px] border border-[var(--line)] bg-white p-3">
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.07em] text-[var(--ink-3)]">
                <Building2 className="h-4 w-4" />
                {isClientMode ? "Qué reunión fue" : "Información básica"}
              </h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label className="text-xs text-muted-foreground">Empresa</Label>
                  <p className="text-sm font-medium text-foreground">{meeting.company}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Contacto</Label>
                  <p className="text-sm font-medium text-foreground">{meeting.firstName} {meeting.lastName}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Cargo</Label>
                  <p className="text-sm font-medium text-foreground">{meeting.jobTitle}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Fecha y hora</Label>
                  <p className="text-sm font-medium text-foreground">
                    {format(new Date(meeting.meetingDate), "d MMM yyyy · HH:mm")}
                  </p>
                </div>
                {mode === "internal" && (
                  <>
                    <div>
                      <Label className="text-xs text-muted-foreground">Cliente</Label>
                      <p className="text-sm font-medium text-foreground">{meeting.client}</p>
                    </div>
                    <div>
                      <Label className="text-xs text-muted-foreground">SDR</Label>
                      <p className="text-sm font-medium text-foreground">{meeting.sdrAssigned}</p>
                    </div>
                    <div>
                      <Label className="text-xs text-muted-foreground">País / región</Label>
                      <p className="text-sm font-medium text-foreground">{meeting.country || "Chile"}</p>
                    </div>
                  </>
                )}
              </div>
              <div className="grid gap-3 rounded-[11px] border border-border bg-[#fbfbfa] p-3 sm:grid-cols-2">
                <div className={leadFieldClass}>
                  <Label className="text-xs text-muted-foreground">País</Label>
                  <p className={leadValueClass}>{meeting.country || "Chile"}</p>
                </div>
                <div className={leadFieldClass}>
                  <Label className="text-xs text-muted-foreground">Industria</Label>
                  <p className={leadValueClass}>{meeting.leadIndustry || "Sin dato"}</p>
                </div>
                <div className={leadFieldClass}>
                  <Label className="text-xs text-muted-foreground">Correo</Label>
                  {meeting.leadEmail ? (
                    <a className={leadLinkClass} href={`mailto:${meeting.leadEmail}`}>
                      {meeting.leadEmail}
                    </a>
                  ) : (
                    <p className={leadValueClass}>Sin dato</p>
                  )}
                </div>
                <div className={leadFieldClass}>
                  <Label className="text-xs text-muted-foreground">Teléfono</Label>
                  {meeting.leadPhone ? (
                    <a className={leadLinkClass} href={`tel:${meeting.leadPhone}`}>
                      {meeting.leadPhone}
                    </a>
                  ) : (
                    <p className={leadValueClass}>Sin dato</p>
                  )}
                </div>
                <div className={leadFieldClass}>
                  <Label className="text-xs text-muted-foreground">Sitio web</Label>
                  {meeting.companyWebsite ? (
                    <a className={leadLinkClass} href={meeting.companyWebsite} target="_blank" rel="noreferrer">
                      Abrir sitio
                    </a>
                  ) : (
                    <p className={leadValueClass}>Sin dato</p>
                  )}
                </div>
                <div className={leadFieldClass}>
                  <Label className="text-xs text-muted-foreground">LinkedIn contacto</Label>
                  {meeting.contactLinkedinUrl ? (
                    <a className={leadLinkClass} href={meeting.contactLinkedinUrl} target="_blank" rel="noreferrer">
                      Ver perfil
                    </a>
                  ) : (
                    <p className={leadValueClass}>Sin dato</p>
                  )}
                </div>
                <div className={leadFieldClass}>
                  <Label className="text-xs text-muted-foreground">LinkedIn empresa</Label>
                  {meeting.companyLinkedinUrl ? (
                    <a className={leadLinkClass} href={meeting.companyLinkedinUrl} target="_blank" rel="noreferrer">
                      Ver empresa
                    </a>
                  ) : (
                    <p className={leadValueClass}>Sin dato</p>
                  )}
                </div>
                <div className={leadFieldClass}>
                  <Label className="text-xs text-muted-foreground">Link de reunión</Label>
                  {meeting.meetingUrl ? (
                    <a className={leadLinkClass} href={meeting.meetingUrl} target="_blank" rel="noreferrer">
                      Abrir reunión
                    </a>
                  ) : (
                    <p className={leadValueClass}>Sin dato</p>
                  )}
                </div>
              </div>
            </section>
            )}

            {showClientSection("evaluation") && <Separator />}

            {showClientSection("evaluation") && (
            <section className="space-y-3 rounded-[12px] border border-[var(--line)] bg-white p-3">
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.07em] text-[var(--ink-3)]">
                <MessageSquare className="h-4 w-4 text-violet-600" />
                Resumen de reunión
              </h3>
              <p className="rounded-[9px] border border-[var(--line)] bg-[#f8f8f6] p-3 text-sm leading-6 text-muted-foreground">
                {meeting.preparationInfo || meeting.meetingSummary}
              </p>
              <p className="text-xs leading-5 text-muted-foreground">
                Esta revisión corresponde solo a la validez contractual de la reunión.
              </p>
            </section>
            )}

            {showClientSection("evaluation") && <Separator />}

            {showClientSection("evaluation") && (
            <section className="space-y-3 rounded-[12px] border border-[var(--line)] bg-white p-3">
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.07em] text-[var(--ink-3)]">
                <ShieldCheck className="h-4 w-4 text-violet-600" />
                {mode === "internal" ? "Validación Conprospección" : "Evaluación de Conprospección"}
              </h3>

              {mode === "internal" ? (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Estado operativo</Label>
                      <select
                        className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50"
                        value={formData.meetingStatus as MeetingStatus}
                        onChange={(event) => setFormData({ ...formData, meetingStatus: event.target.value as MeetingStatus })}
                      >
                        {Object.entries(meetingStatusLabels).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Validación Conprospección</Label>
                      <select
                        className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50"
                        value={formData.cpValidation as CPValidation}
                        onChange={(event) => setFormData({ ...formData, cpValidation: event.target.value as CPValidation })}
                      >
                        {Object.entries(cpValidationLabels).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">BANT CP</Label>
                    <BantSelector
                      value={(formData.cpBANT as BANTCriteria[]) || []}
                      onChange={(value) => setFormData({ ...formData, cpBANT: value })}
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-3 rounded-[11px] border border-border bg-[#f8f8f6] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={meeting.finalValidation} label={getValidationResultLabel(meeting)} size="sm" />
                    <StatusBadge status={meeting.meetingStatus} label={meetingStatusLabels[meeting.meetingStatus]} size="sm" />
                  </div>
                  <p className="text-sm leading-6 text-muted-foreground">
                    Conprospección revisó evidencia, cumplimiento del ICP trabajado desde base/campaña y variables BANT detectadas por IA/CP.
                  </p>
                </div>
              )}
            </section>
            )}

            {showClientSection("evaluation") && <Separator />}

            {showClientSection("evaluation") && (
            <section className="space-y-3 rounded-[12px] border border-[var(--line)] bg-white p-3">
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.07em] text-[var(--ink-3)]">
                <BookOpen className="h-4 w-4 text-emerald-600" />
                {mode === "internal" ? "Evidencia y justificación" : "Grabación y evaluación de la reunión"}
              </h3>
              {mode === "internal" ? (
                <>
                  <div className="grid gap-3 text-sm sm:grid-cols-2">
                    <div className="rounded-lg border border-border p-3">
                      <Label className="text-xs text-muted-foreground">Asistió prospecto</Label>
                      <p className="font-medium text-foreground">{meeting.prospectAttended === false ? "No" : "Sí"}</p>
                    </div>
                    <div className="rounded-lg border border-border p-3">
                      <Label className="text-xs text-muted-foreground">Asistió cliente</Label>
                      <p className="font-medium text-foreground">{meeting.clientAttended === false ? "No" : "Sí"}</p>
                    </div>
                  </div>
                  <EvidenceChecklist meeting={meeting} />
                  <div className="rounded-lg border border-violet-100 bg-violet-50/60 p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm font-medium text-foreground">Resumen IA</span>
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">
                      {meeting.evidence?.aiSummary || "Sección preparada para resumen de reunión. Pendiente de integración real."}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <a
                        className="inline-flex h-7 items-center gap-2 rounded-lg border border-border bg-background px-2.5 text-[0.8rem] font-medium text-foreground hover:bg-muted"
                        href={meeting.evidence?.transcriptUrl || "#"}
                      >
                        <FileText className="h-4 w-4" /> Transcripción <ExternalLink className="h-3 w-3" />
                      </a>
                      <a
                        className="inline-flex h-7 items-center gap-2 rounded-lg border border-border bg-background px-2.5 text-[0.8rem] font-medium text-foreground hover:bg-muted"
                        href={meeting.evidence?.recordingUrl || "#"}
                      >
                        <Calendar className="h-4 w-4" /> Grabación <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </>
              ) : (
                <div className="space-y-3">
                  <div>
                    <Label className="text-xs text-muted-foreground">Evaluación asistida de la reunión</Label>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {meeting.evidence?.aiSummary || meeting.validityReason || "Evaluación preparada con la información disponible de la reunión. Pendiente de integración real."}
                    </p>
                  </div>
                  <div className="rounded-[11px] border border-[var(--line)] bg-[#fbfbfa] p-3">
                    <Label className="text-xs text-muted-foreground">Grabación y análisis IA</Label>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      La evidencia disponible permite revisar grabación, transcripción, resumen IA y señales BANT detectadas por IA/CP.
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <a
                        className="inline-flex h-7 items-center gap-2 rounded-lg border border-border bg-background px-2.5 text-[0.8rem] font-medium text-foreground hover:bg-muted"
                        href={meeting.evidence?.recordingUrl || "#"}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <Calendar className="h-4 w-4" /> Grabación <ExternalLink className="h-3 w-3" />
                      </a>
                      <a
                        className="inline-flex h-7 items-center gap-2 rounded-lg border border-border bg-background px-2.5 text-[0.8rem] font-medium text-foreground hover:bg-muted"
                        href={meeting.evidence?.transcriptUrl || "#"}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <FileText className="h-4 w-4" /> Transcripción <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">BANT detectado por IA/CP</Label>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {meeting.cpBANT.length > 0 ? (
                        meeting.cpBANT.map((criteria) => (
                          <span
                            key={criteria}
                            className="rounded-full border border-[#c7ebde] bg-[var(--ok-bg)] px-2.5 py-1 text-xs font-medium text-[var(--ok-ink)]"
                          >
                            {bantLabels[criteria]}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm text-muted-foreground">Sin variables registradas.</span>
                      )}
                    </div>
                  </div>
                  <p className="text-xs leading-5 text-muted-foreground">
                    Mínimo requerido para validez: 2/4 variables BANT detectadas por IA/CP.
                  </p>
                  <EvidenceChecklist meeting={meeting} />
                  <p className="text-xs leading-5 text-muted-foreground">
                    Criterio base: ICP trabajado desde base/campaña, mínimo requerido 2/4 variables BANT detectadas por IA/CP y evidencia suficiente.
                  </p>
                </div>
              )}
            </section>
            )}

            {isClientMode && (
              <>
                <Separator />
                <section className="space-y-3 rounded-[12px] border border-[var(--line)] bg-white p-3">
                  <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.07em] text-[var(--ink-3)]">
                    <User className="h-4 w-4 text-violet-700" />
                    Tu validación
                  </h3>
                  {locked ? (
                    <div className="rounded-[11px] border border-border bg-[#f8f8f6] p-4">
                      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
                        <Lock className="h-4 w-4" />
                        {clientDecisionLabels[clientDecision]}
                      </div>
                      <p className="text-sm leading-6 text-muted-foreground">
                        {clientDecision === "accepted" && "Reunión aceptada. Esta validación quedó registrada."}
                        {clientDecision === "rejected" && "Validez disputada. Conprospección revisará el respaldo y el motivo contractual."}
                        {clientDecision === "review_requested" && "Observación registrada. Conprospección revisará el respaldo y el motivo contractual."}
                      </p>
                      {meeting.rejectionReason && (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Motivo: {rejectionReasonLabels[meeting.rejectionReason]}
                        </p>
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="grid gap-2 sm:grid-cols-3">
                        {[
                          { value: "accepted", label: "Aceptar reunión" },
                          { value: "review_requested", label: "Observar" },
                          { value: "rejected", label: "Disputar validez" },
                        ].map((option) => (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => {
                              const nextAction = option.value as Exclude<ClientDecision, "pending">;
                              setClientAction(nextAction);
                            }}
                            className={`min-h-10 rounded-[9px] border px-3 py-2 text-sm font-semibold transition ${
                              clientAction === option.value
                                ? option.value === "accepted"
                                  ? "border-[#78c5a3] bg-[var(--ok-bg)] text-[var(--ok-ink)]"
                                  : option.value === "review_requested"
                                    ? "border-[#dc9c63] bg-[var(--rev-bg)] text-[var(--rev-ink)]"
                                    : "border-[#dc958d] bg-[var(--bad-bg)] text-[var(--bad-ink)]"
                                : "border-border bg-background text-foreground hover:bg-muted"
                            }`}
                          >
                            {option.label}
                          </button>
                        ))}
                      </div>
                      {clientAction !== "accepted" && (
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">Motivo contractual</Label>
                          <select
                            aria-label="Motivo contractual"
                            className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50"
                            value={rejectionReason}
                            onChange={(event) => setRejectionReason(event.target.value as RejectionReason)}
                          >
                            {Object.entries(rejectionReasonLabels).map(([value, label]) => (
                              <option key={value} value={value}>
                                {label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      {clientAction !== "accepted" && meeting.cpValidation === "valid_cp" && (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
                          CP ya validó esta reunión con evidencia, ICP trabajado y variables BANT IA/CP. Si observas o disputas la validez, revisaremos el respaldo y el motivo contractual.
                        </div>
                      )}
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">
                          {clientAction === "accepted" ? "Comentario opcional" : "Comentario obligatorio"}
                        </Label>
                        <Textarea
                          value={clientComment}
                          onChange={(event) => setClientComment(event.target.value)}
                          placeholder="Describe el motivo contractual con el contexto necesario."
                          rows={3}
                        />
                      </div>
                    </>
                  )}
                  {saveError && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm leading-6 text-red-700">
                      {saveError}
                    </div>
                  )}
                  <div className="rounded-[11px] border border-[var(--line)] bg-[#fbfbfa] p-3 text-xs leading-5 text-muted-foreground">
                    <div className="mb-1 font-semibold uppercase tracking-[.07em] text-[var(--ink-3)]">Historial</div>
                    <p>
                      Estado cliente: <span className="font-medium text-foreground">{clientDecisionLabels[clientDecision]}</span>
                    </p>
                    <p>
                      Registrado:{" "}
                      <span className="font-medium text-foreground">
                        {meeting.clientDecisionAt ? format(new Date(meeting.clientDecisionAt), "d MMM yyyy · HH:mm") : "Pendiente"}
                      </span>
                    </p>
                  </div>
                </section>
              </>
            )}

            {mode === "internal" && (
              <>
                <Separator />
                <section className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground">Gestión interna</h3>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Resultado para meta</Label>
                      <select
                        className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50"
                        value={(formData.finalValidation || previewFinal) as FinalValidation}
                        onChange={(event) => setFormData({ ...formData, finalValidation: event.target.value as FinalValidation })}
                      >
                        {Object.entries(finalValidationLabels).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Estado comercial</Label>
                      <select
                        className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50"
                        value={formData.commercialStatus as CommercialStatus}
                        onChange={(event) => setFormData({ ...formData, commercialStatus: event.target.value as CommercialStatus })}
                      >
                        {Object.entries(commercialStatusLabels).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Próximo paso</Label>
                    <Input
                      value={formData.nextStep || ""}
                      onChange={(event) => setFormData({ ...formData, nextStep: event.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Notas internas</Label>
                    <Textarea
                      value={formData.internalNotes || ""}
                      onChange={(event) => setFormData({ ...formData, internalNotes: event.target.value })}
                      rows={3}
                    />
                  </div>
                  <div className="rounded-lg border border-border bg-muted/30 p-3 text-sm text-muted-foreground">
                    Acción sugerida: <b className="text-foreground">{meetingActionLabels[meeting.recommendedAction || "manual_review"]}</b>
                  </div>
                </section>
              </>
            )}
          </div>
        </ScrollArea>

        <div className="flex gap-3 border-t border-border p-4">
          <Button variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          {mode === "internal" ? (
            <Button onClick={saveInternal} className="flex-1 bg-violet-600 text-white hover:bg-violet-700">
              Guardar
            </Button>
          ) : locked ? (
            <Button disabled className="flex-1">
              Validación registrada
            </Button>
          ) : (
            <Button onClick={saveClientDecision} className="flex-1 gap-1 bg-violet-600 text-white hover:bg-violet-700">
              <CheckCircle2 className="h-4 w-4" />
              Guardar
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
