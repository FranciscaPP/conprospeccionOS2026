"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { format } from "date-fns";
import {
  AlertTriangle,
  BookOpen,
  Calendar,
  CheckCircle2,
  ChevronDown,
  Clock,
  FileText,
  Search,
  X,
} from "lucide-react";
import { useApp } from "@/lib/app-context";
import { ACTIVE_CLIENTS, clientSlugFromName, type ActiveClientSlug } from "@/lib/access-control";
import { StatusBadge } from "@/components/status-badge";
import { CompanyAvatar } from "@/components/company-avatar";
import { MeetingDrawer } from "@/components/meeting-drawer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ClientDecision, CPValidation, Meeting, MeetingStatus } from "@/lib/types";
import {
  getBANTScore,
  getClientDecision,
  getClientSearchText,
  isClientLocked,
  MONTHLY_GOAL_BY_CLIENT,
} from "@/lib/meeting-rules";

type KpiFilter = "all" | "valid" | "not_valid" | "pending" | "rejected_or_disputed";
type AiBantFilter = "all" | "bant_met" | "bant_not_met" | "insufficient_evidence";

const meetingStatusFilterOptions: Array<{ label: string; value: MeetingStatus | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "scheduled", label: "Agendada" },
  { value: "completed", label: "Realizada" },
  { value: "rescheduled", label: "Reagendada" },
  { value: "cancelled", label: "Cancelada" },
  { value: "no_show", label: "No asistió" },
];

const cpValidationFilterOptions: Array<{ label: string; value: CPValidation | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "waiting_validation", label: "Pendiente de evaluación" },
  { value: "valid_cp", label: "Válida por Conprospección" },
  { value: "not_valid_cp", label: "No válida por Conprospección" },
  { value: "not_completed", label: "No válida por Conprospección" },
  { value: "requires_review", label: "Requiere revisión" },
  { value: "rescheduled", label: "Reagendada" },
];

const clientDecisionFilterOptions: Array<{ label: string; value: ClientDecision | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "pending", label: "Pendiente cliente" },
  { value: "accepted", label: "Aceptada" },
  { value: "review_requested", label: "Observada" },
  { value: "rejected", label: "En disputa" },
];

const aiBantFilterOptions: Array<{ label: string; value: AiBantFilter }> = [
  { value: "all", label: "Todos" },
  { value: "bant_met", label: "Cumple mínimo 2/4 BANT" },
  { value: "bant_not_met", label: "No cumple mínimo 2/4 BANT" },
  { value: "insufficient_evidence", label: "Evidencia insuficiente" },
];

function resolveClientFromParam(meetings: Meeting[], clientParam: string | null) {
  const requestedSlug = clientSlugFromName(clientParam || "") ?? "gbs";
  return (
    meetings.find((meeting) => clientSlugFromName(meeting.client) === requestedSlug)?.client ||
    ACTIVE_CLIENTS.find((client) => client.slug === requestedSlug)?.displayName ||
    "GBS LOGISTICS"
  );
}

function clientPath(slug: ActiveClientSlug) {
  return `/client/meeting-validation?client=${slug}`;
}

function cpStatusMeta(meeting: Meeting): { status: CPValidation; label: string } {
  if (meeting.meetingStatus === "rescheduled" || meeting.cpValidation === "rescheduled") {
    return { status: "rescheduled", label: "Reagendada por CP" };
  }
  if (meeting.cpValidation === "valid_cp") {
    return { status: "valid_cp", label: "Validada por CP" };
  }
  if (meeting.cpValidation === "not_valid_cp" || meeting.cpValidation === "not_completed") {
    return { status: meeting.cpValidation, label: "No validada por CP" };
  }
  if (meeting.cpValidation === "requires_review") {
    return { status: "requires_review", label: "Revisión CP" };
  }
  return { status: "waiting_validation", label: "Pendiente validación CP" };
}

function clientDecisionText(meeting: Meeting) {
  const decision = getClientDecision(meeting);
  if (decision === "accepted") return "Cliente: aceptada";
  if (decision === "rejected") return "Cliente: disputa validez";
  if (decision === "review_requested") return "Cliente: observada";
  return "Cliente: pendiente";
}

function ValidationState({ meeting }: { meeting: Meeting }) {
  const cp = cpStatusMeta(meeting);
  return (
    <div className="inline-flex flex-col items-start">
      <StatusBadge status={cp.status} label={cp.label} size="sm" />
      <span className="mt-1 text-[11px] leading-4 text-muted-foreground">{clientDecisionText(meeting)}</span>
    </div>
  );
}

export default function MeetingValidationPage() {
  const { role, meetings, meetingsLoading, meetingsError, selectedMeetingId, setSelectedMeetingId } = useApp();
  const isInternal = role === "internal";
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [queryMeetingId, setQueryMeetingId] = useState<string | null>(null);
  const [queryClient, setQueryClient] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [kpiFilter, setKpiFilter] = useState<KpiFilter>("all");
  const [dateFromFilter, setDateFromFilter] = useState("");
  const [dateToFilter, setDateToFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("all");
  const [meetingStatusFilter, setMeetingStatusFilter] = useState<MeetingStatus | "all">("all");
  const [cpValidationFilter, setCpValidationFilter] = useState<CPValidation | "all">("all");
  const [clientDecisionFilter, setClientDecisionFilter] = useState<ClientDecision | "all">("all");
  const [aiBantFilter, setAiBantFilter] = useState<AiBantFilter>("all");
  const [showExplainer, setShowExplainer] = useState(true);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  const requestedMeetingId = queryMeetingId || selectedMeetingId;
  const requestedMeeting = useMemo(
    () => meetings.find((meeting) => meeting.id === requestedMeetingId) || null,
    [meetings, requestedMeetingId]
  );
  const selectedClient = requestedMeeting?.client || resolveClientFromParam(meetings, queryClient);

  const clientMeetings = useMemo(
    () => meetings.filter((meeting) => meeting.client === selectedClient),
    [meetings, selectedClient]
  );

  const goal = MONTHLY_GOAL_BY_CLIENT[selectedClient] ?? 10;

  const countries = useMemo(
    () => [...new Set(clientMeetings.map((meeting) => meeting.country).filter(Boolean))].sort() as string[],
    [clientMeetings]
  );

  const baseFilteredMeetings = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return clientMeetings.filter((meeting) => {
      const clientDecision = getClientDecision(meeting);
      const bantScore = getBANTScore(meeting);
      const meetingDay = meeting.meetingDate.slice(0, 10);
      const matchesSearch = !query || getClientSearchText(meeting).includes(query);
      const matchesDateFrom = !dateFromFilter || meetingDay >= dateFromFilter;
      const matchesDateTo = !dateToFilter || meetingDay <= dateToFilter;
      const matchesCountry = countryFilter === "all" || meeting.country === countryFilter;
      const matchesMeetingStatus = meetingStatusFilter === "all" || meeting.meetingStatus === meetingStatusFilter;
      const matchesCPValidation = cpValidationFilter === "all" || meeting.cpValidation === cpValidationFilter;
      const matchesClientDecision = clientDecisionFilter === "all" || clientDecision === clientDecisionFilter;
      const matchesAiBant =
        aiBantFilter === "all" ||
        (aiBantFilter === "bant_met" && bantScore >= 2) ||
        (aiBantFilter === "bant_not_met" && bantScore < 2) ||
        (aiBantFilter === "insufficient_evidence" &&
          (meeting.evidence?.aiRecommendation === "review" || (meeting.evidence?.aiConfidence ?? 1) < 0.7));
      return (
        matchesSearch &&
        matchesDateFrom &&
        matchesDateTo &&
        matchesCountry &&
        matchesMeetingStatus &&
        matchesCPValidation &&
        matchesClientDecision &&
        matchesAiBant
      );
    });
  }, [
    clientMeetings,
    searchQuery,
    dateFromFilter,
    dateToFilter,
    countryFilter,
    meetingStatusFilter,
    cpValidationFilter,
    clientDecisionFilter,
    aiBantFilter,
  ]);

  const kpis = useMemo(() => {
    const finalValid = baseFilteredMeetings.filter((meeting) => meeting.finalValidation === "final_valid").length;
    const finalNotValid = baseFilteredMeetings.filter(
      (meeting) => meeting.finalValidation === "final_not_valid" || meeting.cpValidation === "not_valid_cp" || meeting.cpValidation === "not_completed"
    ).length;
    const pending = baseFilteredMeetings.filter((meeting) => meeting.cpValidation === "valid_cp" && getClientDecision(meeting) === "pending").length;
    const rejected = baseFilteredMeetings.filter((meeting) => getClientDecision(meeting) === "rejected").length;
    const observed = baseFilteredMeetings.filter((meeting) => getClientDecision(meeting) === "review_requested").length;
    return {
      total: baseFilteredMeetings.length,
      finalValid,
      finalNotValid,
      pending,
      rejected,
      observed,
      progress: goal > 0 ? Math.round((finalValid / goal) * 100) : 0,
    };
  }, [baseFilteredMeetings, goal]);

  const tableFilteredMeetings = useMemo(
    () =>
      baseFilteredMeetings.filter((meeting) => {
        if (kpiFilter === "all") return true;
        if (kpiFilter === "valid") return meeting.finalValidation === "final_valid";
        if (kpiFilter === "not_valid") {
          return meeting.finalValidation === "final_not_valid" || meeting.cpValidation === "not_valid_cp" || meeting.cpValidation === "not_completed";
        }
        if (kpiFilter === "pending") return meeting.cpValidation === "valid_cp" && getClientDecision(meeting) === "pending";
        return (
          getClientDecision(meeting) === "rejected" ||
          getClientDecision(meeting) === "review_requested" ||
          meeting.finalValidation === "in_dispute" ||
          meeting.finalValidation === "under_review"
        );
      }),
    [baseFilteredMeetings, kpiFilter]
  );

  const openDrawer = (meeting: Meeting) => {
    setSelectedMeeting(meeting);
    setDrawerOpen(true);
  };

  const applyKpiFilter = (filter: KpiFilter) => {
    setKpiFilter(filter);
  };

  const hasActiveFilters =
    searchQuery.trim() !== "" ||
    kpiFilter !== "all" ||
    dateFromFilter !== "" ||
    dateToFilter !== "" ||
    countryFilter !== "all" ||
    meetingStatusFilter !== "all" ||
    cpValidationFilter !== "all" ||
    clientDecisionFilter !== "all" ||
    aiBantFilter !== "all";

  const clearFilters = () => {
    setSearchQuery("");
    setKpiFilter("all");
    setDateFromFilter("");
    setDateToFilter("");
    setCountryFilter("all");
    setMeetingStatusFilter("all");
    setCpValidationFilter("all");
    setClientDecisionFilter("all");
    setAiBantFilter("all");
  };

  const switchClient = (slug: ActiveClientSlug) => {
    setQueryMeetingId(null);
    setSelectedMeetingId(null);
    setQueryClient(slug);
    setSearchQuery("");
    setKpiFilter("all");
    setDateFromFilter("");
    setDateToFilter("");
    setCountryFilter("all");
    setMeetingStatusFilter("all");
    setCpValidationFilter("all");
    setClientDecisionFilter("all");
    setAiBantFilter("all");
    window.history.replaceState(null, "", clientPath(slug));
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setQueryMeetingId(params.get("meeting"));
    setQueryClient(params.get("client"));
  }, []);

  useEffect(() => {
    if (!requestedMeeting) return;
    setSelectedMeeting(requestedMeeting);
    setDrawerOpen(true);
    setSelectedMeetingId(null);
  }, [requestedMeeting, setSelectedMeetingId]);

  return (
    <div className="flex-1 overflow-hidden">
      <header className="border-b border-border bg-card px-4 py-3 sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-baseline gap-2">
              <h1 className="text-[22px] font-semibold leading-tight text-[var(--ink)]">Avance reuniones</h1>
              <span className="text-lg text-[var(--ink-3)]">·</span>
              <span className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]">{selectedClient}</span>
            </div>
            <p className="mt-1 max-w-full break-words text-sm leading-5 text-muted-foreground">
              Validación cliente de reuniones entregadas por Conprospección
            </p>
          </div>
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:min-w-[240px] sm:items-end">
            <div className="w-full sm:w-[260px]">
              <div className="mb-1.5 flex items-baseline justify-between gap-3">
                <span className="text-xs font-medium text-[var(--ink-2)]">Avance meta</span>
                <strong className="font-display tnum text-[15px] font-semibold text-[var(--ink)]">
                  {kpis.finalValid}/{goal} · {kpis.progress}%
                </strong>
              </div>
              <Progress value={kpis.progress} className="h-1.5 bg-[#ececea]" />
            </div>
            {isInternal && (
              <div className="flex flex-wrap gap-2 sm:justify-end">
                {ACTIVE_CLIENTS.map((client) => (
                  <button
                    key={client.slug}
                    type="button"
                    className={`inline-flex min-h-11 items-center rounded-lg border px-3 py-2 text-xs font-semibold transition sm:min-h-9 ${
                      clientSlugFromName(selectedClient) === client.slug
                        ? "border-[#333] bg-[#f0f0ee] text-[#333]"
                        : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                    onClick={() => switchClient(client.slug)}
                  >
                    {client.displayName}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      <ScrollArea className="h-[calc(100dvh-7rem)] lg:h-[calc(100vh-65px)]">
        <div className="space-y-3 p-3 sm:p-4">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-5">
            <MeetingKpi
              title="Total generadas"
              value={kpis.total}
              icon={<Calendar className="h-5 w-5" />}
              active={kpiFilter === "all"}
              onClick={() => applyKpiFilter("all")}
            />
            <MeetingKpi
              title="Validadas"
              value={kpis.finalValid}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
              active={kpiFilter === "valid"}
              onClick={() => applyKpiFilter("valid")}
            />
            <MeetingKpi
              title="No válidas"
              value={kpis.finalNotValid}
              icon={<AlertTriangle className="h-5 w-5" />}
              variant="danger"
              active={kpiFilter === "not_valid"}
              onClick={() => applyKpiFilter("not_valid")}
            />
            <MeetingKpi
              title="Pendiente cliente"
              value={kpis.pending}
              icon={<Clock className="h-5 w-5" />}
              variant="warning"
              active={kpiFilter === "pending"}
              onClick={() => applyKpiFilter("pending")}
            />
            <MeetingKpi
              title="En revisión / disputa"
              value={kpis.rejected + kpis.observed}
              icon={<AlertTriangle className="h-5 w-5" />}
              variant="review"
              active={kpiFilter === "rejected_or_disputed"}
              onClick={() => applyKpiFilter("rejected_or_disputed")}
            />
          </div>

          <section className="rounded-[12px] border border-[var(--line)] bg-white px-3 py-2.5 shadow-card">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
              <h3 className="flex shrink-0 items-center gap-2 text-sm font-semibold text-foreground">
                <BookOpen className="h-4 w-4 text-[var(--ink-2)]" />
                Criterios de reunión válida
              </h3>
              <ul className="grid flex-1 gap-1.5 text-xs text-muted-foreground sm:grid-cols-2 xl:grid-cols-4">
                {[
                  "Reunión realizada",
                  "Mínimo 2 variables BANT detectadas por IA/CP",
                  "ICP trabajado desde base/campaña, sin alerta contractual",
                  "Evidencia suficiente",
                ].map((criterion) => (
                  <li key={criterion} className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[var(--ok)]" />
                    <span>{criterion}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="hidden">
            <button
              type="button"
              onClick={() => setShowExplainer((value) => !value)}
              aria-expanded={showExplainer}
              className="flex w-full items-center justify-between gap-2 text-left"
            >
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <BookOpen className="h-4 w-4 text-[var(--ink-2)]" />
                ¿Qué es una reunión válida?
              </h3>
              <ChevronDown
                className={`h-4 w-4 shrink-0 text-[var(--ink-3)] transition-transform ${showExplainer ? "rotate-180" : ""}`}
              />
            </button>
            {showExplainer && (
              <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--ok)]" />
                  La reunión se realizó
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--ok)]" />
                  Al menos 2 variables BANT detectadas por IA/CP
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--ok)]" />
                  ICP trabajado desde base/campaña, sin alerta contractual
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--ok)]" />
                  Evidencia suficiente de la reunión
                </li>
              </ul>
            )}
          </section>

          <section className="rounded-[13px] border border-[var(--line)] bg-white p-3 shadow-card">
            <div className="grid gap-3 lg:grid-cols-[minmax(300px,1fr)_300px_180px_auto] lg:items-end">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Buscar empresa, contacto, cargo, correo, teléfono o país"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  className="h-10 rounded-[10px] pl-9 text-sm"
                />
              </div>
              <div>
                <FilterLabel>Fecha</FilterLabel>
                <div className="grid gap-2 sm:grid-cols-2">
                  <Input
                    aria-label="Desde"
                    type="date"
                    value={dateFromFilter}
                    onChange={(event) => setDateFromFilter(event.target.value)}
                    className="h-10 rounded-[10px] text-sm"
                  />
                  <Input
                    aria-label="Hasta"
                    type="date"
                    value={dateToFilter}
                    onChange={(event) => setDateToFilter(event.target.value)}
                    className="h-10 rounded-[10px] text-sm"
                  />
                </div>
              </div>
              <div>
                <FilterLabel>País</FilterLabel>
                <NativeFilter
                  ariaLabel="Filtrar por país"
                  className="w-full"
                  value={countryFilter}
                  onChange={setCountryFilter}
                  options={[
                    { value: "all", label: "Todos" },
                    ...countries.map((country) => ({ value: country, label: country })),
                  ]}
                />
              </div>
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex h-10 items-center justify-center gap-1.5 rounded-[10px] border border-border bg-background px-3 text-sm font-medium text-foreground transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!hasActiveFilters}
              >
                <X className="h-3.5 w-3.5" />
                Limpiar filtros
              </button>
            </div>

            <div className="mt-3 border-t border-border pt-3">
              <button
                type="button"
                onClick={() => setShowAdvancedFilters((value) => !value)}
                aria-expanded={showAdvancedFilters}
                className="inline-flex h-9 items-center gap-2 rounded-[9px] border border-border bg-background px-3 text-sm font-medium text-foreground transition hover:bg-muted"
              >
                <ChevronDown className={`h-4 w-4 transition-transform ${showAdvancedFilters ? "rotate-180" : ""}`} />
                Filtros avanzados
              </button>
              {showAdvancedFilters && (
                <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <div>
                    <FilterLabel>Estado de la reunión</FilterLabel>
                    <NativeFilter
                      ariaLabel="Filtrar por estado de la reunión"
                      className="w-full"
                      value={meetingStatusFilter}
                      onChange={(value) => setMeetingStatusFilter(value as MeetingStatus | "all")}
                      options={meetingStatusFilterOptions}
                    />
                  </div>
                  <div>
                    <FilterLabel>Validación Conprospección</FilterLabel>
                    <NativeFilter
                      ariaLabel="Filtrar por validación Conprospección"
                      className="w-full"
                      value={cpValidationFilter}
                      onChange={(value) => setCpValidationFilter(value as CPValidation | "all")}
                      options={cpValidationFilterOptions}
                    />
                  </div>
                  <div>
                    <FilterLabel>Respuesta del cliente</FilterLabel>
                    <NativeFilter
                      ariaLabel="Filtrar por respuesta del cliente"
                      className="w-full"
                      value={clientDecisionFilter}
                      onChange={(value) => setClientDecisionFilter(value as ClientDecision | "all")}
                      options={clientDecisionFilterOptions}
                    />
                  </div>
                  <div>
                    <FilterLabel>Resultado IA/BANT</FilterLabel>
                    <NativeFilter
                      ariaLabel="Filtrar por resultado IA/BANT"
                      className="w-full"
                      value={aiBantFilter}
                      onChange={(value) => setAiBantFilter(value as AiBantFilter)}
                      options={aiBantFilterOptions}
                    />
                  </div>
                </div>
              )}
            </div>
          </section>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-muted-foreground">
              Mostrando {tableFilteredMeetings.length} de {baseFilteredMeetings.length} reuniones filtradas
            </p>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex min-h-9 items-center gap-1.5 rounded-[9px] border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-muted"
              >
                <X className="h-3.5 w-3.5" />
                Limpiar filtros
              </button>
            )}
          </div>

          <div className="space-y-3 md:hidden">
            {tableFilteredMeetings.length === 0 && (
              <div className="rounded-xl border border-border bg-card p-8 text-center">
                <FileText className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No se encontraron reuniones con esos filtros.</p>
              </div>
            )}
            {tableFilteredMeetings.map((meeting) => {
              const locked = isClientLocked(meeting);

              return (
                <button
                  key={meeting.id}
                  type="button"
                  className="w-full rounded-xl border border-border bg-card p-4 text-left shadow-sm"
                  onClick={() => openDrawer(meeting)}
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2">
                      <CompanyAvatar name={meeting.company} />
                      <div>
                        <p className="text-sm font-semibold text-foreground">{meeting.company}</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {meeting.firstName} {meeting.lastName} · {meeting.jobTitle}
                        </p>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="font-display tnum text-sm font-medium text-foreground">{format(new Date(meeting.meetingDate), "d MMM")}</p>
                      <p className="font-display tnum text-xs text-muted-foreground">{format(new Date(meeting.meetingDate), "HH:mm")}</p>
                    </div>
                  </div>
                  <div className="mb-3 flex flex-wrap gap-2">
                    <ValidationState meeting={meeting} />
                  </div>
                  <div className="flex justify-end">
                    <span className={`rounded-lg px-3 py-1.5 text-sm font-medium ${locked ? "border border-border bg-background text-foreground" : "bg-[#333] text-white"}`}>
                      {locked ? "Ver detalle" : "Validar"}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="hidden rounded-[13px] border border-[var(--line)] bg-card shadow-card md:block">
            <div className="flex h-[46px] items-center justify-between border-b border-[var(--line)] px-4 text-sm text-muted-foreground">
              <span>
                <b className="font-semibold text-foreground">Reuniones para validar</b>
              </span>
              {meetingsLoading && <span>Cargando reuniones...</span>}
              {meetingsError && <span className="text-red-600">{meetingsError}</span>}
            </div>
            <div className="max-h-[60vh] overflow-auto rounded-xl">
              <table className="w-full min-w-[760px]">
                <thead className="sticky top-0 z-10 bg-[#f0f1f2] shadow-sm">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Fecha</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Empresa</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Contacto</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Cargo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Estado</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {tableFilteredMeetings.map((meeting) => {
                    const locked = isClientLocked(meeting);
                    return (
                      <tr key={meeting.id} className="cursor-pointer bg-white transition-colors hover:bg-[#fffdf0]" onClick={() => openDrawer(meeting)}>
                        <td className="px-4 py-3">
                          <p className="font-display tnum text-sm font-medium text-foreground">{format(new Date(meeting.meetingDate), "d MMM")}</p>
                          <p className="font-display tnum text-xs text-muted-foreground">{format(new Date(meeting.meetingDate), "HH:mm")}</p>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <CompanyAvatar name={meeting.company} />
                            <span className="text-sm font-medium text-foreground">{meeting.company}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-foreground">{[meeting.firstName, meeting.lastName].filter(Boolean).join(" ") || "-"}</td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">{meeting.jobTitle}</td>
                        <td className="px-4 py-3">
                          <ValidationState meeting={meeting} />
                        </td>
                        <td className="px-4 py-3">
                          <Button
                            variant={locked ? "outline" : "default"}
                            size="sm"
                            className=""
                            onClick={(event) => {
                              event.stopPropagation();
                              openDrawer(meeting);
                            }}
                          >
                            {locked ? "Ver detalle" : "Validar"}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {tableFilteredMeetings.length === 0 && (
              <div className="p-8 text-center">
                <FileText className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No se encontraron reuniones con esos filtros.</p>
              </div>
            )}
          </div>
        </div>
      </ScrollArea>

      <MeetingDrawer
        meeting={selectedMeeting}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedMeeting(null);
        }}
        mode="client"
      />
    </div>
  );
}

function FilterLabel({ children }: { children: ReactNode }) {
  return <span className="mb-1.5 block text-xs font-medium text-[var(--ink-2)]">{children}</span>;
}

function NativeFilter({
  ariaLabel,
  className,
  onChange,
  options,
  value,
}: {
  ariaLabel: string;
  className?: string;
  onChange: (value: string) => void;
  options: Array<{ label: string; value: string }>;
  value: string;
}) {
  return (
    <select
      aria-label={ariaLabel}
      className={`h-10 rounded-[10px] border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-[#d1bd50] focus:ring-3 focus:ring-[#ffd700]/20 ${className ?? ""}`}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

function MeetingKpi({
  active,
  icon,
  onClick,
  title,
  value,
  variant = "default",
}: {
  active: boolean;
  icon: ReactNode;
  onClick: () => void;
  title: string;
  value: number;
  variant?: "default" | "success" | "warning" | "danger" | "review";
}) {
  const variantClass = {
    default: "border-[#d7bd18] bg-[#fff7b8] text-[var(--ink)]",
    success: "border-[#78c5a3] bg-[var(--ok-bg)] text-[var(--ok-ink)]",
    warning: "border-[#dfa94d] bg-[var(--warn-bg)] text-[var(--warn-ink)]",
    danger: "border-[#dc958d] bg-[var(--bad-bg)] text-[var(--bad-ink)]",
    review: "border-[#dc9c63] bg-[var(--rev-bg)] text-[var(--rev-ink)]",
  }[variant];

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-[11px] border p-3 text-left shadow-card transition hover:-translate-y-px hover:shadow-[0_5px_14px_rgba(20,20,20,.08)] ${variantClass} ${
        active ? "outline outline-1 outline-offset-2 outline-[rgba(43,43,43,.35)]" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <small className="block text-[10px] font-medium uppercase tracking-[.06em] opacity-75">{title}</small>
          <strong className="font-display tnum mt-2 block text-[25px] font-semibold leading-none text-[var(--ink)]">{value}</strong>
        </div>
        <span className="grid h-8 w-8 place-items-center rounded-[9px] bg-white/55 text-current">{icon}</span>
      </div>
    </button>
  );
}
