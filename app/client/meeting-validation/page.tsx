"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useApp } from "@/lib/app-context";
import { ACTIVE_CLIENTS, clientSlugFromName, type ActiveClientSlug } from "@/lib/access-control";
import { isClientLocked, MONTHLY_GOAL_BY_CLIENT } from "@/lib/meeting-rules";
import type { FinalValidation, Meeting } from "@/lib/types";

// ─────────────────────────────────────────────────────────────────────────────
// Diseño aprobado (docs/meeting-validation-interactive-flow.html) portado a React
// con datos reales de Supabase (useApp) y guardado real vía PATCH /api/internal/meetings.
// ─────────────────────────────────────────────────────────────────────────────

type DecisionValue = "validar" | "rechazar" | "revision" | "reagendar";
type FilterValue = "all" | "validada" | "no-validada" | "pendiente" | "objetada" | "reagendada";
type TypeValue = "all" | "meeting" | "quote" | "quote-meeting";
type SortKey = "date" | "company" | "person" | "role" | "status";

type Visual = {
  id: string;
  date: string;
  dateIso: string;
  time: string;
  startTime: string;
  company: string;
  initials: string;
  color: string;
  person: string;
  role: string;
  status: string;
  filter: FilterValue;
  prep: string;
  evaluation: string;
  chips: string[];
  transcriptSummary: string;
  evidenceSummary: string;
  commercialStatus: string;
  nextStep: string;
  meetingUrl: string;
  email: string;
  phone: string;
  country: string;
  contactLinkedin: string;
  industry: string;
  companySize: string;
  website: string;
  companyLinkedin: string;
  cpValidation: string;
  evidenceSource: string;
  evidenceUrl: string;
  recordingUrl: string;
  bantDetected: string[];
  isQuote: boolean;
  hasMeeting: boolean;
};

const monthNames = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

function stripPlatformNames(value = "") {
  return String(value)
    .replace(/\bGHL\b/gi, "el CRM")
    .replace(/\bGoHighLevel\b/gi, "el CRM")
    .replace(/\bSNOV\.?IO\b/gi, "la fuente comercial")
    .replace(/\bApollo\.?io\b/gi, "la fuente comercial")
    .replace(/\bApollo\b/gi, "la fuente comercial");
}
function visibleSource(value = "") {
  const text = String(value || "").trim();
  if (!text || /\b(GHL|GoHighLevel|SNOV|Apollo)\b/i.test(text)) return "Pendiente";
  return stripPlatformNames(text);
}
function cleanDisplay(value = "") {
  const text = stripPlatformNames(value).trim();
  if (!text || /^(por completar|sin dato|no data|undefined|null)$/i.test(text)) return "";
  return text;
}
function countryFromPhone(phone = "") {
  const compact = String(phone || "").replace(/\s+/g, "");
  if (compact.startsWith("+51")) return "Peru";
  if (compact.startsWith("+56")) return "Chile";
  return "";
}
function initialsForName(value = "") {
  const words = String(value).replace(/[^A-Za-z0-9 ÁÉÍÓÚÜÑáéíóúüñ]/g, " ").trim().split(/\s+/).filter(Boolean);
  return `${words[0]?.[0] || "?"}${words[1]?.[0] || ""}`.toUpperCase();
}
function formatDateShort(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", timeZone: "America/Santiago" }).format(date).replace(".", "");
}
function formatTimeShort(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("es-CL", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Santiago" }).format(date);
}
function toIso(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
function commercialLabel(value?: string) {
  const map: Record<string, string> = {
    pending_followup: "Propuesta",
    next_step_scheduled: "Reunion agendada",
    requested_proposal: "Propuesta",
    proposal_sent: "Propuesta enviada",
    proposal_followup: "Avance propuesta",
    negotiation: "Avance propuesta",
    no_response: "Sin respuesta",
    client_won: "Cliente ganado",
    client_lost: "Cliente perdido",
    not_commercially_qualified: "Sin respuesta",
  };
  return map[value || ""] || "Propuesta";
}
function visualStatus(m: Meeting): { status: string; filter: FilterValue } {
  if (m.finalValidation === "final_valid") return { status: "Validada", filter: "validada" };
  if (m.finalValidation === "final_not_valid") return { status: "No válida", filter: "no-validada" };
  if (m.finalValidation === "in_dispute") return { status: "Pedir revisión", filter: "objetada" };
  if (m.meetingStatus === "rescheduled" || m.finalValidation === "rescheduled") return { status: "Reagendada", filter: "reagendada" };
  return { status: "Pendiente validación", filter: "pendiente" };
}
function badgeClass(filter: FilterValue) {
  if (filter === "validada") return "valid";
  if (filter === "no-validada") return "rejected";
  if (filter === "objetada") return "review";
  if (filter === "reagendada") return "rescheduled";
  return "pending";
}
function displayCpValidation(v: Visual) {
  if (v.filter === "validada") return "Reunión válida";
  if (v.filter === "no-validada") return "Reunión no válida";
  if (v.filter === "reagendada") return "Reagendar reunión";
  if (v.filter === "objetada") return "Pedir revisión";
  return stripPlatformNames(v.cpValidation || "Pendiente");
}
function cpBadgeClass(label: string) {
  if (label === "Reunión válida") return "cp-mini-badge";
  if (label === "Reagendar reunión") return "cp-mini-badge reschedule";
  return "cp-mini-badge invalid";
}
function decisionFromFilter(filter: FilterValue): DecisionValue {
  if (filter === "validada") return "validar";
  if (filter === "no-validada") return "rechazar";
  if (filter === "reagendada") return "reagendar";
  if (filter === "objetada") return "revision";
  return "validar";
}
const DECISION_TO_FINAL: Record<DecisionValue, FinalValidation> = {
  validar: "final_valid",
  rechazar: "final_not_valid",
  revision: "in_dispute",
  reagendar: "rescheduled",
};

function toVisual(m: Meeting): Visual {
  const summaryRaw = `${m.meetingSummary || ""} ${m.preparationInfo || ""}`;
  const isQuote = String(m.id || "").startsWith("quote-") || /solo cotizacion|solicitud directa de cotizacion/i.test(summaryRaw);
  const hasMeeting = Boolean(m.meetingUrl) || /reuni/i.test(summaryRaw);
  const summary = stripPlatformNames(m.meetingSummary || m.preparationInfo || "Pendiente");
  const prep = stripPlatformNames(m.preparationInfo || m.meetingSummary || "Pendiente");
  const { status, filter } = visualStatus(m);
  const bant = (m.cpBANT || []).map((b) => String(b));
  return {
    id: String(m.id),
    date: formatDateShort(m.meetingDate),
    dateIso: String(m.meetingDate || "").slice(0, 10),
    time: isQuote ? "Cotizar" : formatTimeShort(m.meetingDate),
    startTime: m.meetingDate,
    company: m.company || "Sin empresa",
    initials: initialsForName(m.company),
    color: isQuote ? "#6d55a3" : "#0e9f6e",
    person: m.contact || [m.firstName, m.lastName].filter(Boolean).join(" ") || "Contacto sin nombre",
    role: m.jobTitle || "Contacto comercial",
    status,
    filter,
    prep,
    evaluation: isQuote
      ? "Solicitud directa de cotización. Para GBS puede contar como oportunidad equivalente a reunión si el cliente la valida."
      : summary,
    chips: isQuote ? ["Solo cotización", "Cuenta para meta", "Seguimiento comercial"] : ["Reunión realizada", `BANT ${bant.length}/4`, "ICP acordado"],
    transcriptSummary: isQuote
      ? "Sin grabación ni transcripción porque no hubo reunión. La evidencia comercial es la solicitud directa de cotización."
      : summary,
    evidenceSummary: isQuote
      ? "Solicitud comercial directa cargada desde workflow. El cliente valida si cuenta para meta y se activa seguimiento de cotización."
      : summary,
    commercialStatus: commercialLabel(m.commercialStatus),
    nextStep: stripPlatformNames(m.nextStep || (isQuote ? "Contactar para levantar requerimiento y enviar cotización." : "Validar evidencia y completar evaluación comercial.")),
    meetingUrl: m.meetingUrl || "",
    email: m.leadEmail || "",
    phone: m.leadPhone || "",
    country: m.country || "",
    contactLinkedin: m.contactLinkedinUrl || "",
    industry: m.leadIndustry || "",
    companySize: "",
    website: m.companyWebsite || "",
    companyLinkedin: m.companyLinkedinUrl || "",
    cpValidation: "Reunión válida",
    evidenceSource: isQuote ? "Solicitud comercial" : "Pendiente",
    evidenceUrl: m.evidence?.transcriptUrl || "",
    recordingUrl: m.evidence?.recordingUrl || "",
    bantDetected: bant,
    isQuote,
    hasMeeting,
  };
}
function meetingType(v: Visual): Exclude<TypeValue, "all"> {
  if (v.isQuote && v.hasMeeting) return "quote-meeting";
  if (v.isQuote) return "quote";
  return "meeting";
}
function displayCountry(v: Visual) {
  return countryFromPhone(v.phone) || v.country || "Por confirmar";
}

function resolveClientFromParam(meetings: Meeting[], clientParam: string | null) {
  const requestedSlug = clientSlugFromName(clientParam || "") ?? "gbs";
  return (
    meetings.find((meeting) => clientSlugFromName(meeting.client) === requestedSlug)?.client ||
    ACTIVE_CLIENTS.find((client) => client.slug === requestedSlug)?.displayName ||
    "GBS LOGISTICS"
  );
}

export default function MeetingValidationPage() {
  const { role, meetings, updateMeeting, refreshMeetings, selectedMeetingId, setSelectedMeetingId } = useApp();
  const isInternal = role === "internal";

  const [queryClient, setQueryClient] = useState<string | null>(null);
  const [queryMeetingId, setQueryMeetingId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<FilterValue>("all");
  const [typeFilter, setTypeFilter] = useState<TypeValue>("all");
  const [sortState, setSortState] = useState<{ key: SortKey; direction: "asc" | "desc" }>({ key: "date", direction: "asc" });
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({ start: "", end: "" });
  const [draftRange, setDraftRange] = useState<{ start: string; end: string }>({ start: "", end: "" });
  const [calendar, setCalendar] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  const [selected, setSelected] = useState<Visual | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"decision" | "evidence" | "data" | "commercial">("decision");
  const [decision, setDecision] = useState<DecisionValue>("validar");
  const [comment, setComment] = useState("");
  const [commStatus, setCommStatus] = useState("Propuesta");
  const [nextStepInput, setNextStepInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; show: boolean }>({ msg: "", show: false });

  const dateDetailsRef = useRef<HTMLDetailsElement>(null);
  const statusDetailsRef = useRef<HTMLDetailsElement>(null);
  const countryDetailsRef = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setQueryClient(params.get("client"));
    setQueryMeetingId(params.get("meeting"));
  }, []);

  const requestedMeetingId = queryMeetingId || selectedMeetingId;
  const requestedMeeting = useMemo(
    () => meetings.find((m) => m.id === requestedMeetingId) || null,
    [meetings, requestedMeetingId]
  );
  const selectedClient = requestedMeeting?.client || resolveClientFromParam(meetings, queryClient);

  const clientMeetings = useMemo(
    () => meetings.filter((m) => m.client === selectedClient),
    [meetings, selectedClient]
  );
  const goal = MONTHLY_GOAL_BY_CLIENT[selectedClient] ?? 10;

  const visuals = useMemo(() => clientMeetings.map(toVisual), [clientMeetings]);
  const meetingById = useMemo(() => new Map(clientMeetings.map((m) => [String(m.id), m])), [clientMeetings]);

  const countries = useMemo(
    () => [...new Set(visuals.map((v) => displayCountry(v)).filter(Boolean))].sort(),
    [visuals]
  );
  const [countryFilter, setCountryFilter] = useState("all");

  const inDateRange = (v: Visual) => {
    if (!dateRange.start || !dateRange.end) return true;
    return v.dateIso >= dateRange.start && v.dateIso <= dateRange.end;
  };

  const baseFiltered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return visuals.filter((v) => {
      const searchable = `${v.company} ${v.person} ${v.role} ${v.email} ${v.phone} ${displayCountry(v)} ${v.website}`.toLowerCase();
      const matchesSearch = !q || searchable.includes(q);
      const matchesType = typeFilter === "all" || meetingType(v) === typeFilter;
      const matchesCountry = countryFilter === "all" || displayCountry(v) === countryFilter;
      return matchesSearch && matchesType && matchesCountry && inDateRange(v);
    });
  }, [visuals, search, typeFilter, countryFilter, dateRange]);

  const stats = useMemo(() => {
    const c = {
      all: baseFiltered.length,
      validada: baseFiltered.filter((v) => v.filter === "validada").length,
      "no-validada": baseFiltered.filter((v) => v.filter === "no-validada").length,
      pendiente: baseFiltered.filter((v) => v.filter === "pendiente").length,
      objetada: baseFiltered.filter((v) => v.filter === "objetada").length,
      reagendada: baseFiltered.filter((v) => v.filter === "reagendada").length,
    };
    return c;
  }, [baseFiltered]);

  const typeCounts = useMemo(() => {
    const q = search.trim().toLowerCase();
    const scoped = visuals.filter((v) => {
      const searchable = `${v.company} ${v.person} ${v.role} ${v.email} ${v.phone} ${displayCountry(v)} ${v.website}`.toLowerCase();
      return (!q || searchable.includes(q)) && inDateRange(v);
    });
    return {
      all: scoped.length,
      meeting: scoped.filter((v) => meetingType(v) === "meeting").length,
      quote: scoped.filter((v) => meetingType(v) === "quote").length,
      "quote-meeting": scoped.filter((v) => meetingType(v) === "quote-meeting").length,
    };
  }, [visuals, search, dateRange]);

  const goalValid = stats.validada;
  const goalPct = goal ? Math.round((goalValid / goal) * 100) : 0;

  const rows = useMemo(() => {
    const filtered = statusFilter === "all" ? baseFiltered : baseFiltered.filter((v) => v.filter === statusFilter);
    const dir = sortState.direction === "asc" ? 1 : -1;
    const sortValue = (v: Visual) => {
      if (sortState.key === "date") return v.startTime || v.dateIso || "";
      if (sortState.key === "status") return v.status || "";
      if (sortState.key === "company") return v.company || "";
      if (sortState.key === "person") return v.person || "";
      return v.role || "";
    };
    return [...filtered].sort(
      (a, b) => String(sortValue(a)).localeCompare(String(sortValue(b)), "es", { numeric: true, sensitivity: "base" }) * dir
    );
  }, [baseFiltered, statusFilter, sortState]);

  const showToast = (msg: string) => {
    setToast({ msg, show: true });
    setTimeout(() => setToast((t) => ({ ...t, show: false })), 1800);
  };

  const openMeeting = (v: Visual) => {
    setSelected(v);
    setDecision(decisionFromFilter(v.filter));
    setComment("");
    setCommStatus(v.commercialStatus);
    setNextStepInput(v.nextStep);
    setActiveTab("decision");
    setSaveError(null);
    setPanelOpen(true);
  };
  const closePanel = () => {
    setPanelOpen(false);
    setSelectedMeetingId(null);
  };

  useEffect(() => {
    if (!requestedMeeting) return;
    openMeeting(toVisual(requestedMeeting));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedMeetingId, clientMeetings.length]);

  const locked = selected ? isClientLocked(meetingById.get(selected.id) as Meeting) : false;

  const saveDecision = async () => {
    if (!selected) return;
    setSaving(true);
    setSaveError(null);
    const finalValidation = DECISION_TO_FINAL[decision];
    try {
      const response = await fetch("/api/internal/meetings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: selected.id, finalValidation }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "No se pudo guardar la validación.");
      updateMeeting(selected.id, { finalValidation, clientComment: comment });
      await refreshMeetings();
      showToast("Decisión guardada");
      closePanel();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "No se pudo guardar. Reintenta en unos segundos.");
    } finally {
      setSaving(false);
    }
  };

  const saveCommercial = () => {
    if (!selected) return;
    updateMeeting(selected.id, { nextStep: nextStepInput });
    showToast("Avance comercial actualizado");
    closePanel();
  };

  const switchClient = (slug: ActiveClientSlug) => {
    setQueryMeetingId(null);
    setSelectedMeetingId(null);
    setQueryClient(slug);
    setSearch("");
    setStatusFilter("all");
    setTypeFilter("all");
    setCountryFilter("all");
    window.history.replaceState(null, "", `/client/meeting-validation?client=${slug}`);
  };

  // Calendar helpers
  const calendarCells = useMemo(() => {
    const first = new Date(calendar.year, calendar.month, 1);
    const start = new Date(first);
    start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
    const cells: { iso: string; day: number; inMonth: boolean }[] = [];
    for (let i = 0; i < 42; i++) {
      const day = new Date(start);
      day.setDate(start.getDate() + i);
      cells.push({ iso: toIso(day), day: day.getDate(), inMonth: day.getMonth() === calendar.month });
    }
    return cells;
  }, [calendar]);

  const selectCalendarDate = (iso: string) => {
    setDraftRange((prev) => {
      if (!prev.start || (prev.start && prev.end)) return { start: iso, end: "" };
      if (iso < prev.start) return { start: iso, end: prev.start };
      return { ...prev, end: iso };
    });
  };

  const formatRangeLabel = (range = dateRange) => {
    if (!range.start || !range.end) return "Fecha: Todas";
    const start = new Date(`${range.start}T00:00:00`);
    const end = new Date(`${range.end}T00:00:00`);
    const lastDay = new Date(end.getFullYear(), end.getMonth() + 1, 0).getDate();
    if (start.getDate() === 1 && end.getDate() === lastDay && start.getMonth() === end.getMonth()) {
      return `Fecha: ${monthNames[start.getMonth()]} ${start.getFullYear()}`;
    }
    const sameMonth = start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear();
    return sameMonth
      ? `Fecha: ${start.getDate()}-${end.getDate()} ${monthNames[start.getMonth()]}`
      : `Fecha: ${start.getDate()} ${monthNames[start.getMonth()]}-${end.getDate()} ${monthNames[end.getMonth()]}`;
  };

  const statusLabel: Record<FilterValue, string> = {
    all: "Estado: Todos",
    pendiente: "Pendiente validación",
    validada: "Validada",
    "no-validada": "No validada",
    objetada: "Pedir revisión",
    reagendada: "Reagendar",
  };

  const statCards: { key: FilterValue; label: string }[] = [
    { key: "all", label: "Total generadas" },
    { key: "validada", label: "Validadas" },
    { key: "no-validada", label: "No validadas" },
    { key: "pendiente", label: "Pendiente validación" },
    { key: "objetada", label: "Pedir revisión" },
    { key: "reagendada", label: "Reagendar" },
  ];

  const typeButtons: { key: TypeValue; label: string }[] = [
    { key: "all", label: "Todos" },
    { key: "meeting", label: "Reunión" },
    { key: "quote", label: "Solo cotización" },
    { key: "quote-meeting", label: "Cotización + reunión" },
  ];

  return (
    <div id="avroot" className="av">
      <style>{AV_CSS}</style>

      <header className="topbar">
        <div>
          <h1>Avance reuniones</h1>
          <p>{selectedClient}</p>
        </div>
        <div className="top-actions">
          {isInternal && (
            <div className="client-switch">
              {ACTIVE_CLIENTS.map((client) => (
                <button
                  key={client.slug}
                  type="button"
                  className={clientSlugFromName(selectedClient) === client.slug ? "active" : ""}
                  onClick={() => switchClient(client.slug)}
                >
                  {client.displayName}
                </button>
              ))}
            </div>
          )}
          {stats.pendiente > 0 && (
            <div className="notice">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
              {stats.pendiente} {stats.pendiente === 1 ? "requiere" : "requieren"} validación
            </div>
          )}
        </div>
      </header>

      <section className="work">
        <div className="left">
          <div className="compact-stats">
            {statCards.map((card) => {
              const count = stats[card.key];
              const pct = stats.all ? Math.round((count / stats.all) * 100) : 0;
              const active = card.key === "all" ? statusFilter === "all" : statusFilter === card.key;
              return (
                <button
                  key={card.key}
                  type="button"
                  className={`stat${active ? " active" : ""}`}
                  data-filter={card.key}
                  onClick={() => setStatusFilter(card.key)}
                >
                  <small>{card.label}</small>
                  <strong>{count}<span>{card.key === "all" ? "100%" : `${pct}%`}</span></strong>
                </button>
              );
            })}
          </div>

          <section className="goal">
            <div className="goal-row"><span>Avance meta</span><strong>{goalValid}/{goal} · {goalPct}%</strong></div>
            <div className="goal-bar"><i style={{ width: `${Math.min(goalPct, 100)}%` }} /></div>
          </section>

          <section className="rules">
            <b>Regla de validación</b>
            <span><i className="check">✓</i>La reunión se realizó</span>
            <span><i className="check">✓</i>2 variables BANT</span>
            <span><i className="check">✓</i>Dentro del ICP acordado</span>
          </section>

          <div className="type-segment">
            <span>Tipo</span>
            {typeButtons.map((t) => (
              <button
                key={t.key}
                type="button"
                className={typeFilter === t.key ? "active" : ""}
                data-type-filter={t.key}
                onClick={() => setTypeFilter(t.key)}
              >
                {t.label} <strong>{typeCounts[t.key]}</strong>
              </button>
            ))}
          </div>

          <div className="filters">
            <label className="field">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
              <input
                placeholder="Buscar empresa, contacto, cargo, correo, teléfono o país"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>

            <details className="filter-menu" ref={statusDetailsRef}>
              <summary>{statusLabel[statusFilter]}</summary>
              <div>
                {(Object.keys(statusLabel) as FilterValue[]).map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => {
                      setStatusFilter(key);
                      if (statusDetailsRef.current) statusDetailsRef.current.open = false;
                    }}
                  >
                    {statusLabel[key]}
                  </button>
                ))}
              </div>
            </details>

            <details className="filter-menu date-menu" ref={dateDetailsRef}>
              <summary>{formatRangeLabel()}</summary>
              <div>
                <div className="date-controls">
                  <select aria-label="Mes" value={calendar.month} onChange={(e) => setCalendar((c) => ({ ...c, month: Number(e.target.value) }))}>
                    {monthNames.map((name, idx) => (<option key={name} value={idx}>{name}</option>))}
                  </select>
                  <select aria-label="Año" value={calendar.year} onChange={(e) => setCalendar((c) => ({ ...c, year: Number(e.target.value) }))}>
                    {[2025, 2026, 2027].map((y) => (<option key={y} value={y}>{y}</option>))}
                  </select>
                </div>
                <div className="calendar-grid">
                  {["L", "M", "M", "J", "V", "S", "D"].map((l, i) => (<span key={`${l}-${i}`}>{l}</span>))}
                  {calendarCells.map((cell) => {
                    const inRange = draftRange.start && draftRange.end && cell.iso >= draftRange.start && cell.iso <= draftRange.end;
                    const isEdge = cell.iso === draftRange.start || cell.iso === draftRange.end;
                    return (
                      <button
                        key={cell.iso}
                        type="button"
                        className={`${cell.inMonth ? "" : "out"} ${inRange ? "in-range" : ""} ${isEdge ? "range-edge" : ""}`.trim()}
                        onClick={() => selectCalendarDate(cell.iso)}
                      >
                        {cell.day}
                      </button>
                    );
                  })}
                </div>
                <div className="date-actions">
                  <button
                    type="button"
                    onClick={() => {
                      const start = new Date(calendar.year, calendar.month, 1);
                      const end = new Date(calendar.year, calendar.month + 1, 0);
                      setDraftRange({ start: toIso(start), end: toIso(end) });
                    }}
                  >
                    Todo el mes
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setDraftRange({ start: "", end: "" });
                      setDateRange({ start: "", end: "" });
                      if (dateDetailsRef.current) dateDetailsRef.current.open = false;
                    }}
                  >
                    Limpiar
                  </button>
                  <button
                    type="button"
                    className="apply"
                    onClick={() => {
                      setDateRange({ start: draftRange.start, end: draftRange.end || draftRange.start });
                      if (dateDetailsRef.current) dateDetailsRef.current.open = false;
                    }}
                  >
                    Aplicar
                  </button>
                </div>
              </div>
            </details>

            <details className="filter-menu" ref={countryDetailsRef}>
              <summary>{countryFilter === "all" ? "País: Todos" : `País: ${countryFilter}`}</summary>
              <div>
                <button type="button" onClick={() => { setCountryFilter("all"); if (countryDetailsRef.current) countryDetailsRef.current.open = false; }}>Todos</button>
                {countries.map((c) => (
                  <button key={c} type="button" onClick={() => { setCountryFilter(c); if (countryDetailsRef.current) countryDetailsRef.current.open = false; }}>{c}</button>
                ))}
              </div>
            </details>
          </div>

          <section className="table-card">
            <div className="table-head"><span><b>Reuniones para validar</b></span><span className="muted">{rows.length} de {clientMeetings.length}</span></div>
            <table>
              <thead>
                <tr>
                  {([["date", "Fecha"], ["company", "Empresa"], ["person", "Contacto"], ["role", "Cargo"], ["status", "Estado"]] as [SortKey, string][]).map(([key, label]) => {
                    const active = sortState.key === key;
                    return (
                      <th key={key}>
                        <button
                          type="button"
                          className={`sort-head${active ? " active" : ""}${active && sortState.direction === "asc" ? " asc" : ""}${active && sortState.direction === "desc" ? " desc" : ""}`}
                          onClick={() =>
                            setSortState((s) => (s.key === key ? { key, direction: s.direction === "asc" ? "desc" : "asc" } : { key, direction: "asc" }))
                          }
                        >
                          {label}
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr><td colSpan={5} className="muted">No hay reuniones con este filtro.</td></tr>
                )}
                {rows.map((v) => (
                  <tr key={v.id} className={selected?.id === v.id ? "selected" : ""} onClick={() => openMeeting(v)} style={{ cursor: "pointer" }}>
                    <td className="date">
                      <b>{v.date}</b>
                      <span>{v.time === "Cotizar" ? <i className="quote-pill">Cotizar</i> : v.time}</span>
                    </td>
                    <td>
                      <div className="company-cell">
                        <span className="company"><span className="co" style={{ background: v.color }}>{v.initials}</span>{v.company}</span>
                        {cleanDisplay(v.industry) && <span className="company-industry">{cleanDisplay(v.industry)}</span>}
                      </div>
                    </td>
                    <td className="contact-cell"><b>{v.person}</b><span className="country-mini">{displayCountry(v)}</span></td>
                    <td className="muted">{v.role}</td>
                    <td>
                      <span className={`badge ${badgeClass(v.filter)}`}><span>{v.status}</span></span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>

        <div className={`backdrop${panelOpen ? " show" : ""}`} onClick={closePanel} />

        {selected && (
          <aside className={`panel${panelOpen ? " show" : ""}`} aria-live="polite">
            <div className="panel-header">
              <div className="panel-title">
                <h2>{selected.company}</h2>
                <p>{selected.person} · {selected.role}</p>
                <span className={cpBadgeClass(displayCpValidation(selected))}>{displayCpValidation(selected)}</span>
              </div>
              <button className="close" onClick={closePanel} aria-label="Cerrar detalle">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4}><path d="M18 6 6 18M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="panel-tabs">
              {(["decision", "evidence", "data", "commercial"] as const).map((tab) => (
                <button key={tab} type="button" className={`tab${activeTab === tab ? " active" : ""}`} onClick={() => setActiveTab(tab)}>
                  {tab === "decision" ? "Decisión" : tab === "evidence" ? "Evidencia" : tab === "data" ? "Datos" : "Comercial"}
                </button>
              ))}
            </div>

            <div className="panel-body">
              {activeTab === "decision" && (
                <section className="tabs-content active">
                  <div className="validation-flow">
                    <span>Conprospección revisa evidencia, ICP, variables BANT y grabación.</span>
                    <span>Cliente y Conprospección evalúan juntos si la reunión cuenta para la meta y dejan claro el porqué.</span>
                  </div>
                  {locked ? (
                    <div className="note">Esta validación ya quedó registrada. Solo Conprospección puede reabrirla internamente si corresponde.</div>
                  ) : (
                    <>
                      <div className="section">
                        <h3>Tu validación</h3>
                        <div className="choice">
                          {([["validar", "Validar"], ["rechazar", "No validar"], ["revision", "Pedir revisión"], ["reagendar", "Reagendar"]] as [DecisionValue, string][]).map(([val, label]) => (
                            <label key={val} data-choice={val}>
                              <input type="radio" name="decision" value={val} checked={decision === val} onChange={() => { setDecision(val); if (val === "revision") setActiveTab("evidence"); }} />
                              {label}
                            </label>
                          ))}
                        </div>
                      </div>
                      <textarea placeholder="Comentario opcional" value={comment} onChange={(e) => setComment(e.target.value)} />
                      {saveError && <div className="note" style={{ color: "var(--bad-ink)" }}>{saveError}</div>}
                      <div className="footer-actions">
                        <button className="btn light" onClick={closePanel} disabled={saving}>Cancelar</button>
                        <button className="btn" onClick={saveDecision} disabled={saving}>{saving ? "Guardando…" : "Guardar"}</button>
                      </div>
                    </>
                  )}
                </section>
              )}

              {activeTab === "evidence" && (
                <section className="tabs-content active">
                  <div className="section">
                    <h3>Evidencia revisada</h3>
                    <div className="note">{selected.evaluation}</div>
                    <div className="chips">{selected.chips.map((c, i) => (<span key={i} className="chip ok">{c}</span>))}</div>
                  </div>
                  <div className="section">
                    <h3>Grabación de la reunión</h3>
                    <div className="media-card">
                      <div className="player">
                        <button
                          className="play"
                          aria-label="Reproducir grabación"
                          onClick={() => { if (selected.recordingUrl) window.open(selected.recordingUrl, "_blank", "noopener,noreferrer"); else showToast("Sin grabación disponible aún"); }}
                        >
                          <svg viewBox="0 0 24 24" width="25" height="25" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
                        </button>
                      </div>
                      <div className="timeline"><span>00:00</span><div className="line"><i /></div><span>--:--</span></div>
                    </div>
                    <div className="evidence-links">
                      <div><small>Fuente</small><span>{visibleSource(selected.evidenceSource)}</span></div>
                      <div><small>Transcripción</small>{selected.evidenceUrl ? <a href={selected.evidenceUrl} target="_blank" rel="noreferrer">Abrir transcripción</a> : <span>Sin link</span>}</div>
                      <div><small>Grabación</small>{selected.recordingUrl ? <a href={selected.recordingUrl} target="_blank" rel="noreferrer">Abrir grabación</a> : <span>Sin link</span>}</div>
                      <div><small>BANT detectado</small><span>{selected.bantDetected.length ? selected.bantDetected.join(", ") : "Pendiente"}</span></div>
                    </div>
                  </div>
                  <div className="section">
                    <h3>Resumen y transcripción</h3>
                    <div className="note">{selected.transcriptSummary}</div>
                  </div>
                  <div className="section">
                    <h3>Variables y próximos pasos</h3>
                    <div className="note">{selected.evidenceSummary}</div>
                  </div>
                </section>
              )}

              {activeTab === "data" && (
                <section className="tabs-content active">
                  <div className="section">
                    <h3>Datos de reunión</h3>
                    <div className="kv">
                      <div><small>Fecha</small><b>{selected.date} · {selected.time}</b></div>
                      <div><small>Link reunión</small><b>{selected.meetingUrl || "Sin dato"}</b></div>
                    </div>
                  </div>
                  <div className="section">
                    <h3>Datos del contacto</h3>
                    <div className="kv">
                      <div><small>Contacto</small><b>{selected.person}</b></div>
                      <div><small>Cargo</small><b>{selected.role}</b></div>
                      <div><small>Email</small><b>{selected.email || "Sin dato"}</b></div>
                      <div><small>Teléfono</small><b>{selected.phone || "Sin dato"}</b></div>
                      <div><small>País</small><b>{displayCountry(selected)}</b></div>
                      <div><small>LinkedIn contacto</small><b>{cleanDisplay(selected.contactLinkedin) || "Sin dato"}</b></div>
                    </div>
                  </div>
                  <div className="section">
                    <h3>Datos de empresa</h3>
                    <div className="kv">
                      <div><small>Industria</small><b>{cleanDisplay(selected.industry) || "Sin dato"}</b></div>
                      <div><small>Tamaño empresa</small><b>{cleanDisplay(selected.companySize) || "Sin dato"}</b></div>
                      <div><small>Sitio web</small><b>{cleanDisplay(selected.website) || "Sin dato"}</b></div>
                      <div><small>LinkedIn empresa</small><b>{cleanDisplay(selected.companyLinkedin) || "Sin dato"}</b></div>
                    </div>
                  </div>
                  <div className="section">
                    <h3>Preparación</h3>
                    <div className="note">{selected.prep}</div>
                  </div>
                </section>
              )}

              {activeTab === "commercial" && (
                <section className="tabs-content active">
                  <div className="section">
                    <h3>Actualizar seguimiento comercial</h3>
                    <label className="field">
                      <select value={commStatus} onChange={(e) => setCommStatus(e.target.value)}>
                        {["Propuesta", "Reunión agendada", "Propuesta enviada", "Avance propuesta", "Cliente ganado", "Cliente perdido", "Sin respuesta", "Contactar a futuro"].map((o) => (
                          <option key={o}>{o}</option>
                        ))}
                      </select>
                    </label>
                    <textarea placeholder="Próximo paso comercial" value={nextStepInput} onChange={(e) => setNextStepInput(e.target.value)} />
                    <button className="btn" onClick={saveCommercial}>Guardar</button>
                  </div>
                  <div className="section">
                    <h3>Último seguimiento</h3>
                    <div className="note">{selected.nextStep}</div>
                  </div>
                </section>
              )}
            </div>
          </aside>
        )}
      </section>

      <div className={`toast${toast.show ? " show" : ""}`}>{toast.msg}</div>
    </div>
  );
}

const AV_CSS = `
#avroot{--gold:#ffd700;--carbon-2:#333;--canvas:#f6f6f4;--card:#fff;--ink:#151515;--ink-2:#5c5e59;--ink-3:#8b8d87;--line:#e2e2dc;--line-2:#d5d6d0;--ok:#0e9f6e;--ok-bg:#e7f6f0;--ok-ink:#0a6e4d;--warn:#b06a00;--warn-bg:#fbf1df;--warn-ink:#8a5300;--bad:#c0362c;--bad-bg:#fbeae8;--bad-ink:#962a22;--rev:#cf7320;--rev-bg:#fdf0e6;--rev-ink:#9a5418;--shadow:0 1px 2px rgba(20,20,20,.05),0 1px 3px rgba(20,20,20,.04);--shadow-panel:0 16px 45px rgba(20,20,20,.16);background:var(--canvas);color:var(--ink);min-height:100%;display:flex;flex-direction:column;font-family:Inter,"Segoe UI",Roboto,Arial,sans-serif}
#avroot *{box-sizing:border-box}
#avroot button{cursor:pointer;font:inherit}
#avroot .topbar{min-height:82px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:14px 28px;gap:16px;position:sticky;top:0;z-index:12}
#avroot .topbar h1{font-size:24px;margin:0 0 4px;letter-spacing:-.02em}
#avroot .topbar p{margin:0;color:var(--ink-2);font-size:14px}
#avroot .top-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}
#avroot .client-switch{display:flex;gap:6px;flex-wrap:wrap}
#avroot .client-switch button{height:34px;border:1px solid var(--line-2);background:#fff;border-radius:9px;padding:0 11px;font-size:12px;font-weight:600;color:var(--ink-2)}
#avroot .client-switch button.active{background:#f0f0ee;border-color:var(--carbon-2);color:var(--carbon-2)}
#avroot .notice{display:inline-flex;align-items:center;gap:8px;border:1px solid #edcf7b;background:#fff9df;color:#8a5d00;border-radius:11px;padding:10px 13px;font-weight:600;white-space:nowrap}
#avroot .notice svg{width:18px;height:18px}
#avroot .work{padding:22px 28px 30px;display:block;min-width:0}
#avroot .left{display:grid;gap:15px;min-width:0}
#avroot .compact-stats{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}
#avroot .stat{border:1px solid var(--line);border-radius:11px;padding:13px;box-shadow:var(--shadow);text-align:left;color:var(--ink);transition:.15s}
#avroot .stat small{display:block;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);font-size:10px;font-weight:500}
#avroot .stat strong{display:flex;align-items:baseline;gap:7px;margin-top:7px;font-size:25px;line-height:1;font-weight:600}
#avroot .stat strong span{font-size:12px;color:var(--ink-2);font-weight:500}
#avroot .stat[data-filter="all"]{background:#fff7b8;border-color:#d7bd18}
#avroot .stat[data-filter="validada"]{background:#cfecde;border-color:#78c5a3}
#avroot .stat[data-filter="no-validada"]{background:#f5d8d4;border-color:#dc958d}
#avroot .stat[data-filter="pendiente"]{background:#f8e3bd;border-color:#dfa94d}
#avroot .stat[data-filter="objetada"]{background:#f6d8bf;border-color:#dc9c63}
#avroot .stat[data-filter="reagendada"]{background:#dedfd9;border-color:#aeb1a8}
#avroot .stat.active{outline:2px solid rgba(43,43,43,.45);outline-offset:2px}
#avroot .stat:hover{transform:translateY(-1px)}
#avroot .goal{background:#fffef4;border:1px solid #e2d37a;border-left:4px solid var(--gold);border-radius:12px;padding:12px 14px;box-shadow:var(--shadow)}
#avroot .goal-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:9px}
#avroot .goal-row span{color:#3f403c;font-size:13px}
#avroot .goal-row strong{font-size:16px;font-weight:600;color:#fff;background:#3f403c;border-radius:9px;padding:6px 10px}
#avroot .goal-bar{height:7px;background:#ebe8d0;border-radius:99px;overflow:hidden}
#avroot .goal-bar i{display:block;height:100%;background:linear-gradient(90deg,#ffd700,#c8a900)}
#avroot .rules{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px 15px;box-shadow:var(--shadow);display:flex;align-items:center;gap:18px;flex-wrap:wrap}
#avroot .rules b{font-size:14px}
#avroot .rules span{display:inline-flex;align-items:center;gap:7px;color:var(--ink-2);font-size:13px}
#avroot .check{width:17px;height:17px;border-radius:50%;border:2px solid var(--ok);color:var(--ok);display:grid;place-items:center;font-size:11px;font-weight:900}
#avroot .type-segment{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
#avroot .type-segment>span{font-size:12px;color:#6a6d67;margin-right:4px}
#avroot .type-segment button{height:32px;border:1px solid var(--line-2);background:#fff;color:#4e504b;border-radius:999px;padding:0 10px;font-size:12px;font-weight:500}
#avroot .type-segment button strong{font-weight:600;margin-left:6px;color:#262724}
#avroot .type-segment button.active{background:#fff7b8;border-color:#d7bd18;color:#3f3300}
#avroot .type-segment button[data-type-filter="quote"].active{background:#eee8fb;border-color:#c9b7ea;color:#56358d}
#avroot .filters{display:grid;grid-template-columns:minmax(260px,1fr) 200px 230px 150px;gap:10px}
#avroot .field{height:40px;border:1px solid var(--line-2);background:#fff;border-radius:10px;padding:0 12px;display:flex;align-items:center;gap:8px;color:#3f403c}
#avroot .field svg{width:17px;height:17px}
#avroot .field input,#avroot .field select{border:0;outline:0;background:transparent;min-width:0;width:100%;color:var(--ink);font-size:14px}
#avroot .filter-menu{position:relative}
#avroot .filter-menu summary{height:40px;border:1px solid var(--line-2);background:#fff;border-radius:10px;padding:0 12px;display:flex;align-items:center;justify-content:space-between;gap:8px;color:#3f403c;list-style:none;cursor:pointer;font-size:14px}
#avroot .filter-menu summary::-webkit-details-marker{display:none}
#avroot .filter-menu summary:after{content:"⌄";color:var(--ink-2);font-size:15px}
#avroot .filter-menu[open] summary{border-color:#d1bd50;box-shadow:0 0 0 2px rgba(255,215,0,.2)}
#avroot .filter-menu>div{position:absolute;z-index:50;top:44px;left:0;right:0;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow-panel);padding:6px}
#avroot .filter-menu button{display:block;width:100%;border:0;background:#fff;color:var(--ink);text-align:left;border-radius:8px;padding:9px 10px;font-size:13px}
#avroot .filter-menu button:hover{background:#f6f6f4}
#avroot .date-menu>div{right:auto;width:320px;padding:12px}
#avroot .date-controls{display:grid;grid-template-columns:1fr 88px;gap:8px;margin-bottom:10px}
#avroot .date-controls select{height:36px;border:1px solid var(--line-2);border-radius:9px;background:#fff;padding:0 9px;color:var(--ink)}
#avroot .calendar-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}
#avroot .calendar-grid span{height:24px;display:grid;place-items:center;color:var(--ink-3);font-size:11px;text-transform:uppercase}
#avroot .calendar-grid button{height:34px;text-align:center;padding:0;border:1px solid transparent;background:#fff;border-radius:8px}
#avroot .calendar-grid button:hover{background:#fffdf0;border-color:#ead879}
#avroot .calendar-grid button.out{color:#b9bab4;background:#fafaf8}
#avroot .calendar-grid button.in-range{background:#fff8cc;border-color:#f0df89}
#avroot .calendar-grid button.range-edge{background:var(--gold);border-color:#d8b900;color:#201900}
#avroot .date-actions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-top:10px}
#avroot .date-actions button{text-align:center;background:#f7f7f5;border:1px solid var(--line-2);border-radius:9px;height:34px}
#avroot .date-actions .apply{background:var(--carbon-2);color:#fff;border-color:var(--carbon-2)}
#avroot .table-card{background:#fff;border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow);overflow:auto;max-height:480px}
#avroot .table-head{height:46px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;border-bottom:1px solid var(--line);font-size:14px;color:var(--ink-2);position:sticky;top:0;background:#fff;z-index:3}
#avroot .table-head b{color:var(--ink)}
#avroot table{width:100%;border-collapse:collapse}
#avroot th{height:42px;background:#f0f1f2;color:#656b74;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;padding:0 16px;position:sticky;top:46px;z-index:2}
#avroot td{height:70px;border-top:1px solid var(--line);padding:0 16px;font-size:14px}
#avroot tr:hover td{background:#fffdf0}
#avroot tr.selected td{background:#fff8e8}
#avroot .sort-head{border:0;background:transparent;color:#656b74;text-transform:uppercase;letter-spacing:.06em;font-size:11px;font-weight:700;display:inline-flex;align-items:center;gap:5px}
#avroot .sort-head:after{content:"";width:8px;height:12px;opacity:.2;background:linear-gradient(to bottom,transparent 0 1px,currentColor 1px 2px,transparent 2px 5px,currentColor 5px 6px,transparent 6px)}
#avroot .sort-head.asc:after{clip-path:polygon(50% 0,100% 45%,68% 45%,68% 100%,32% 100%,32% 45%,0 45%);opacity:.6}
#avroot .sort-head.desc:after{clip-path:polygon(32% 0,68% 0,68% 55%,100% 55%,50% 100%,0 55%,32% 55%);opacity:.6}
#avroot .date b{display:block;font-weight:600}
#avroot .date span{display:block;color:var(--ink-2);font-size:12px;margin-top:3px}
#avroot .company{display:inline-flex;align-items:center;gap:10px;font-weight:500;color:var(--ink)}
#avroot .co{width:35px;height:35px;border-radius:10px;display:grid;place-items:center;color:#fff;font-size:12px;font-weight:600}
#avroot .company-cell{display:grid;gap:3px;min-width:0}
#avroot .company-industry{display:block;color:#858881;font-size:11px;padding-left:45px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#avroot .contact-cell b{display:block;font-weight:400}
#avroot .country-mini{display:block;color:#858881;font-size:11px;margin-top:3px}
#avroot .muted{color:var(--ink-2)}
#avroot .badge{display:inline-flex;align-items:center;gap:7px;border-radius:99px;padding:6px 10px;font-size:12px;font-weight:500;white-space:nowrap}
#avroot .badge:before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
#avroot .pending{background:#fff3bd;color:#7a5500}
#avroot .valid{background:var(--ok-bg);color:var(--ok-ink)}
#avroot .review{background:#fff1d8;color:#8b4f0c}
#avroot .rejected{background:#f3d2d2;color:#8c1f1b}
#avroot .rescheduled{background:#e7e8e3;color:#4c4f48}
#avroot .quote-pill{display:inline-flex;align-items:center;border:1px solid #c9b7ea;background:#eee8fb;color:#56358d;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:600;font-style:normal}
#avroot .btn{height:36px;border:1px solid var(--carbon-2);background:var(--carbon-2);color:#fff;border-radius:9px;padding:0 13px;font-weight:600}
#avroot .btn.light{background:#fff;color:var(--carbon-2);border-color:var(--line-2)}
#avroot .btn:disabled{opacity:.6;cursor:default}
#avroot .backdrop{position:fixed;inset:0;background:rgba(0,0,0,.18);opacity:0;pointer-events:none;transition:.18s;z-index:20}
#avroot .backdrop.show{opacity:1;pointer-events:auto}
#avroot .panel{position:fixed;right:18px;top:18px;bottom:18px;width:min(560px,calc(100vw - 36px));background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow-panel);overflow:hidden;display:none;flex-direction:column;z-index:30}
#avroot .panel.show{display:flex}
#avroot .panel-header{padding:18px;border-bottom:1px solid var(--line);display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
#avroot .panel-header h2{margin:0;font-size:20px;font-weight:500}
#avroot .panel-header p{margin:5px 0 0;color:var(--ink-2);line-height:1.35}
#avroot .panel-title{min-width:0;display:grid;gap:4px}
#avroot .cp-mini-badge{justify-self:start;display:inline-flex;align-items:center;border:1px solid #8fd0b4;background:#ccebdc;color:#075f41;border-radius:999px;padding:3px 8px;font-size:10.5px;font-weight:500}
#avroot .cp-mini-badge.invalid{background:#f7dfdc;border-color:#e7b9b3;color:#84261f}
#avroot .cp-mini-badge.reschedule{background:#ececea;border-color:#d1d1ca;color:#4f504b}
#avroot .close{width:34px;height:34px;border:0;background:#fff;border-radius:9px;display:grid;place-items:center;color:var(--ink)}
#avroot .close:hover{background:#f1f1ee}
#avroot .close svg{width:21px;height:21px}
#avroot .panel-tabs{height:56px;display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--line);background:#fff}
#avroot .tab{border:0;background:#fff;color:var(--ink-2);font-size:14px;font-weight:500}
#avroot .tab.active{color:var(--ink);background:#fffdf0;box-shadow:inset 0 -3px 0 var(--gold)}
#avroot .panel-body{overflow:auto;padding:18px;flex:1}
#avroot .tabs-content{display:grid;gap:14px}
#avroot .section{display:grid;gap:10px}
#avroot .section h3{margin:0;font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--ink-3);font-weight:500}
#avroot .validation-flow{border:1px solid var(--line);border-radius:11px;padding:10px 11px;background:#f8f8f6;display:grid;gap:6px;color:#666963;font-size:12.5px;line-height:1.38}
#avroot .note{background:#f8f8f6;border:1px solid var(--line);border-radius:9px;padding:10px 11px;line-height:1.45;color:#5f625d;font-size:12.5px}
#avroot .choice{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
#avroot .choice label{min-height:34px;border-radius:9px;border:1px solid var(--line-2);background:#fff;color:var(--ink);font-weight:500;display:grid;place-items:center;text-align:center;cursor:pointer;font-size:12.5px;padding:0 8px;position:relative}
#avroot .choice input{position:absolute;opacity:0;pointer-events:none}
#avroot .choice label[data-choice="validar"]{background:var(--ok-bg);border-color:#c7ebde;color:var(--ok-ink)}
#avroot .choice label[data-choice="rechazar"]{background:#f7dddd;border-color:#e5a09a;color:#8f2721}
#avroot .choice label[data-choice="revision"]{background:#fff1d8;border-color:#e0b46d;color:#8b4f0c}
#avroot .choice label[data-choice="reagendar"]{background:#efefec;border-color:#d7d7d0;color:#565650}
#avroot .choice label:has(input:checked){box-shadow:inset 0 0 0 2px currentColor}
#avroot textarea{width:100%;min-height:58px;resize:none;border:1px solid var(--line-2);border-radius:9px;padding:9px 10px;outline:0;font-size:12.5px;line-height:1.35;color:#4f514d;font-family:inherit}
#avroot .footer-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px}
#avroot .chips{display:flex;gap:8px;flex-wrap:wrap}
#avroot .chip{border:1px solid var(--line);background:#f0f0ec;color:var(--ink-2);border-radius:99px;padding:7px 10px;font-size:12px;font-weight:500}
#avroot .chip.ok{background:var(--ok-bg);color:var(--ok-ink);border-color:#c7ebde}
#avroot .media-card{border:1px solid #deded8;background:#fbfbfa;color:#2f302d;border-radius:11px;overflow:hidden}
#avroot .player{height:82px;background:#fbfbfa;display:grid;grid-template-columns:auto 1fr;place-items:center start;gap:12px;padding:14px}
#avroot .player:after{content:"Video y transcripción IA disponibles";font-size:13px;color:#555851}
#avroot .play{width:42px;height:42px;border-radius:50%;border:1px solid #d7bd18;background:#fff7b8;color:#4a3b00;display:grid;place-items:center}
#avroot .timeline{height:38px;padding:0 14px;display:flex;align-items:center;gap:10px;background:#f0f0ec;color:#61645e}
#avroot .line{height:6px;flex:1;background:#deded8;border-radius:99px;overflow:hidden}
#avroot .line i{display:block;height:100%;width:0;background:var(--gold)}
#avroot .evidence-links{display:grid;grid-template-columns:1fr 1fr;gap:8px}
#avroot .evidence-links div{border:1px solid var(--line);border-radius:9px;background:#f8f8f6;padding:9px 10px;min-width:0}
#avroot .evidence-links small{display:block;color:var(--ink-3);font-size:10px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
#avroot .evidence-links a,#avroot .evidence-links span{display:block;color:#3f403c;font-size:12.5px;overflow-wrap:anywhere;text-decoration:none}
#avroot .evidence-links a:hover{text-decoration:underline}
#avroot .kv{display:grid;grid-template-columns:1fr 1fr;gap:10px}
#avroot .kv div{min-width:0;border:1px solid var(--line);border-radius:11px;padding:11px;background:#fbfbfa}
#avroot .kv small{display:block;color:var(--ink-3);font-weight:500;text-transform:uppercase;font-size:10px;letter-spacing:.06em;margin-bottom:5px}
#avroot .kv b{display:block;min-width:0;font-size:13px;font-weight:400;overflow-wrap:anywhere}
#avroot .toast{position:fixed;right:22px;bottom:22px;background:#202020;color:#fff;border-radius:12px;padding:13px 15px;box-shadow:var(--shadow-panel);font-weight:700;opacity:0;transform:translateY(10px);pointer-events:none;transition:.18s;z-index:60}
#avroot .toast.show{opacity:1;transform:translateY(0)}
@media(max-width:1180px){#avroot .compact-stats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:820px){#avroot .topbar{padding:16px}#avroot .work{padding:16px}#avroot .filters{grid-template-columns:1fr}#avroot table{min-width:760px}#avroot .panel{width:calc(100vw - 24px);right:12px;top:12px;bottom:12px}#avroot .choice,#avroot .footer-actions,#avroot .kv,#avroot .evidence-links{grid-template-columns:1fr 1fr}}
`;
