"use client";

import { useMemo, useState } from "react";
import type React from "react";
import {
  AlertTriangle,
  Calendar,
  CalendarCheck,
  CheckCircle2,
  ChevronRight,
  Clock,
  Flag,
  RefreshCw,
  Search,
  Target,
  UserCheck,
  XCircle,
} from "lucide-react";
import { format, isSameWeek, isToday, isTomorrow } from "date-fns";
import { es } from "date-fns/locale";
import { useApp } from "@/lib/app-context";
import { DemoDisabledButton } from "@/components/demo-disabled-button";
import { MeetingDrawer } from "@/components/meeting-drawer";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { FinalValidation, Meeting, MeetingStatus } from "@/lib/types";
import {
  clientDecisionLabels,
  finalValidationLabels,
  meetingStatusLabels,
} from "@/lib/types";
import {
  getClientPriority,
  getDaysRemainingInMonth,
  getValidationResultLabel,
  getInternalSearchText,
  isFinalValid,
  MONTHLY_GOAL_BY_CLIENT,
  splitContactName,
} from "@/lib/meeting-rules";

type QuickFilter =
  | "all"
  | "today"
  | "tomorrow"
  | "week"
  | "pending"
  | "validated"
  | "rejected"
  | "review"
  | "rescheduled"
  | "no_show";

const quickFilterLabels: Record<QuickFilter, string> = {
  all: "Todas",
  today: "Hoy",
  tomorrow: "Mañana",
  week: "Esta semana",
  pending: "Pendientes",
  validated: "Validadas",
  rejected: "Rechazadas",
  review: "En revisión",
  rescheduled: "Reagendadas",
  no_show: "No realizadas",
};

const statusToBadge = (meeting: Meeting): MeetingStatus | FinalValidation => {
  if (meeting.meetingStatus === "no_show") return "no_show";
  if (meeting.meetingStatus === "rescheduled") return "rescheduled";
  if (meeting.finalValidation === "final_valid") return "completed";
  if (meeting.finalValidation === "final_not_valid") return "final_not_valid";
  if (meeting.finalValidation === "in_dispute" || meeting.clientDecision === "review_requested") return "pending";
  if (meeting.clientDecision === "pending") return "scheduled";
  return meeting.meetingStatus;
};

export default function InternalMeetingFollowupPage() {
  const { meetings } = useApp();
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [quickFilter, setQuickFilter] = useState<QuickFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [clientFilter, setClientFilter] = useState("all");
  const [sdrFilter, setSdrFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("all");
  const [companyFilter, setCompanyFilter] = useState("all");
  const [countryFilter, setCountryFilter] = useState("all");

  const today = new Date();
  const daysRemaining = getDaysRemainingInMonth(today);

  const clients = useMemo(() => [...new Set(meetings.map((m) => m.client))].sort(), [meetings]);
  const sdrs = useMemo(() => [...new Set(meetings.map((m) => m.sdrAssigned))].sort(), [meetings]);
  const companies = useMemo(() => [...new Set(meetings.map((m) => m.company))].sort(), [meetings]);
  const countries = useMemo(
    () => [...new Set(meetings.map((m) => m.country).filter(Boolean))].sort() as string[],
    [meetings]
  );

  const quickCounts = useMemo(() => {
    const count = (filter: QuickFilter) =>
      meetings.filter((meeting) => matchesQuickFilter(meeting, filter, today)).length;

    return {
      today: count("today"),
      tomorrow: count("tomorrow"),
      week: count("week"),
      pending: count("pending"),
      validated: count("validated"),
      rejected: count("rejected"),
      review: count("review"),
      rescheduled: count("rescheduled"),
      no_show: count("no_show"),
    };
  }, [meetings, today]);

  const clientProgress = useMemo(() => {
    return clients
      .map((client) => {
        const clientMeetings = meetings.filter((meeting) => meeting.client === client);
        const goal = MONTHLY_GOAL_BY_CLIENT[client] ?? 10;
        const validated = clientMeetings.filter(isFinalValid).length;
        const pending = clientMeetings.filter((meeting) => meeting.clientDecision === "pending").length;
        const rejected = clientMeetings.filter((meeting) => meeting.clientDecision === "rejected").length;
        const review = clientMeetings.filter((meeting) => meeting.clientDecision === "review_requested").length;
        const projection = Math.min(goal, validated + pending);
        const gap = Math.max(goal - validated, 0);
        const priority = getClientPriority(validated, pending, goal, daysRemaining) as "Alta" | "Media" | "Baja";
        const progress = Math.min(Math.round((validated / goal) * 100), 100);

        return {
          client,
          goal,
          validated,
          pending,
          rejected,
          review,
          projection,
          gap,
          priority,
          progress,
        };
      })
      .sort((a, b) => {
        const order: Record<"Alta" | "Media" | "Baja", number> = { Alta: 0, Media: 1, Baja: 2 };
        return order[a.priority] - order[b.priority] || b.gap - a.gap;
      });
  }, [clients, daysRemaining, meetings]);

  const filteredMeetings = useMemo(() => {
    const search = searchQuery.trim().toLowerCase();

    return meetings.filter((meeting) => {
      const meetingDate = new Date(meeting.meetingDate);
      const matchesSearch = search === "" || getInternalSearchText(meeting).includes(search);
      const matchesClient = clientFilter === "all" || meeting.client === clientFilter;
      const matchesSdr = sdrFilter === "all" || meeting.sdrAssigned === sdrFilter;
      const matchesStatus =
        statusFilter === "all" ||
        meeting.meetingStatus === statusFilter ||
        meeting.clientDecision === statusFilter ||
        meeting.finalValidation === statusFilter;
      const matchesDate =
        dateFilter === "all" ||
        (dateFilter === "today" && isToday(meetingDate)) ||
        (dateFilter === "tomorrow" && isTomorrow(meetingDate)) ||
        (dateFilter === "week" && isSameWeek(meetingDate, today, { weekStartsOn: 1 }));
      const matchesCompany = companyFilter === "all" || meeting.company === companyFilter;
      const matchesCountry = countryFilter === "all" || meeting.country === countryFilter;
      const matchesQuick = matchesQuickFilter(meeting, quickFilter, today);

      return (
        matchesSearch &&
        matchesClient &&
        matchesSdr &&
        matchesStatus &&
        matchesDate &&
        matchesCompany &&
        matchesCountry &&
        matchesQuick
      );
    });
  }, [
    clientFilter,
    companyFilter,
    countryFilter,
    dateFilter,
    meetings,
    quickFilter,
    searchQuery,
    sdrFilter,
    statusFilter,
    today,
  ]);

  const riskClients = clientProgress.filter((client) => client.priority === "Alta").slice(0, 3);
  const closeClients = clientProgress
    .filter((client) => client.validated >= client.goal || client.gap <= 1)
    .slice(0, 3);

  const openDrawer = (meeting: Meeting) => {
    setSelectedMeeting(meeting);
    setDrawerOpen(true);
  };

  return (
    <div className="flex-1 overflow-hidden">
      <header className="border-b border-border bg-card px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-lg font-semibold text-foreground sm:text-xl">Seguimiento interno de reuniones</h1>
            <p className="max-w-full break-words text-sm leading-5 text-muted-foreground">
              Control diario por cliente, estado contractual y prioridad operativa.
            </p>
          </div>
          <DemoDisabledButton className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </DemoDisabledButton>
        </div>
      </header>

      <ScrollArea className="h-[calc(100dvh-7rem)] lg:h-[calc(100vh-65px)]">
        <main className="space-y-4 p-4 sm:space-y-6 sm:p-6">
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5 xl:grid-cols-9">
            <QuickKPI
              active={quickFilter === "today"}
              icon={<Calendar className="h-4 w-4" />}
              label="Hoy"
              value={quickCounts.today}
              onClick={() => setQuickFilter(quickFilter === "today" ? "all" : "today")}
            />
            <QuickKPI
              active={quickFilter === "tomorrow"}
              icon={<CalendarCheck className="h-4 w-4" />}
              label="Mañana"
              value={quickCounts.tomorrow}
              onClick={() => setQuickFilter(quickFilter === "tomorrow" ? "all" : "tomorrow")}
            />
            <QuickKPI
              active={quickFilter === "week"}
              icon={<Clock className="h-4 w-4" />}
              label="Semana"
              value={quickCounts.week}
              onClick={() => setQuickFilter(quickFilter === "week" ? "all" : "week")}
            />
            <QuickKPI
              active={quickFilter === "pending"}
              icon={<UserCheck className="h-4 w-4" />}
              label="Pendientes"
              value={quickCounts.pending}
              tone="warning"
              onClick={() => setQuickFilter(quickFilter === "pending" ? "all" : "pending")}
            />
            <QuickKPI
              active={quickFilter === "validated"}
              icon={<CheckCircle2 className="h-4 w-4" />}
              label="Validadas"
              value={quickCounts.validated}
              tone="success"
              onClick={() => setQuickFilter(quickFilter === "validated" ? "all" : "validated")}
            />
            <QuickKPI
              active={quickFilter === "rejected"}
              icon={<XCircle className="h-4 w-4" />}
              label="Rechazadas"
              value={quickCounts.rejected}
              tone="danger"
              onClick={() => setQuickFilter(quickFilter === "rejected" ? "all" : "rejected")}
            />
            <QuickKPI
              active={quickFilter === "review"}
              icon={<AlertTriangle className="h-4 w-4" />}
              label="En revisión"
              value={quickCounts.review}
              tone="warning"
              onClick={() => setQuickFilter(quickFilter === "review" ? "all" : "review")}
            />
            <QuickKPI
              active={quickFilter === "rescheduled"}
              icon={<CalendarCheck className="h-4 w-4" />}
              label="Reagendadas"
              value={quickCounts.rescheduled}
              onClick={() => setQuickFilter(quickFilter === "rescheduled" ? "all" : "rescheduled")}
            />
            <QuickKPI
              active={quickFilter === "no_show"}
              icon={<XCircle className="h-4 w-4" />}
              label="No realizadas"
              value={quickCounts.no_show}
              tone="danger"
              onClick={() => setQuickFilter(quickFilter === "no_show" ? "all" : "no_show")}
            />
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
            <div className="rounded-xl border border-border bg-card">
              <div className="flex flex-col gap-3 border-b border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <h2 className="text-sm font-semibold text-foreground">Prioridad de clientes</h2>
                  <p className="text-xs text-muted-foreground">
                    Proyección interna simple: validadas finales + pendientes de validación cliente.
                  </p>
                </div>
                <div className="flex flex-col items-start rounded-lg bg-muted px-3 py-2 sm:block sm:text-right">
                  <p className="text-[11px] font-medium uppercase text-muted-foreground">Días restantes</p>
                  <p className="text-lg font-semibold text-foreground">{daysRemaining}</p>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[680px]">
                  <thead className="bg-muted/50">
                    <tr>
                      {["Cliente", "Meta", "Validadas", "Pendientes", "Brecha", "Proyección", "Prioridad"].map(
                        (heading) => (
                          <th
                            key={heading}
                            className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground"
                          >
                            {heading}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {clientProgress.map((client) => (
                      <tr key={client.client} className="hover:bg-muted/30">
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-foreground">{client.client}</p>
                          <Progress value={client.progress} className="mt-2 h-1.5" />
                        </td>
                        <td className="px-4 py-3 text-sm text-foreground">{client.goal}</td>
                        <td className="px-4 py-3 text-sm font-medium text-emerald-700">{client.validated}</td>
                        <td className="px-4 py-3 text-sm text-amber-700">{client.pending}</td>
                        <td className="px-4 py-3 text-sm text-foreground">{client.gap}</td>
                        <td className="px-4 py-3 text-sm text-foreground">{client.projection}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${priorityClass(client.priority)}`}>
                            {client.priority}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
              <ClientSummaryBlock
                title="Clientes en riesgo"
                empty="Sin clientes críticos hoy"
                items={riskClients.map((client) => ({
                  name: client.client,
                  meta: `${client.validated}/${client.goal}`,
                  detail: `Brecha ${client.gap}, ${client.pending} pendientes`,
                  tone: "danger",
                }))}
              />
              <ClientSummaryBlock
                title="Clientes cerca de cumplir"
                empty="Ningún cliente cerca de meta"
                items={closeClients.map((client) => ({
                  name: client.client,
                  meta: `${client.validated}/${client.goal}`,
                  detail: client.validated >= client.goal ? "Meta cumplida" : `Brecha ${client.gap}`,
                  tone: "success",
                }))}
              />
            </div>
          </section>

          <section className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Reuniones</h2>
                <p className="text-xs text-muted-foreground">
                  Filtro activo: {quickFilterLabels[quickFilter]} · {filteredMeetings.length} resultado(s)
                </p>
              </div>
              {quickFilter !== "all" && (
                <Button variant="outline" size="sm" onClick={() => setQuickFilter("all")}>
                  Limpiar KPI
                </Button>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-7">
              <div className="relative md:col-span-2">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-9"
                  placeholder="Buscar cliente, empresa, contacto, cargo o SDR"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </div>
              <FilterSelect label="Cliente" value={clientFilter} onChange={setClientFilter} values={clients} />
              <FilterSelect label="SDR" value={sdrFilter} onChange={setSdrFilter} values={sdrs} />
              <NativeFilter
                label="Estado"
                value={statusFilter}
                onChange={setStatusFilter}
                options={[
                  { value: "all", label: "Estado: todos" },
                  { value: "scheduled", label: "Agendada" },
                  { value: "completed", label: "Realizada" },
                  { value: "pending", label: "Pendiente validación" },
                  { value: "final_valid", label: "Validada" },
                  { value: "final_not_valid", label: "Rechazada" },
                  { value: "in_dispute", label: "En revisión" },
                  { value: "rescheduled", label: "Reagendada" },
                  { value: "no_show", label: "No realizada" },
                ]}
              />
              <NativeFilter
                label="Fecha"
                value={dateFilter}
                onChange={setDateFilter}
                options={[
                  { value: "all", label: "Fecha: todas" },
                  { value: "today", label: "Hoy" },
                  { value: "tomorrow", label: "Mañana" },
                  { value: "week", label: "Esta semana" },
                ]}
              />
              <FilterSelect label="Empresa" value={companyFilter} onChange={setCompanyFilter} values={companies} />
              <FilterSelect label="País" value={countryFilter} onChange={setCountryFilter} values={countries} />
            </div>
          </section>

          <section className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1180px]">
                <thead className="bg-muted/50">
                  <tr>
                    {[
                      "Fecha",
                      "Cliente",
                      "Empresa",
                      "Nombre",
                      "Apellido",
                      "Cargo",
                      "País",
                      "SDR",
                      "Estado reunión",
                      "Estado validación",
                      "Resultado",
                      "Acción",
                    ].map((heading) => (
                      <th
                        key={heading}
                        className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredMeetings.map((meeting) => {
                    const names = splitContactName(meeting.contact);
                    const firstName = meeting.firstName || names.firstName;
                    const lastName = meeting.lastName || names.lastName;

                    return (
                      <tr key={meeting.id} className="hover:bg-muted/30">
                        <td className="px-3 py-3">
                          <p className="text-xs font-medium text-foreground">
                            {format(new Date(meeting.meetingDate), "dd MMM", { locale: es })}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {format(new Date(meeting.meetingDate), "HH:mm")}
                          </p>
                        </td>
                        <td className="px-3 py-3 text-xs font-medium text-foreground">{meeting.client}</td>
                        <td className="px-3 py-3 text-xs text-foreground">{meeting.company}</td>
                        <td className="px-3 py-3 text-xs text-foreground">{firstName}</td>
                        <td className="px-3 py-3 text-xs text-foreground">{lastName}</td>
                        <td className="px-3 py-3 text-xs text-muted-foreground">{meeting.jobTitle}</td>
                        <td className="px-3 py-3 text-xs text-muted-foreground">{meeting.country ?? "Sin dato"}</td>
                        <td className="px-3 py-3 text-xs text-muted-foreground">{meeting.sdrAssigned}</td>
                        <td className="px-3 py-3">
                          <StatusBadge
                            status={statusToBadge(meeting)}
                            label={meetingStatusLabels[meeting.meetingStatus]}
                            size="sm"
                          />
                        </td>
                        <td className="px-3 py-3">
                          <StatusBadge
                            status={statusToBadge(meeting)}
                            label={clientDecisionLabels[meeting.clientDecision ?? "pending"]}
                            size="sm"
                          />
                        </td>
                        <td className="px-3 py-3">
                          <StatusBadge
                            status={statusToBadge(meeting)}
                            label={getValidationResultLabel(meeting)}
                            size="sm"
                          />
                          <p className="mt-1 text-[11px] text-muted-foreground">
                            BANT {meeting.bantScore ?? meeting.cpBANT.length}/4
                          </p>
                        </td>
                        <td className="px-3 py-3">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="gap-1 text-violet-700"
                            onClick={() => openDrawer(meeting)}
                          >
                            Ver detalle
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {filteredMeetings.length === 0 && (
              <div className="py-10 text-center">
                <Flag className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No hay reuniones con estos filtros.</p>
              </div>
            )}
          </section>
        </main>
      </ScrollArea>

      <MeetingDrawer
        meeting={selectedMeeting}
        mode="internal"
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedMeeting(null);
        }}
      />
    </div>
  );
}

function matchesQuickFilter(meeting: Meeting, filter: QuickFilter, today: Date) {
  const meetingDate = new Date(meeting.meetingDate);

  if (filter === "all") return true;
  if (filter === "today") return isToday(meetingDate);
  if (filter === "tomorrow") return isTomorrow(meetingDate);
  if (filter === "week") return isSameWeek(meetingDate, today, { weekStartsOn: 1 });
  if (filter === "pending") return meeting.clientDecision === "pending";
  if (filter === "validated") return isFinalValid(meeting);
  if (filter === "rejected") return meeting.clientDecision === "rejected" || meeting.finalValidation === "final_not_valid";
  if (filter === "review") return meeting.clientDecision === "review_requested" || meeting.finalValidation === "in_dispute";
  if (filter === "rescheduled") return meeting.meetingStatus === "rescheduled";
  if (filter === "no_show") return meeting.meetingStatus === "no_show" || meeting.finalValidation === "final_not_valid";
  return true;
}

function priorityClass(priority: string) {
  if (priority === "Alta") return "border-rose-200 bg-rose-50 text-rose-700";
  if (priority === "Media") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function QuickKPI({
  active,
  icon,
  label,
  onClick,
  tone = "default",
  value,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  tone?: "default" | "success" | "warning" | "danger";
  value: number;
}) {
  const toneClass = {
    default: "border-border bg-card text-foreground",
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
    danger: "border-rose-200 bg-rose-50 text-rose-800",
  }[tone];

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border p-3 text-left transition hover:border-violet-300 hover:bg-violet-50 ${
        active ? "border-violet-300 bg-violet-50 ring-2 ring-violet-100" : toneClass
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-muted-foreground">{icon}</span>
        <span className="text-xl font-semibold text-foreground">{value}</span>
      </div>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
    </button>
  );
}

function ClientSummaryBlock({
  empty,
  items,
  title,
}: {
  empty: string;
  items: Array<{ detail: string; meta: string; name: string; tone: "danger" | "success" }>;
  title: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h2 className="mb-3 text-sm font-semibold text-foreground">{title}</h2>
      {items.length === 0 ? (
        <p className="rounded-lg bg-muted px-3 py-4 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.name} className="rounded-lg border border-border p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-foreground">{item.name}</p>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    item.tone === "danger"
                      ? "bg-rose-100 text-rose-700"
                      : "bg-emerald-100 text-emerald-700"
                  }`}
                >
                  {item.meta}
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{item.detail}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  onChange,
  value,
  values,
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
  values: string[];
}) {
  return (
    <NativeFilter
      label={label}
      value={value}
      onChange={onChange}
      options={[
        { value: "all", label: `${label}: todos` },
        ...values.map((item) => ({ value: item, label: item })),
      ]}
    />
  );
}

function NativeFilter({
  label,
  onChange,
  options,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  options: Array<{ label: string; value: string }>;
  value: string;
}) {
  return (
    <select
      aria-label={`Filtrar por ${label.toLowerCase()}`}
      className="h-8 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/50"
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
