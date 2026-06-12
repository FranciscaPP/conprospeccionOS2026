"use client";

import { useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import {
  AlertTriangle,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  FileText,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useApp } from "@/lib/app-context";
import { KPICard } from "@/components/kpi-card";
import { StatusBadge } from "@/components/status-badge";
import { MeetingDrawer } from "@/components/meeting-drawer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { FinalValidation, Meeting, MeetingStatus } from "@/lib/types";
import {
  getClientDecision,
  getClientSearchText,
  getSimpleClientStatus,
  getValidationTooltip,
  getValidationResultLabel,
  isClientLocked,
  MONTHLY_GOAL_BY_CLIENT,
} from "@/lib/meeting-rules";

type KpiFilter = "all" | "valid" | "pending" | "rejected_or_disputed";

function statusToBadge(status: string): FinalValidation | MeetingStatus {
  if (status === "Validada") return "final_valid";
  if (status === "Rechazada" || status === "No realizada") return "final_not_valid";
  if (status === "En revisión") return "in_dispute";
  if (status === "Reagendada") return "rescheduled";
  return "pending";
}

export default function MeetingValidationPage() {
  const { meetings, selectedMeetingId, setSelectedMeetingId } = useApp();
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [queryMeetingId, setQueryMeetingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [kpiFilter, setKpiFilter] = useState<KpiFilter>("all");
  const [monthFilter, setMonthFilter] = useState("all");
  const [dayFilter, setDayFilter] = useState("all");

  const requestedMeetingId = queryMeetingId || selectedMeetingId;
  const requestedMeeting = useMemo(
    () => meetings.find((meeting) => meeting.id === requestedMeetingId) || null,
    [meetings, requestedMeetingId]
  );
  const selectedClient = requestedMeeting?.client || "GBS Logistics";

  const clientMeetings = useMemo(
    () => meetings.filter((meeting) => meeting.client === selectedClient),
    [meetings, selectedClient]
  );

  const goal = MONTHLY_GOAL_BY_CLIENT[selectedClient] ?? 10;

  const kpis = useMemo(() => {
    const finalValid = clientMeetings.filter((meeting) => meeting.finalValidation === "final_valid").length;
    const pending = clientMeetings.filter((meeting) => getClientDecision(meeting) === "pending").length;
    const rejected = clientMeetings.filter((meeting) => getClientDecision(meeting) === "rejected").length;
    const disputed = clientMeetings.filter((meeting) => meeting.finalValidation === "in_dispute").length;
    return {
      total: clientMeetings.length,
      finalValid,
      pending,
      rejected,
      disputed,
      progress: Math.round((finalValid / goal) * 100),
    };
  }, [clientMeetings, goal]);

  const months = useMemo(
    () => [...new Set(clientMeetings.map((meeting) => meeting.meetingDate.slice(0, 7)))].sort(),
    [clientMeetings]
  );

  const days = useMemo(() => {
    return [...new Set(
      clientMeetings
        .filter((meeting) => monthFilter === "all" || meeting.meetingDate.slice(0, 7) === monthFilter)
        .map((meeting) => meeting.meetingDate.slice(0, 10))
    )].sort();
  }, [clientMeetings, monthFilter]);

  const filteredMeetings = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return clientMeetings.filter((meeting) => {
      const simpleStatus = getSimpleClientStatus(meeting);
      const matchesSearch = !query || getClientSearchText(meeting).includes(query);
      const matchesStatus = statusFilter === "all" || simpleStatus === statusFilter;
      const matchesKpi =
        kpiFilter === "all" ||
        (kpiFilter === "valid" && meeting.finalValidation === "final_valid") ||
        (kpiFilter === "pending" && getClientDecision(meeting) === "pending") ||
        (kpiFilter === "rejected_or_disputed" &&
          (getClientDecision(meeting) === "rejected" || meeting.finalValidation === "in_dispute"));
      const matchesMonth = monthFilter === "all" || meeting.meetingDate.slice(0, 7) === monthFilter;
      const matchesDay = dayFilter === "all" || meeting.meetingDate.slice(0, 10) === dayFilter;
      return matchesSearch && matchesStatus && matchesKpi && matchesMonth && matchesDay;
    });
  }, [clientMeetings, searchQuery, statusFilter, kpiFilter, monthFilter, dayFilter]);

  const openDrawer = (meeting: Meeting) => {
    setSelectedMeeting(meeting);
    setDrawerOpen(true);
  };

  const applyKpiFilter = (filter: KpiFilter) => {
    setKpiFilter(filter);
    setStatusFilter("all");
  };

  useEffect(() => {
    setQueryMeetingId(new URLSearchParams(window.location.search).get("meeting"));
  }, []);

  useEffect(() => {
    if (!requestedMeeting) return;
    setSelectedMeeting(requestedMeeting);
    setDrawerOpen(true);
    setSelectedMeetingId(null);
  }, [requestedMeeting, setSelectedMeetingId]);

  return (
    <div className="flex-1 overflow-hidden">
      <header className="border-b border-border bg-card px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-lg font-semibold text-foreground sm:text-xl">Validación de reuniones</h1>
            <p className="max-w-full break-words text-sm leading-5 text-muted-foreground">
              {selectedClient} · Revisión de reuniones entregadas
            </p>
          </div>
          {kpis.pending > 0 && (
            <div className="flex w-fit items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800">
              <Clock className="h-4 w-4" />
              {kpis.pending} requieren validación
            </div>
          )}
        </div>
      </header>

      <ScrollArea className="h-[calc(100dvh-7rem)] lg:h-[calc(100vh-65px)]">
        <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KPICard
              title="Total generadas"
              value={kpis.total}
              icon={<Calendar className="h-5 w-5" />}
              active={kpiFilter === "all" && statusFilter === "all"}
              onClick={() => applyKpiFilter("all")}
            />
            <KPICard
              title="Validadas para meta"
              value={kpis.finalValid}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
              active={kpiFilter === "valid"}
              onClick={() => applyKpiFilter("valid")}
            />
            <KPICard
              title="Pendientes de validación"
              value={kpis.pending}
              icon={<Clock className="h-5 w-5" />}
              variant="warning"
              active={kpiFilter === "pending"}
              onClick={() => applyKpiFilter("pending")}
            />
            <KPICard
              title="Objetadas / en disputa"
              value={kpis.rejected + kpis.disputed}
              icon={<AlertTriangle className="h-5 w-5" />}
              variant="danger"
              active={kpiFilter === "rejected_or_disputed"}
              onClick={() => applyKpiFilter("rejected_or_disputed")}
            />
          </div>

          <section className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Avance de meta</h3>
                <p className="text-xs text-muted-foreground">Se consideran reuniones validadas por cliente y aplicables a la meta.</p>
              </div>
              <span className="text-lg font-bold text-violet-600">
                {kpis.finalValid}/{goal} · {kpis.progress}%
              </span>
            </div>
            <Progress value={kpis.progress} className="h-2" />
          </section>

          <section className="rounded-xl border border-violet-100 bg-violet-50/60 p-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-lg bg-violet-600 p-2 text-white">
                <BookOpen className="h-4 w-4" />
              </div>
              <div className="min-w-0 space-y-2">
                <h3 className="text-sm font-semibold text-foreground">¿Qué es una reunión válida?</h3>
                <p className="max-w-full break-words text-sm leading-6 text-muted-foreground">
                  Cuenta para la meta cuando el prospecto corresponde al ICP acordado, la reunión se realiza y existen al menos dos variables comerciales relevantes. Aquí se muestra la información necesaria para revisar y calificar la reunión.
                </p>
              </div>
            </div>
          </section>

          <div className="grid gap-3 lg:grid-cols-[1fr_220px_180px_180px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por empresa, nombre, apellido o cargo"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                className="pl-9"
              />
            </div>
            <NativeFilter
              ariaLabel="Filtrar por estado"
              className="w-full"
              value={statusFilter}
              onChange={(value) => {
                setStatusFilter(value);
                setKpiFilter("all");
              }}
              options={[
                { value: "all", label: "Estado: Todos" },
                ...["Pendiente de validación", "Validada", "Rechazada", "En revisión", "Reagendada", "No realizada"].map((status) => ({
                  value: status,
                  label: status,
                })),
              ]}
            />
            <NativeFilter
              ariaLabel="Filtrar por mes"
              className="w-full"
              value={monthFilter}
              onChange={(value) => {
                setMonthFilter(value);
                setDayFilter("all");
              }}
              options={[
                { value: "all", label: "Mes: Todos" },
                ...months.map((month) => ({
                  value: month,
                  label: format(new Date(`${month}-01T12:00:00`), "MMMM yyyy"),
                })),
              ]}
            />
            <NativeFilter
              ariaLabel="Filtrar por día"
              className="w-full"
              value={dayFilter}
              onChange={setDayFilter}
              options={[
                { value: "all", label: "Día: Todos" },
                ...days.map((date) => ({
                  value: date,
                  label: format(new Date(`${date}T12:00:00`), "d MMM yyyy"),
                })),
              ]}
            />
          </div>

          <div className="space-y-3 md:hidden">
            {filteredMeetings.length === 0 && (
              <div className="rounded-xl border border-border bg-card p-8 text-center">
                <FileText className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No se encontraron reuniones con esos filtros.</p>
              </div>
            )}
            {filteredMeetings.map((meeting) => {
              const simpleStatus = getSimpleClientStatus(meeting);
              const locked = isClientLocked(meeting);

              return (
                <button
                  key={meeting.id}
                  type="button"
                  className="w-full rounded-xl border border-border bg-card p-4 text-left shadow-sm"
                  onClick={() => openDrawer(meeting)}
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{meeting.company}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {meeting.firstName} {meeting.lastName} · {meeting.jobTitle}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-medium text-foreground">{format(new Date(meeting.meetingDate), "d MMM")}</p>
                      <p className="text-xs text-muted-foreground">{format(new Date(meeting.meetingDate), "HH:mm")}</p>
                    </div>
                  </div>
                  <div className="mb-3 flex flex-wrap gap-2">
                    <StatusBadge status={statusToBadge(simpleStatus)} label={simpleStatus} size="sm" />
                    <ValidationResultTooltip meeting={meeting} />
                  </div>
                  <div className="flex justify-end">
                    <span className={`rounded-lg px-3 py-1.5 text-sm font-medium ${locked ? "border border-border bg-background text-foreground" : "bg-violet-600 text-white"}`}>
                      {locked ? "Ver detalle" : "Validar"}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="hidden overflow-hidden rounded-xl border border-border bg-card md:block">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px]">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Fecha</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Empresa</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Nombre</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Apellido</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Cargo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Estado</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Resultado de revisión</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredMeetings.map((meeting) => {
                    const simpleStatus = getSimpleClientStatus(meeting);
                    const locked = isClientLocked(meeting);
                    return (
                      <tr key={meeting.id} className="cursor-pointer transition-colors hover:bg-muted/30" onClick={() => openDrawer(meeting)}>
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-foreground">{format(new Date(meeting.meetingDate), "d MMM")}</p>
                          <p className="text-xs text-muted-foreground">{format(new Date(meeting.meetingDate), "HH:mm")}</p>
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-foreground">{meeting.company}</td>
                        <td className="px-4 py-3 text-sm text-foreground">{meeting.firstName}</td>
                        <td className="px-4 py-3 text-sm text-foreground">{meeting.lastName || "-"}</td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">{meeting.jobTitle}</td>
                        <td className="px-4 py-3">
                          <StatusBadge status={statusToBadge(simpleStatus)} label={simpleStatus} size="sm" />
                        </td>
                        <td className="px-4 py-3">
                          <ValidationResultTooltip meeting={meeting} variant="table" />
                        </td>
                        <td className="px-4 py-3">
                          <Button
                            variant={locked ? "outline" : "default"}
                            size="sm"
                            className={locked ? "" : "bg-violet-600 text-white hover:bg-violet-700"}
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
            {filteredMeetings.length === 0 && (
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

function ValidationResultTooltip({
  meeting,
  variant = "compact",
}: {
  meeting: Meeting;
  variant?: "compact" | "table";
}) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger render={<span className="inline-flex" />}>
          <span
            className={
              variant === "table"
                ? "inline-flex cursor-help items-center gap-2 text-sm text-foreground"
                : "inline-flex cursor-help items-center gap-1 rounded-full border border-violet-100 bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700"
            }
          >
            <ShieldCheck className={variant === "table" ? "h-4 w-4 text-violet-600" : "h-3 w-3"} />
            {getValidationResultLabel(meeting)}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-[320px] text-xs leading-5">
          {getValidationTooltip(meeting)}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
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
      className={`h-8 rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50 ${className ?? ""}`}
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
