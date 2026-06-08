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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusBadge } from "@/components/status-badge";
import type {
  BANTCriteria,
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
  getBANTScore,
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

const bantOptions: BANTCriteria[] = ["budget", "authority", "need", "timeline"];

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
  const { updateMeeting } = useApp();
  const [formData, setFormData] = useState<Partial<Meeting>>({});
  const [rejectionReason, setRejectionReason] = useState<RejectionReason>("wrong_role");
  const [clientComment, setClientComment] = useState("");

  useEffect(() => {
    if (!meeting) return;
    setFormData(meeting);
    setRejectionReason(meeting.rejectionReason || "wrong_role");
    setClientComment(meeting.clientComment || "");
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
  const bantScore = getBANTScore(meeting);

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
    updateMeeting(meeting.id, {
      clientValidation: "valid_client",
      clientDecision: "accepted",
      clientDecisionAt: new Date().toISOString(),
      clientComment,
      finalValidation: validByContract ? "final_valid" : "in_dispute",
    });
    onClose();
  };

  const rejectMeeting = () => {
    updateMeeting(meeting.id, {
      clientValidation: "not_valid_client",
      clientDecision: "rejected",
      clientDecisionAt: new Date().toISOString(),
      rejectionReason,
      clientComment,
      finalValidation: meeting.cpValidation === "valid_cp" ? "in_dispute" : "final_not_valid",
    });
    onClose();
  };

  const requestReview = () => {
    updateMeeting(meeting.id, {
      clientValidation: "requires_review",
      clientDecision: "review_requested",
      clientDecisionAt: new Date().toISOString(),
      clientComment,
      finalValidation: "in_dispute",
    });
    onClose();
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[520px] p-0 sm:max-w-[520px]">
        <SheetHeader className="border-b border-border p-6 pb-4">
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

        <ScrollArea className="h-[calc(100vh-180px)]">
          <div className="space-y-6 p-6">
            <section className="space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Building2 className="h-4 w-4" />
                Información básica
              </h3>
              <div className="grid grid-cols-2 gap-4">
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
                    <div>
                      <Label className="text-xs text-muted-foreground">Stage GHL futuro</Label>
                      <p className="text-sm font-medium text-foreground">{meeting.ghlStageKey || "pendiente_validacion"}</p>
                    </div>
                  </>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={meeting.meetingStatus} label={meetingStatusLabels[meeting.meetingStatus]} size="sm" />
                <StatusBadge status={meeting.finalValidation} label={simpleStatus} size="sm" />
                {locked && <StatusBadge status="final_valid" label="Registro bloqueado" size="sm" />}
              </div>
            </section>

            <Separator />

            <section className="space-y-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <MessageSquare className="h-4 w-4 text-violet-600" />
                Resumen ejecutivo
              </h3>
              <p className="rounded-lg bg-muted/50 p-3 text-sm leading-6 text-muted-foreground">
                {meeting.meetingSummary}
              </p>
              <p className="text-xs leading-5 text-muted-foreground">
                Validez y resultado comercial son cosas distintas: una reunión válida puede contar para la meta aunque el negocio se gane, se pierda o quede en seguimiento.
              </p>
            </section>

            <Separator />

            <section className="space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <ShieldCheck className="h-4 w-4 text-violet-600" />
                Validación Conprospección
              </h3>

              {mode === "internal" ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Estado reunión</Label>
                      <Select
                        value={formData.meetingStatus as MeetingStatus}
                        onValueChange={(value) => setFormData({ ...formData, meetingStatus: value as MeetingStatus })}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(meetingStatusLabels).map(([value, label]) => (
                            <SelectItem key={value} value={value}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Validación CP</Label>
                      <Select
                        value={formData.cpValidation as CPValidation}
                        onValueChange={(value) => setFormData({ ...formData, cpValidation: value as CPValidation })}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(cpValidationLabels).map(([value, label]) => (
                            <SelectItem key={value} value={value}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
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
                    <span className="text-xs text-muted-foreground">BANT {bantScore}/4</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {meeting.validityReason || meeting.cpComment || "Evaluación basada en perfil acordado y evidencia disponible."}
                  </p>
                </div>
              )}
            </section>

            <Separator />

            <section className="space-y-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <BookOpen className="h-4 w-4 text-emerald-600" />
                Evidencia y justificación
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
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
                  <span className="text-xs text-muted-foreground">
                    Confianza {Math.round((meeting.evidence?.aiConfidence ?? 0.72) * 100)}%
                  </span>
                </div>
                <p className="text-sm leading-6 text-muted-foreground">
                  {meeting.evidence?.aiSummary || "Sección preparada para resumen de Tactiq + Claude. Pendiente de integración real."}
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
            </section>

            {mode === "internal" && (
              <>
                <Separator />
                <section className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground">Gestión interna</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Validación final</Label>
                      <Select
                        value={(formData.finalValidation || previewFinal) as FinalValidation}
                        onValueChange={(value) => setFormData({ ...formData, finalValidation: value as FinalValidation })}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(finalValidationLabels).map(([value, label]) => (
                            <SelectItem key={value} value={value}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Estado comercial</Label>
                      <Select
                        value={formData.commercialStatus as CommercialStatus}
                        onValueChange={(value) => setFormData({ ...formData, commercialStatus: value as CommercialStatus })}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(commercialStatusLabels).map(([value, label]) => (
                            <SelectItem key={value} value={value}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
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

            {mode === "client" && (
              <>
                <Separator />
                <section className="space-y-4">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <User className="h-4 w-4 text-amber-600" />
                    Tu validación
                  </h3>
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
                      {meeting.clientDecisionAt && (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Registrado el {format(new Date(meeting.clientDecisionAt), "d MMM yyyy · HH:mm")}
                        </p>
                      )}
                      {meeting.rejectionReason && (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Motivo: {rejectionReasonLabels[meeting.rejectionReason]}
                        </p>
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Motivo si objetas la reunión</Label>
                        <Select value={rejectionReason} onValueChange={(value) => setRejectionReason(value as RejectionReason)}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {Object.entries(rejectionReasonLabels).map(([value, label]) => (
                              <SelectItem key={value} value={value}>{label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
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
          ) : (
            <>
              <Button variant="outline" onClick={requestReview} className="flex-1 gap-1">
                <RotateCcw className="h-4 w-4" />
                Revisar
              </Button>
              <Button variant="outline" onClick={rejectMeeting} className="flex-1 gap-1 text-rose-600">
                <XCircle className="h-4 w-4" />
                Objetar
              </Button>
              <Button onClick={acceptMeeting} className="flex-1 gap-1 bg-violet-600 text-white hover:bg-violet-700">
                <CheckCircle2 className="h-4 w-4" />
                Validar
              </Button>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
