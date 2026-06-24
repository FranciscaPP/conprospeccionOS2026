"use client";

import { useState } from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  Building2,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  History,
  MessageSquare,
  PlayCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useApp } from "@/lib/app-context";
import type { BANTCriteria, Meeting } from "@/lib/types";
import { cpValidationLabels, meetingStatusLabels, rejectionReasonLabels } from "@/lib/types";
import { deriveFinalValidation, getClientDecision, isClientLocked } from "@/lib/meeting-rules";

interface Props {
  meeting: Meeting | null;
  open: boolean;
  onClose: () => void;
}

// Motivos de solicitud de revisión (revisar/ajustar más adelante).
const REVIEW_REASONS = [
  "No coincide con el ICP definido",
  "Falta evidencia de la reunión",
  "Datos del contacto o empresa incorrectos",
  "Necesito más detalle de la justificación",
  "Otro motivo",
];

// Orden y nombres de las variables BANT (como en el mockup).
const BANT_ORDER: { key: BANTCriteria; label: string }[] = [
  { key: "need", label: "Necesidad" },
  { key: "authority", label: "Autoridad" },
  { key: "timeline", label: "Tiempo" },
  { key: "budget", label: "Presupuesto" },
];

function fmtDate(value?: string) {
  if (!value) return "";
  try {
    return format(new Date(value), "d MMM yyyy", { locale: es });
  } catch {
    return "";
  }
}

function fmtDateTime(value?: string) {
  if (!value) return "";
  try {
    return format(new Date(value), "d MMM yyyy · HH:mm", { locale: es });
  } catch {
    return "";
  }
}

function statusDot(status: string) {
  if (status.includes("realiz") || status.includes("complet")) return "#16a34a";
  if (status.includes("reagend") || status.includes("resched")) return "#d97706";
  if (status.includes("cancel")) return "#dc2626";
  if (status.includes("no_show") || status.includes("no asis")) return "#dc2626";
  return "#0284c7";
}

function icpMeta(meeting: Meeting): { cumple: boolean | null; texto: string } {
  if (meeting.cpValidation === "valid_cp") {
    return { cumple: true, texto: "La empresa y el contacto cumplen con el ICP definido para esta campaña." };
  }
  if (meeting.cpValidation === "not_valid_cp" || meeting.cpValidation === "not_completed") {
    return { cumple: false, texto: "La empresa o el contacto no calzan con el ICP definido para esta campaña." };
  }
  return { cumple: null, texto: "Conprospección aún no registró la evaluación de ICP." };
}

// La justificación NO se escribe a mano: se compone desde la evaluación real.
function justificacion(meeting: Meeting): string {
  const n = (meeting.cpBANT || []).length;
  if (meeting.cpValidation === "valid_cp") {
    const bant = n > 0
      ? ` y se detectaron ${n} ${n === 1 ? "variable" : "variables"} BANT durante la conversación`
      : "";
    return `La reunión cumple con el ICP definido${bant}, con evidencia suficiente para considerarla válida.`;
  }
  if (meeting.cpValidation === "not_valid_cp" || meeting.cpValidation === "not_completed") {
    const motivo = meeting.validityReason ? `: ${meeting.validityReason}` : ".";
    return `Conprospección consideró que la reunión no cumple los criterios de validez${motivo}`;
  }
  return "Conprospección aún no emitió su evaluación para esta reunión.";
}

export function ClientMeetingDrawer({ meeting, open, onClose }: Props) {
  const { updateMeeting, refreshMeetings } = useApp();
  const [showReview, setShowReview] = useState(false);
  const [reason, setReason] = useState(REVIEW_REASONS[0]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (!meeting) return null;

  const locked = isClientLocked(meeting);
  const decision = getClientDecision(meeting);
  const icp = icpMeta(meeting);
  const cpBant = meeting.cpBANT || [];
  const ev = meeting.evidence;
  const fullName = [meeting.firstName, meeting.lastName].filter(Boolean).join(" ") || meeting.contact;

  const persist = async (updates: Partial<Meeting>) => {
    try {
      const res = await fetch("/api/internal/meetings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: meeting.id, finalValidation: updates.finalValidation, comment: updates.clientComment }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.error || "No se pudo guardar.");
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar. Reintentá en unos segundos.");
      return false;
    } finally {
      await refreshMeetings();
    }
  };

  const confirmar = async () => {
    setSaving(true);
    setError(null);
    const finalValidation = deriveFinalValidation({ ...meeting, clientValidation: "valid_client", clientDecision: "accepted" });
    const updates: Partial<Meeting> = {
      clientValidation: "valid_client",
      clientDecision: "accepted",
      clientDecisionAt: new Date().toISOString(),
      clientComment: comment,
      finalValidation,
    };
    updateMeeting(meeting.id, updates);
    const ok = await persist(updates);
    setSaving(false);
    if (ok) onClose();
  };

  const solicitarRevision = async () => {
    if (comment.trim().length === 0) {
      setError("El comentario es obligatorio para solicitar una revisión.");
      return;
    }
    setSaving(true);
    setError(null);
    const finalValidation = deriveFinalValidation({ ...meeting, clientValidation: "requires_review", clientDecision: "review_requested" });
    const updates: Partial<Meeting> = {
      clientValidation: "requires_review",
      clientDecision: "review_requested",
      clientDecisionAt: new Date().toISOString(),
      clientComment: `${reason}: ${comment.trim()}`,
      finalValidation,
    };
    updateMeeting(meeting.id, updates);
    const ok = await persist(updates);
    setSaving(false);
    if (ok) onClose();
  };

  // Historial real derivado de los datos que existen hoy.
  const timeline: { title: string; subtitle?: string; date?: string }[] = [
    { title: "Reunión agendada", date: fmtDate(meeting.meetingDate) },
    { title: `Reunión: ${meetingStatusLabels[meeting.meetingStatus]}`, date: fmtDateTime(meeting.meetingDate) },
  ];
  if (meeting.cpValidation !== "waiting_validation") {
    timeline.push({
      title: `Evaluación Conprospección: ${cpValidationLabels[meeting.cpValidation]}`,
      subtitle: meeting.validityReason || undefined,
    });
  }
  if (decision !== "pending") {
    timeline.push({
      title: decision === "accepted" ? "El cliente confirmó la evaluación" : "El cliente solicitó revisión",
      subtitle: meeting.clientComment || undefined,
      date: fmtDateTime(meeting.clientDecisionAt),
    });
  }

  const secHead = (icon: React.ReactNode, n: number, title: string) => (
    <h3 className="flex items-center gap-2 text-[13px] font-semibold text-foreground">
      <span className="text-muted-foreground">{icon}</span>
      <span className="text-muted-foreground">{n}.</span> {title}
    </h3>
  );

  const field = (label: string, value?: React.ReactNode) => (
    <div className="min-w-0">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="min-w-0 break-words text-sm font-medium text-foreground [overflow-wrap:anywhere]">{value || " "}</p>
    </div>
  );

  const link = (href?: string, text?: string) =>
    href ? (
      <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-medium text-[#1d4ed8] underline-offset-2 hover:underline [overflow-wrap:anywhere]">
        {text} <ExternalLink className="h-3 w-3 shrink-0" />
      </a>
    ) : (
      " "
    );

  const evBtn = (icon: React.ReactNode, label: string, href?: string) => (
    <a
      href={href || undefined}
      target={href ? "_blank" : undefined}
      rel="noreferrer"
      aria-disabled={!href}
      className={`inline-flex items-center gap-2 rounded-[10px] border px-4 py-2.5 text-sm font-semibold transition ${
        href ? "border-border bg-white text-foreground hover:bg-muted" : "cursor-not-allowed border-border bg-muted/40 text-muted-foreground"
      }`}
    >
      {icon} {label}
    </a>
  );

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[calc(100vw-32px)] overflow-hidden border-l border-[var(--line)] p-0 shadow-[0_16px_45px_rgba(20,20,20,.16)] sm:max-w-[520px]">
        <SheetHeader className="border-b border-border px-5 py-4">
          <SheetTitle className="text-lg font-semibold leading-tight">Detalle de reunión</SheetTitle>
          <div className="mt-1 flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: statusDot(meeting.meetingStatus) }} />
            <span className="text-[13px] font-medium text-muted-foreground">
              Reunión: {meetingStatusLabels[meeting.meetingStatus]} · {fmtDateTime(meeting.meetingDate)}
            </span>
          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100dvh-9rem)] sm:h-[calc(100vh-9rem)]">
          <div className="space-y-6 px-5 py-5">
            {/* 1. Contacto y empresa */}
            <section className="space-y-3">
              {secHead(<User className="h-4 w-4" />, 1, "Contacto y empresa")}
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                {field("Empresa", meeting.company)}
                {field("País", meeting.country)}
                {field("Contacto", fullName)}
                {field("Website", link(meeting.companyWebsite, meeting.companyWebsite?.replace(/^https?:\/\//, "")))}
                {field("Cargo", meeting.jobTitle)}
                {field("LinkedIn empresa", link(meeting.companyLinkedinUrl, "Ver empresa"))}
                {field("Email", meeting.leadEmail)}
                {field("LinkedIn contacto", link(meeting.contactLinkedinUrl, "Ver perfil"))}
                {field("Teléfono", meeting.leadPhone)}
                {field("Link reunión", link(meeting.meetingUrl, "Unirse a la reunión"))}
              </div>
            </section>

            <div className="border-t border-border" />

            {/* 2. Resumen de reunión */}
            <section className="space-y-2">
              {secHead(<MessageSquare className="h-4 w-4" />, 2, "Resumen de reunión")}
              <p className="text-sm leading-6 text-muted-foreground" style={{ display: "-webkit-box", WebkitLineClamp: 6, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                {meeting.meetingSummary || meeting.preparationInfo || " "}
              </p>
            </section>

            <div className="border-t border-border" />

            {/* 3. Evaluación Conprospección */}
            <section className="space-y-3">
              {secHead(<ShieldCheck className="h-4 w-4" />, 3, "Evaluación Conprospección")}
              <div className="grid gap-3 sm:grid-cols-2">
                {/* ICP */}
                <div className="rounded-[12px] border border-border bg-white p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[.05em] text-muted-foreground">ICP</p>
                  <p className={`mt-1 text-sm font-bold ${icp.cumple === true ? "text-emerald-600" : icp.cumple === false ? "text-red-600" : "text-amber-600"}`}>
                    {icp.cumple === true ? "✓ Cumple" : icp.cumple === false ? "✗ No cumple" : "Pendiente"}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{icp.texto}</p>
                </div>
                {/* BANT */}
                <div className="rounded-[12px] border border-border bg-white p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[.05em] text-muted-foreground">BANT</p>
                  <p className="mt-1 text-xs text-muted-foreground">{cpBant.length} de 4 variables</p>
                  <div className="mt-2 space-y-1.5">
                    {BANT_ORDER.map((b) => {
                      const ok = cpBant.includes(b.key);
                      return (
                        <div key={b.key} className="flex items-center justify-between text-xs text-foreground">
                          <span>{b.label}</span>
                          <span className={ok ? "font-bold text-emerald-600" : "font-bold text-muted-foreground/50"}>{ok ? "✓" : "—"}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
              {/* Justificación (compuesta, separada del BANT) */}
              <div className="rounded-[12px] border border-border bg-white p-3">
                <p className="text-[11px] font-semibold uppercase tracking-[.05em] text-muted-foreground">Justificación</p>
                <p className="mt-1 text-sm leading-6 text-foreground">{justificacion(meeting)}</p>
              </div>
              <div className="rounded-[10px] border border-sky-200 bg-sky-50 px-3.5 py-2.5 text-xs leading-5 text-sky-800">
                Una reunión que no tenga próximos pasos, cierre comercial o fecha de implementación no es indicio de que no sea válida.
              </div>
            </section>

            <div className="border-t border-border" />

            {/* 4. Evidencia */}
            <section className="space-y-3">
              {secHead(<FileText className="h-4 w-4" />, 4, "Evidencia")}
              <div className="flex flex-wrap gap-2">
                {evBtn(<PlayCircle className="h-4 w-4" />, "Ver grabación", ev?.recordingUrl)}
                {evBtn(<FileText className="h-4 w-4" />, "Ver transcripción", ev?.transcriptUrl)}
                {evBtn(<Sparkles className="h-4 w-4" />, "Resumen IA", ev?.aiSummary ? "#" : undefined)}
              </div>
              {ev?.aiSummary && (
                <p className="rounded-[10px] border border-border bg-[#f8f8f6] p-3 text-xs leading-6 text-muted-foreground">
                  {ev.aiSummary}
                </p>
              )}
              <p className="text-[11px] leading-5 text-muted-foreground">
                La IA solo aporta evidencia de la reunión. La validez la determina Conprospección.
              </p>
            </section>

            <div className="border-t border-border" />

            {/* 5. Acción cliente */}
            <section className="space-y-3">
              {secHead(<CheckCircle2 className="h-4 w-4" />, 5, "Acción cliente")}
              {locked ? (
                <div className="rounded-[11px] border border-border bg-[#f8f8f6] p-3 text-sm leading-6 text-muted-foreground">
                  {decision === "accepted"
                    ? "Confirmaste esta reunión."
                    : "Solicitud de revisión enviada — en revisión por Conprospección."}
                </div>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">
                    Confirma la evaluación realizada por Conprospección o solicita revisión.
                  </p>
                  <div className="flex flex-wrap gap-3">
                    <Button
                      onClick={confirmar}
                      disabled={saving}
                      className="gap-2 bg-emerald-600 text-white hover:bg-emerald-700"
                    >
                      <CheckCircle2 className="h-4 w-4" /> Confirmar reunión
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setShowReview((v) => !v)}
                      disabled={saving}
                      className="gap-2 border-orange-400 text-orange-600 hover:bg-orange-50"
                    >
                      <RotateCcw className="h-4 w-4" /> Solicitar revisión
                    </Button>
                  </div>
                  {showReview && (
                    <div className="space-y-2 rounded-[11px] border border-orange-200 bg-orange-50/50 p-3">
                      <Label className="text-xs text-muted-foreground">Motivo</Label>
                      <select
                        aria-label="Motivo de revisión"
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/40"
                      >
                        {REVIEW_REASONS.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                      <Label className="text-xs text-muted-foreground">Comentario (obligatorio)</Label>
                      <Textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} placeholder="Detallá el motivo de la revisión…" />
                      <Button onClick={solicitarRevision} disabled={saving} className="bg-orange-600 text-white hover:bg-orange-700">
                        Enviar solicitud de revisión
                      </Button>
                    </div>
                  )}
                  {error && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
                  )}
                </>
              )}
            </section>

            <div className="border-t border-border" />

            {/* 6. Historial */}
            <section className="space-y-3">
              {secHead(<History className="h-4 w-4" />, 6, "Historial")}
              <ol className="relative space-y-4 border-l border-border pl-5">
                {timeline.map((item, i) => (
                  <li key={i} className="relative">
                    <span className="absolute -left-[23px] top-1 h-2.5 w-2.5 rounded-full border-2 border-white bg-[#333]" />
                    {item.date && <p className="text-[11px] font-medium text-muted-foreground"><Clock className="mr-1 inline h-3 w-3" />{item.date}</p>}
                    <p className="text-sm font-semibold text-foreground">{item.title}</p>
                    {item.subtitle && <p className="text-xs leading-5 text-muted-foreground">{item.subtitle}</p>}
                  </li>
                ))}
              </ol>
            </section>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
