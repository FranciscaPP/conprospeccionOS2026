"use client";

import { useMemo, useState } from "react";
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
  Target,
} from "lucide-react";
import { useApp } from "@/lib/app-context";
import { KPICard } from "@/components/kpi-card";
import { StatusBadge } from "@/components/status-badge";
import { MeetingDrawer } from "@/components/meeting-drawer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { FinalValidation, Meeting, MeetingStatus } from "@/lib/types";
import {
  getClientDecision,
  getClientSearchText,
  getSimpleClientStatus,
  getValidationResultLabel,
  isClientLocked,
  MONTHLY_GOAL_BY_CLIENT,
} from "@/lib/meeting-rules";

function statusToBadge(status: string): FinalValidation | MeetingStatus {
  if (status === "Validada") return "final_valid";
  if (status === "Rechazada" || status === "No realizada") return "final_not_valid";
  if (status === "En revisión") return "in_dispute";
  if (status === "Reagendada") return "rescheduled";
  return "pending";
}

export default function MeetingValidationPage() {
  const { meetings } = useApp();
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("all");
  const [companyFilter, setCompanyFilter] = useState("all");

  const clientMeetings = useMemo(
    () => meetings.filter((meeting) => meeting.client === "GBS Logistics"),
    [meetings]
  );

  const goal = MONTHLY_GOAL_BY_CLIENT["GBS Logistics"] ?? 10;

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

  const companies = useMemo(
    () => [...new Set(clientMeetings.map((meeting) => meeting.company))],
    [clientMeetings]
  );

  const dates = useMemo(
    () => [...new Set(clientMeetings.map((meeting) => meeting.meetingDate.slice(0, 10)))].sort(),
    [clientMeetings]
  );

  const filteredMeetings = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return clientMeetings.filter((meeting) => {
      const simpleStatus = getSimpleClientStatus(meeting);
      const matchesSearch = !query || getClientSearchText(meeting).includes(query);
      const matchesStatus = statusFilter === "all" || simpleStatus === statusFilter;
      const matchesCompany = companyFilter === "all" || meeting.company === companyFilter;
      const matchesDate = dateFilter === "all" || meeting.meetingDate.slice(0, 10) === dateFilter;
      return matchesSearch && matchesStatus && matchesCompany && matchesDate;
    });
  }, [clientMeetings, searchQuery, statusFilter, companyFilter, dateFilter]);

  const openDrawer = (meeting: Meeting) => {
    setSelectedMeeting(meeting);
    setDrawerOpen(true);
  };

  return (
    <div className="flex-1 overflow-hidden">
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Validación de reuniones</h1>
            <p className="text-sm text-muted-foreground">
              GBS Logistics · Revisión contractual de reuniones entregadas
            </p>
          </div>
          {kpis.pending > 0 && (
            <div className="hidden items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800 md:flex">
              <Clock className="h-4 w-4" />
              {kpis.pending} requieren tu validación
            </div>
          )}
        </div>
      </header>

      <ScrollArea className="h-[calc(100vh-65px)]">
        <div className="space-y-6 p-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KPICard title="Total generadas" value={kpis.total} icon={<Calendar className="h-5 w-5" />} />
            <KPICard title="Válidas finales" value={kpis.finalValid} icon={<CheckCircle2 className="h-5 w-5" />} variant="success" />
            <KPICard title="Pendientes de tu validación" value={kpis.pending} icon={<Clock className="h-5 w-5" />} variant="warning" />
            <KPICard title="Objetadas / en disputa" value={kpis.rejected + kpis.disputed} icon={<AlertTriangle className="h-5 w-5" />} variant="danger" />
          </div>

          <section className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Avance de meta contractual</h3>
                <p className="text-xs text-muted-foreground">Se consideran solo reuniones válidas finales.</p>
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
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-foreground">¿Qué es una reunión válida?</h3>
                <p className="text-sm leading-6 text-muted-foreground">
                  Cuenta para la meta cuando el prospecto asistió, pertenece a una región válida, corresponde a la persona o área acordada y cumple al menos 2 de 4 criterios BANT: presupuesto, autoridad, necesidad y horizonte de tiempo. La validez no depende de que el negocio se gane o se pierda después.
                </p>
              </div>
            </div>
          </section>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[220px] flex-1">
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
              className="w-[220px]"
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: "all", label: "Estado: todos" },
                ...["Pendiente de validación", "Validada", "Rechazada", "En revisión", "Reagendada", "No realizada"].map((status) => ({
                  value: status,
                  label: status,
                })),
              ]}
            />
            <NativeFilter
              ariaLabel="Filtrar por fecha"
              className="w-[180px]"
              value={dateFilter}
              onChange={setDateFilter}
              options={[
                { value: "all", label: "Fecha: todas" },
                ...dates.map((date) => ({
                  value: date,
                  label: format(new Date(`${date}T12:00:00`), "d MMM yyyy"),
                })),
              ]}
            />
            <NativeFilter
              ariaLabel="Filtrar por empresa"
              className="w-[200px]"
              value={companyFilter}
              onChange={setCompanyFilter}
              options={[
                { value: "all", label: "Empresa: todas" },
                ...companies.map((company) => ({ value: company, label: company })),
              ]}
            />
          </div>

          <div className="overflow-hidden rounded-xl border border-border bg-card">
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
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">Resultado Conprospección</th>
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
                          <div className="flex items-center gap-2">
                            <ShieldCheck className="h-4 w-4 text-violet-600" />
                            <span className="text-sm text-foreground">{getValidationResultLabel(meeting)}</span>
                          </div>
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
