"use client";

import { useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import {
  BookOpen,
  Building2,
  Calendar,
  Check,
  CheckCircle2,
  ExternalLink,
  FileText,
  Lock,
  MessageSquare,
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
  getSimpleClientStatus,
  getValidationResultLabel,
  isClientLocked,
  isContractuallyValid,
  meetingStatusToCP,
} from "@/lib/meeting-rules";

interface MeetingDrawerProps {
  meeting: Meeting | null;
  open: boolean;
  onClose: () => void;
  mode: "client" | "internal";
}

type ClientDrawerTab = "validation" | "contact" | "evaluation" | "commercial";

const bantOptions: BANTCriteria[] = ["budget", "authority", "need", "timeline"];
const leadFieldClass = "min-w-0 space-y-1";
const leadValueClass = "min-w-0 break-words text-sm font-medium text-foreground [overflow-wrap:anywhere]";
const leadLinkClass = "min-w-0 break-words text-sm font-medium text-violet-700 hover:underline [overflow-wrap:anywhere]";

function EvidenceChecklist({ meeting }: { meeting: Meeting }) {
  const evidence = meeting.bantEvidence?.length
    ? meeting.bantEvidence
    : bantOptions.map((criteria) => ({
        criteria,
        met: meeting.cpBANT.includes(criteria),
        quote: meeting.cpBANT.includes(criteria)
          ? "Evidencia demo pendiente de transcript real."
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
              “{item.quote}”
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
    ? "bg-violet-100 text-violet-700 border-violet-300"
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
  const [rejectionReason, setRejectionReason] = useState<RejectionReason>("wrong_role");
  const [clientComment, setClientComment] = useState("");
  const [clientAction, setClientAction] = useState<Exclude<ClientDecision, "pending">>("accepted");
  const [commercialStatus, setCommercialStatus] = useState<CommercialStatus>("pending_followup");
  const [commercialNextStep, setCommercialNextStep] = useState("");
  const [clientTab, setClientTab] = useState<ClientDrawerTab>("validation");

  useEffect(() => {
    if (!meeting) return;
    setFormData(meeting);
    setRejectionReason(meeting.rejectionReason || "wrong_role");
    setClientComment(meeting.clientComment || "");
    setClientAction(meeting.clientDecision && meeting.clientDecision !== "pending" ? meeting.clientDecision : "accepted");
    setCommercialStatus(meeting.commercialStatus || "pending_followup");
    setCommercialNextStep(meeting.nextStep || "");
    setClientTab("validation");
  }, [meeting]);

  const previewFinal = useMemo(() => {
    if (!meeting) return "pending" as FinalValidation;
    return deriveFinalValidation({ ...meeting, ...formData });
  }, [meeting, formData]);

  if (!meeting) return null;

  const simpleStatus = getSimpleClientStatus(meeting);
  const clientDecision = getClientDecision(meeting);
  const locked = isClientLocked(meeting);
  const validByContract = isContractuallyValid(meeting);
  const isClientMode = mode === "client";
  const showClientSection = (tab: ClientDrawerTab) => !isClientMode || clientTab === tab;
  const clientTabs: Array<{ value: ClientDrawerTab; label: string }> = [
    { value: "validation", label: "Validar" },
    { value: "contact", label: "Contacto" },
    { value: "evaluation", label: "Evaluación" },
    { value: "commercial", label: "Avance" },
  ];

  const saveInternal = () => {
    updateMeeting(meeting.id, {
      ...formData,
      ...meetingStatusToCP((formData.meetingStatus || meeting.meetingStatus) as MeetingStatus),
      finalValidation: (formData.finalValidation || previewFinal) as FinalValidation,
      bantScore: (formData.cpBANT as BANTCriteria[] | undefined)?.length ?? meeting.bantScore,
    });
    onClose();
  };

  const acceptMeeting = () => {
    const updates: Partial<Meeting> = {
      clientValidation: "valid_client",
      clientDecision: "accepted",
      clientDecisionAt: new Date().toISOString(),
      clientComment,
      finalValidation: validByContract ? "final_valid" : "in_dispute",
    };
    updateMeeting(meeting.id, updates);
    void persistClientValidation(meeting.id, updates.finalValidation as FinalValidation);
    onClose();
  };

  const rejectMeeting = () => {
    const updates: Partial<Meeting> = {
      clientValidation: "not_valid_client",
      clientDecision: "rejected",
      clientDecisionAt: new Date().toISOString(),
      rejectionReason,
      clientComment,
      finalValidation: meeting.cpValidation === "valid_cp" ? "in_dispute" : "final_not_valid",
    };
    updateMeeting(meeting.id, updates);
    void persistClientValidation(meeting.id, updates.finalValidation as FinalValidation);
    onClose();
  };

  const requestReview = () => {
    const updates: Partial<Meeting> = {
      clientValidation: "requires_review",
      clientDecision: "review_requested",
      clientDecisionAt: new Date().toISOString(),
      clientComment,
      finalValidation: "in_dispute",
    };
    updateMeeting(meeting.id, updates);
    void persistClientValidation(meeting.id, "in_dispute");
    onClose();
  };

  const persistClientValidation = async (id: string, finalValidation: FinalValidation) => {
    try {
      const response = await fetch("/api/internal/meetings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, finalValidation }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "No se pudo guardar la validaciÃ³n.");
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "No se pudo guardar la validaciÃ³n.");
    } finally {
      await refreshMeetings();
    }
  };

  const saveClientDecision = () => {
    if (clientAction === "accepted") {
      acceptMeeting();
      return;
    }
    if (clientAction === "review_requested") {
      requestReview();
      return;
    }
    rejectMeeting();
  };

  const saveCommercialProgress = () => {
    updateMeeting(meeting.id, {
      commercialStatus,
      nextStep: commercialNextStep,
    });
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[calc(100vw-1rem)] p-0 sm:max-w-[560px]">
        <SheetHeader className="border-b border-border p-4 pb-3 sm:p-6 sm:pb-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <SheetTitle className="text-lg font-semibold">{meeting.company}</SheetTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {meeting.firstName} {meeting.lastName} · {meeting.jobTitle}
              </p>
            </div>
            <StatusBadge status={meeting.finalValidation} label={getValidationResultLabel(meeting)} />
          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100dvh-8rem)] sm:h-[calc(100vh-180px)]">
          <div className="space-y-5 p-4 sm:space-y-6 sm:p-6">
            {isClientMode && (
              <div className="sticky top-0 z-20 -mx-4 border-b border-border bg-background/95 px-4 py-4 backdrop-blur sm:-mx-6 sm:px-6">
                <div className="flex gap-2 overflow-x-auto pb-1 sm:grid sm:grid-cols-4 sm:overflow-visible sm:pb-0">
                  {clientTabs.map((tab) => (
                    <button
                      key={tab.value}
                      type="button"
                      onClick={() => setClientTab(tab.value)}
                      className={`min-h-12 min-w-[7.5rem] rounded-xl border px-4 py-3 text-sm font-semibold transition sm:min-w-0 ${
                        clientTab === tab.value
                          ? "border-violet-300 bg-violet-50 text-violet-700"
                          : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {isClientMode && clientTab === "validation" && (
              <section className="space-y-4">
                <div className="rounded-lg border border-violet-100 bg-violet-50/70 p-4">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <User className="h-4 w-4 text-violet-700" />
                    Validar reunión
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    Selecciona una decisión y guarda el registro. Si se objeta la reunión, el motivo es obligatorio.
                  </p>
                </div>

                <div className="grid gap-3 rounded-lg border border-border bg-muted/20 p-3 sm:grid-cols-2">
                  <div>
                    <Label className="text-xs text-muted-foreground">Resultado de revisión</Label>
                    <p className="text-sm font-medium text-foreground">{getValidationResultLabel(meeting)}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Fecha de calificación cliente</Label>
                    <p className="text-sm font-medium text-foreground">
                      {meeting.clientDecisionAt
                        ? format(new Date(meeting.clientDecisionAt), "d MMM yyyy · HH:mm")
                        : "Pendiente de registro"}
                    </p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Variables válidas</Label>
                    <p className="text-sm font-medium text-foreground">
                      {meeting.cpBANT.length > 0
                        ? meeting.cpBANT.map((criteria) => bantLabels[criteria]).join(", ")
                        : "Sin variables registradas"}
                    </p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Estado actual</Label>
                    <p className="text-sm font-medium text-foreground">{simpleStatus}</p>
                  </div>
                </div>

                {locked ? (
                  <div className="rounded-lg border border-border bg-muted/40 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
                      <Lock className="h-4 w-4" />
                      {clientDecisionLabels[clientDecision]}
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">
                      {clientDecision === "accepted" && "Reunión validada. Esta validación quedó registrada."}
                      {clientDecision === "rejected" && "Reunión objetada. Solo Conprospección puede reabrirla internamente si corresponde."}
                      {clientDecision === "review_requested" && "Solicitud de revisión registrada. No se puede modificar hasta respuesta de Conprospección."}
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
                        { value: "accepted", label: "Validar reunión" },
                        { value: "rejected", label: "Objetar reunión" },
                        { value: "review_requested", label: "Solicitar revisión" },
                      ].map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => setClientAction(option.value as Exclude<ClientDecision, "pending">)}
                          className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
                            clientAction === option.value
                              ? "border-violet-300 bg-violet-50 text-violet-700"
                              : "border-border bg-background text-foreground hover:bg-muted"
                          }`}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                    {clientAction === "accepted" && (
                      <div className="rounded-lg border border-emerald-100 bg-emerald-50/70 p-3 text-sm leading-6 text-emerald-800">
                        La reunión se marcará como validada y quedará registrada.
                      </div>
                    )}
                    {clientAction === "review_requested" && (
                      <div className="rounded-lg border border-amber-100 bg-amber-50/70 p-3 text-sm leading-6 text-amber-800">
                        La reunión quedará en revisión hasta respuesta de Conprospección.
                      </div>
                    )}
                    {clientAction === "rejected" && (
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Motivo si se objeta la reunión</Label>
                        <select
                          aria-label="Motivo si se objeta la reunión"
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
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Comentario opcional</Label>
                      <Textarea
                        value={clientComment}
                        onChange={(event) => setClientComment(event.target.value)}
                        placeholder="Agrega contexto si corresponde."
                        rows={3}
                      />
                    </div>
                  </>
                )}
              </section>
            )}

            {showClientSection("contact") && (
            <section className="space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Building2 className="h-4 w-4" />
                Información básica
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
              <div className="grid gap-4 rounded-lg border border-border bg-muted/20 p-3 sm:grid-cols-2">
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
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={meeting.meetingStatus} label={meetingStatusLabels[meeting.meetingStatus]} size="sm" />
                <StatusBadge status={meeting.finalValidation} label={simpleStatus} size="sm" />
                {locked && <StatusBadge status="final_valid" label="Registro bloqueado" size="sm" />}
              </div>
            </section>
            )}

            {showClientSection("evaluation") && <Separator />}

            {showClientSection("evaluation") && (
            <section className="space-y-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <MessageSquare className="h-4 w-4 text-violet-600" />
                Información de preparación
              </h3>
              <p className="rounded-lg bg-muted/50 p-3 text-sm leading-6 text-muted-foreground">
                {meeting.preparationInfo || meeting.meetingSummary}
              </p>
              <p className="text-xs leading-5 text-muted-foreground">
                Validez y resultado comercial son cosas distintas: una reunión válida puede contar para la meta aunque el negocio se gane, se pierda o quede en seguimiento.
              </p>
            </section>
            )}

            {showClientSection("evaluation") && <Separator />}

            {showClientSection("evaluation") && (
            <section className="space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <ShieldCheck className="h-4 w-4 text-violet-600" />
                {mode === "internal" ? "Validación Conprospección" : "Resultado de revisión"}
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
                <div className="rounded-lg border border-border bg-muted/30 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">{getValidationResultLabel(meeting)}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    La reunión fue revisada con la información disponible y las condiciones acordadas. El detalle operativo queda registrado internamente.
                  </p>
                </div>
              )}
            </section>
            )}

            {showClientSection("evaluation") && <Separator />}

            {showClientSection("evaluation") && (
            <section className="space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <BookOpen className="h-4 w-4 text-emerald-600" />
                {mode === "internal" ? "Evidencia y justificación" : "Evaluación de reunión"}
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
                      <span className="text-sm font-medium text-foreground">Resumen IA demo</span>
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
                <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-3">
                  <div>
                    <Label className="text-xs text-muted-foreground">Evaluación asistida de la reunión</Label>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {meeting.evidence?.aiSummary || meeting.validityReason || "Evaluación preparada con la información disponible de la reunión. Pendiente de integración real."}
                    </p>
                  </div>
                  <div className="rounded-lg border border-violet-100 bg-violet-50/60 p-3">
                    <Label className="text-xs text-muted-foreground">Grabación y análisis IA</Label>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      La estructura queda preparada para usar grabación y transcripción de la reunión. La IA podrá resumir conversación, detectar señales comerciales y sugerir el avance recomendado.
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
                    <Label className="text-xs text-muted-foreground">Variables comerciales consideradas</Label>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {meeting.cpBANT.length > 0 ? (
                        meeting.cpBANT.map((criteria) => (
                          <span
                            key={criteria}
                            className="rounded-full border border-violet-100 bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700"
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
                    Criterio base: perfil dentro del ICP acordado y al menos dos variables comerciales válidas.
                  </p>
                </div>
              )}
            </section>
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

            {isClientMode && clientTab === "commercial" && (
              <>
                <Separator />
                <section className="space-y-4">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    Avance comercial
                  </h3>
                  <div className="rounded-lg border border-border bg-muted/30 p-3">
                    <p className="mb-3 text-sm leading-6 text-muted-foreground">
                      Registro simple para seguimiento posterior a la reunión. Este avance comercial no modifica la validación para meta.
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Estado comercial</Label>
                        <select
                          aria-label="Estado comercial"
                          className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50"
                          value={commercialStatus}
                          onChange={(event) => setCommercialStatus(event.target.value as CommercialStatus)}
                        >
                          {Object.entries(commercialStatusLabels).map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Próximo paso comercial</Label>
                        <Input
                          value={commercialNextStep}
                          onChange={(event) => setCommercialNextStep(event.target.value)}
                          placeholder="Ej: Enviar propuesta comercial"
                        />
                      </div>
                    </div>
                    <div className="mt-3 rounded-lg border border-violet-100 bg-violet-50/60 p-3">
                      <Label className="text-xs text-muted-foreground">Análisis IA de avance</Label>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        {commercialNextStep
                          ? `Siguiente acción detectada: ${commercialNextStep}. La IA podrá cruzar este avance con la grabación y la transcripción cuando exista integración real.`
                          : "Pendiente de próximo paso comercial. La IA podrá sugerir avance cuando exista grabación/transcripción conectada."}
                      </p>
                    </div>
                    <div className="mt-3 flex justify-end">
                      <Button type="button" variant="outline" size="sm" onClick={saveCommercialProgress}>
                        Guardar avance
                      </Button>
                    </div>
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
              Guardar cambios
            </Button>
          ) : locked ? (
            <Button disabled className="flex-1">
              Validación registrada
            </Button>
          ) : clientTab !== "validation" ? (
            <Button
              type="button"
              onClick={() => setClientTab("validation")}
              className="flex-1 gap-1 bg-violet-600 text-white hover:bg-violet-700"
            >
              <CheckCircle2 className="h-4 w-4" />
              Ir a validar
            </Button>
          ) : (
            <Button onClick={saveClientDecision} className="flex-1 gap-1 bg-violet-600 text-white hover:bg-violet-700">
              <CheckCircle2 className="h-4 w-4" />
              Guardar decisión
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
