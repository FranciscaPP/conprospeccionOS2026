"use client";

import { useState, useMemo } from "react";
import { useApp } from "@/lib/app-context";
import { KPICard } from "@/components/kpi-card";
import { StatusBadge } from "@/components/status-badge";
import { MeetingDrawer } from "@/components/meeting-drawer";
import { DemoDisabledButton } from "@/components/demo-disabled-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Calendar,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Target,
  RefreshCw,
  Search,
  ChevronRight,
  Building2,
  Users,
  XCircle,
  TrendingUp,
  Flag,
} from "lucide-react";
import { format } from "date-fns";
import type { Meeting } from "@/lib/types";
import {
  meetingStatusLabels,
  cpValidationLabels,
  clientValidationLabels,
  finalValidationLabels,
  commercialStatusLabels,
  bantLabels,
} from "@/lib/types";

export default function InternalMeetingFollowupPage() {
  const { meetings } = useApp();
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [clientFilter, setClientFilter] = useState<string>("all");
  const [sdrFilter, setSdrFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [cpValidationFilter, setCpValidationFilter] = useState<string>("all");
  const [clientValidationFilter, setClientValidationFilter] = useState<string>("all");
  const [finalValidationFilter, setFinalValidationFilter] = useState<string>("all");
  const [disputeFilter, setDisputeFilter] = useState<string>("all");

  // Calculate KPIs
  const kpis = useMemo(() => {
    const scheduled = meetings.filter((m) => m.meetingStatus === "scheduled").length;
    const completed = meetings.filter((m) => m.meetingStatus === "completed").length;
    const pendingCpValidation = meetings.filter(
      (m) => m.cpValidation === "waiting_validation"
    ).length;
    const pendingClientValidation = meetings.filter(
      (m) => m.clientValidation === "waiting_client_validation"
    ).length;
    const cpValid = meetings.filter((m) => m.cpValidation === "valid_cp").length;
    const clientValid = meetings.filter((m) => m.clientValidation === "valid_client").length;
    const finalValid = meetings.filter((m) => m.finalValidation === "final_valid").length;
    const inDispute = meetings.filter((m) => m.finalValidation === "in_dispute").length;
    const goal = 45;
    const officialProgress = Math.round((finalValid / goal) * 100);
    // Projected includes valid CP that are waiting client validation
    const projected = finalValid + meetings.filter(
      (m) => m.cpValidation === "valid_cp" && m.clientValidation === "waiting_client_validation"
    ).length;
    const projectedProgress = Math.round((projected / goal) * 100);

    return {
      scheduled,
      completed,
      pendingCpValidation,
      pendingClientValidation,
      cpValid,
      clientValid,
      finalValid,
      inDispute,
      goal,
      officialProgress,
      projectedProgress,
    };
  }, [meetings]);

  // Get unique values for filters
  const clients = useMemo(() => [...new Set(meetings.map((m) => m.client))], [meetings]);
  const sdrs = useMemo(() => [...new Set(meetings.map((m) => m.sdrAssigned))], [meetings]);

  // Apply filters
  const filteredMeetings = useMemo(() => {
    return meetings.filter((meeting) => {
      const matchesSearch =
        searchQuery === "" ||
        meeting.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
        meeting.contact.toLowerCase().includes(searchQuery.toLowerCase()) ||
        meeting.sdrAssigned.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesClient = clientFilter === "all" || meeting.client === clientFilter;
      const matchesSdr = sdrFilter === "all" || meeting.sdrAssigned === sdrFilter;
      const matchesStatus = statusFilter === "all" || meeting.meetingStatus === statusFilter;
      const matchesCpValidation =
        cpValidationFilter === "all" || meeting.cpValidation === cpValidationFilter;
      const matchesClientValidation =
        clientValidationFilter === "all" ||
        meeting.clientValidation === clientValidationFilter;
      const matchesFinalValidation =
        finalValidationFilter === "all" ||
        meeting.finalValidation === finalValidationFilter;
      const matchesDispute =
        disputeFilter === "all" ||
        (disputeFilter === "yes" && meeting.disputeFlag) ||
        (disputeFilter === "no" && !meeting.disputeFlag);

      return (
        matchesSearch &&
        matchesClient &&
        matchesSdr &&
        matchesStatus &&
        matchesCpValidation &&
        matchesClientValidation &&
        matchesFinalValidation &&
        matchesDispute
      );
    });
  }, [
    meetings,
    searchQuery,
    clientFilter,
    sdrFilter,
    statusFilter,
    cpValidationFilter,
    clientValidationFilter,
    finalValidationFilter,
    disputeFilter,
  ]);

  const handleRowClick = (meeting: Meeting) => {
    setSelectedMeeting(meeting);
    setDrawerOpen(true);
  };

  return (
    <div className="flex-1 overflow-hidden">
      {/* Header */}
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Seguimiento interno de reuniones</h1>
            <p className="text-sm text-muted-foreground">
              Conprospección OS · Control operativo · Datos demo · Prototipo funcional
            </p>
          </div>
          <DemoDisabledButton className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </DemoDisabledButton>
        </div>
      </header>

      <ScrollArea className="h-[calc(100vh-65px)]">
        <div className="p-6 space-y-6">
          {/* KPI Cards - 2 rows */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <KPICard
              title="Agendadas"
              value={kpis.scheduled}
              icon={<Calendar className="h-5 w-5" />}
            />
            <KPICard
              title="Realizadas"
              value={kpis.completed}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Pend. CP"
              value={kpis.pendingCpValidation}
              icon={<Clock className="h-5 w-5" />}
              variant="warning"
            />
            <KPICard
              title="Pend. cliente"
              value={kpis.pendingClientValidation}
              icon={<Clock className="h-5 w-5" />}
              variant="warning"
            />
            <KPICard
              title="Válidas CP"
              value={kpis.cpValid}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <KPICard
              title="Válidas cliente"
              value={kpis.clientValid}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Válidas finales"
              value={kpis.finalValid}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="En disputa"
              value={kpis.inDispute}
              icon={<AlertTriangle className="h-5 w-5" />}
              variant="danger"
            />
            <KPICard
              title="Avance oficial"
              value={`${kpis.finalValid}/${kpis.goal}`}
              trend={`${kpis.officialProgress}%`}
              icon={<Target className="h-5 w-5" />}
              variant="primary"
            />
            <KPICard
              title="Proyección"
              value={`${kpis.projectedProgress}%`}
              icon={<TrendingUp className="h-5 w-5" />}
              variant="primary"
            />
          </div>

          {/* Filters - Multiple rows */}
          <div className="bg-card border border-border rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-medium text-foreground">Filtros</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
              <div className="relative col-span-2">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select value={clientFilter} onValueChange={(value) => value && setClientFilter(value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Cliente" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Cliente: todos</SelectItem>
                  {clients.map((client) => (
                    <SelectItem key={client} value={client}>
                      {client}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={sdrFilter} onValueChange={(value) => value && setSdrFilter(value)}>
                <SelectTrigger>
                  <SelectValue placeholder="SDR" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">SDR: todos</SelectItem>
                  {sdrs.map((sdr) => (
                    <SelectItem key={sdr} value={sdr}>
                      {sdr}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={(value) => value && setStatusFilter(value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Estado: todos</SelectItem>
                  {Object.entries(meetingStatusLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={cpValidationFilter} onValueChange={(value) => value && setCpValidationFilter(value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Validación CP" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">CP: todos</SelectItem>
                  {Object.entries(cpValidationLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={clientValidationFilter} onValueChange={(value) => value && setClientValidationFilter(value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Validación cliente" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Cliente: todos</SelectItem>
                  {Object.entries(clientValidationLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={finalValidationFilter} onValueChange={(value) => value && setFinalValidationFilter(value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Final Val" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Final: todos</SelectItem>
                  {Object.entries(finalValidationLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={disputeFilter} onValueChange={(value) => value && setDisputeFilter(value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Disputa" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Disputa: todas</SelectItem>
                  <SelectItem value="yes">En disputa</SelectItem>
                  <SelectItem value="no">Sin disputa</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Goal Progress Bars */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-card rounded-xl border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="text-sm font-medium text-foreground">Avance oficial de meta</h3>
                  <p className="text-xs text-muted-foreground">
                    Basado en reuniones válidas finales
                  </p>
                </div>
                <span className="text-lg font-bold text-violet-600">
                  {kpis.finalValid}/{kpis.goal} · {kpis.officialProgress}%
                </span>
              </div>
              <Progress value={kpis.officialProgress} className="h-2" />
            </div>
            <div className="bg-card rounded-xl border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="text-sm font-medium text-foreground">Avance proyectado de meta</h3>
                  <p className="text-xs text-muted-foreground">
                    Incluye CP válidas pendientes de validación cliente
                  </p>
                </div>
                <span className="text-lg font-bold text-emerald-600">
                  {kpis.projectedProgress}%
                </span>
              </div>
              <Progress value={kpis.projectedProgress} className="h-2 [&>div]:bg-emerald-500" />
            </div>
          </div>

          {/* Meeting Table */}
          <div className="bg-card rounded-xl border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Cliente
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      SDR
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Fecha
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Empresa / contacto
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      CP Val
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      CP BANT
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Cliente
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Final
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Comercial
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Flags
                    </th>
                    <th className="text-left px-3 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Acción
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredMeetings.map((meeting) => (
                    <tr
                      key={meeting.id}
                      className="hover:bg-muted/30 transition-colors cursor-pointer"
                      onClick={() => handleRowClick(meeting)}
                    >
                      <td className="px-3 py-3">
                        <span className="text-xs font-medium text-foreground">{meeting.client}</span>
                      </td>
                      <td className="px-3 py-3">
                        <span className="text-xs text-muted-foreground">{meeting.sdrAssigned}</span>
                      </td>
                      <td className="px-3 py-3">
                        <p className="text-xs text-foreground">
                          {format(new Date(meeting.meetingDate), "MMM d")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(meeting.meetingDate), "HH:mm")}
                        </p>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-violet-100">
                            <span className="text-xs font-semibold text-violet-700">
                              {meeting.company.charAt(0)}
                            </span>
                          </div>
                          <div>
                            <p className="text-xs font-medium text-foreground">{meeting.company}</p>
                            <p className="text-xs text-muted-foreground">
                              {meeting.contact}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge
                          status={meeting.meetingStatus}
                          label={meetingStatusLabels[meeting.meetingStatus]}
                          size="sm"
                        />
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge
                          status={meeting.cpValidation}
                          label={cpValidationLabels[meeting.cpValidation].replace("CP", "").trim()}
                          size="sm"
                        />
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex gap-0.5">
                          {meeting.cpBANT.length > 0 ? (
                            meeting.cpBANT.map((b) => (
                              <span
                                key={b}
                                className="px-1.5 py-0.5 text-xs font-medium rounded bg-violet-100 text-violet-700"
                              >
                                {bantLabels[b].charAt(0)}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge
                          status={meeting.clientValidation}
                          label={clientValidationLabels[meeting.clientValidation].replace("client", "").trim()}
                          size="sm"
                        />
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge
                          status={meeting.finalValidation}
                          label={finalValidationLabels[meeting.finalValidation]}
                          size="sm"
                        />
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge
                          status={meeting.commercialStatus}
                          label={commercialStatusLabels[meeting.commercialStatus]}
                          size="sm"
                        />
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex gap-1">
                          {meeting.disputeFlag && (
                            <span className="flex h-5 w-5 items-center justify-center rounded bg-orange-100" title="En disputa">
                              <AlertTriangle className="h-3 w-3 text-orange-600" />
                            </span>
                          )}
                          {meeting.pendingClientFlag && (
                            <span className="flex h-5 w-5 items-center justify-center rounded bg-amber-100" title="Pendiente cliente">
                              <Clock className="h-3 w-3 text-amber-600" />
                            </span>
                          )}
                          {!meeting.disputeFlag && !meeting.pendingClientFlag && (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <Button variant="ghost" size="sm" className="gap-1 text-violet-600 h-7 px-2">
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredMeetings.length === 0 && (
              <div className="p-8 text-center">
                <Building2 className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">No se encontraron reuniones</p>
              </div>
            )}
          </div>
        </div>
      </ScrollArea>

      {/* Meeting Drawer */}
      <MeetingDrawer
        meeting={selectedMeeting}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedMeeting(null);
        }}
        mode="internal"
      />
    </div>
  );
}

