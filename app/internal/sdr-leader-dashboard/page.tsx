"use client";

import { useMemo, useState } from "react";
import { useApp } from "@/lib/app-context";
import { KPICard } from "@/components/kpi-card";
import { StatusBadge } from "@/components/status-badge";
import { DemoDisabledButton } from "@/components/demo-disabled-button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  RefreshCw,
  Calendar,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Target,
  TrendingUp,
  Users,
  CalendarCheck,
  ClipboardCheck,
  AlertCircle,
  Building2,
  ArrowRight,
} from "lucide-react";
import { clientContracts, sdrs, alerts } from "@/lib/mock-data";
import { format, parseISO, isToday, differenceInDays } from "date-fns";
import {
  meetingStatusLabels,
  cpValidationLabels,
  clientValidationLabels,
  finalValidationLabels,
} from "@/lib/types";

export default function SDRLeaderDashboardPage() {
  const { meetings } = useApp();
  const [activeTab, setActiveTab] = useState("overview");
  const contract = clientContracts[0];

  // Calculate all KPIs
  const kpis = useMemo(() => {
    const today = new Date();
    const clientMeetings = meetings.filter((m) => m.client === "GBS Logistics");
    
    // Today's metrics
    const meetingsToday = clientMeetings.filter((m) => isToday(parseISO(m.meetingDate)));
    const scheduledToday = meetingsToday.filter((m) => m.meetingStatus === "scheduled").length;
    const completedToday = meetingsToday.filter((m) => m.meetingStatus === "completed").length;
    
    // Validation metrics
    const pendingCPValidation = clientMeetings.filter((m) => m.cpValidation === "waiting_validation").length;
    const pendingClientValidation = clientMeetings.filter((m) => m.clientValidation === "waiting_client_validation").length;
    const inDispute = clientMeetings.filter((m) => m.finalValidation === "in_dispute").length;
    const finalValid = clientMeetings.filter((m) => m.finalValidation === "final_valid").length;
    const rebooked = clientMeetings.filter((m) => m.meetingStatus === "rescheduled").length;
    
    // Goal calculations
    const goalProgress = Math.round((finalValid / contract.contractGoal) * 100);
    const futureScheduled = clientMeetings.filter(
      (m) => m.meetingStatus === "scheduled" && new Date(m.meetingDate) > today
    ).length;
    const projectedProgress = Math.round(((finalValid + futureScheduled) / contract.contractGoal) * 100);
    
    // Expected progress
    const contractStart = parseISO(contract.activeProspectingStartDate);
    const contractEnd = parseISO(contract.contractEndDate);
    const totalDays = differenceInDays(contractEnd, contractStart);
    const elapsedDays = differenceInDays(today, contractStart);
    const expectedMeetings = Math.round((elapsedDays / totalDays) * contract.contractGoal);

    return {
      scheduledToday,
      completedToday,
      pendingCPValidation,
      pendingClientValidation,
      inDispute,
      finalValid,
      rebooked,
      goalProgress,
      projectedProgress,
      contractGoal: contract.contractGoal,
      expectedMeetings,
      futureScheduled,
    };
  }, [meetings, contract]);

  // Meetings requiring attention (validation queue)
  const validationQueue = useMemo(() => {
    return meetings
      .filter(
        (m) =>
          m.client === "GBS Logistics" &&
          (m.cpValidation === "waiting_validation" ||
            m.cpValidation === "requires_review" ||
            m.clientValidation === "waiting_client_validation")
      )
      .sort((a, b) => new Date(a.meetingDate).getTime() - new Date(b.meetingDate).getTime());
  }, [meetings]);

  // Disputes
  const disputes = useMemo(() => {
    return meetings.filter((m) => m.client === "GBS Logistics" && m.finalValidation === "in_dispute");
  }, [meetings]);

  // Client progress data
  const clientProgress = useMemo(() => {
    const clientMeetings = meetings.filter((m) => m.client === "GBS Logistics");
    const finalValid = clientMeetings.filter((m) => m.finalValidation === "final_valid").length;
    const futureScheduled = clientMeetings.filter(
      (m) => m.meetingStatus === "scheduled" && new Date(m.meetingDate) > new Date()
    ).length;
    
    return {
      name: "GBS Logistics",
      goal: contract.contractGoal,
      actual: finalValid,
      projected: finalValid + futureScheduled,
      expected: kpis.expectedMeetings,
      status: finalValid >= kpis.expectedMeetings ? "on_track" : "at_risk",
    };
  }, [meetings, contract, kpis.expectedMeetings]);

  // SDR Performance summary
  const sdrPerformance = useMemo(() => {
    return sdrs.map((sdr) => {
      const sdrMeetings = meetings.filter((m) => m.sdrAssigned === sdr.name);
      const completed = sdrMeetings.filter((m) => m.meetingStatus === "completed").length;
      const valid = sdrMeetings.filter((m) => m.finalValidation === "final_valid").length;
      const pending = sdrMeetings.filter(
        (m) => m.cpValidation === "waiting_validation" || m.clientValidation === "waiting_client_validation"
      ).length;
      
      return {
        ...sdr,
        completed,
        valid,
        pending,
        validRate: completed > 0 ? Math.round((valid / completed) * 100) : 0,
      };
    });
  }, [meetings]);

  return (
    <div className="flex-1 overflow-hidden">
      {/* Header */}
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Panel líder SDR</h1>
            <p className="text-sm text-muted-foreground">
              Conprospección OS · Control operativo · {format(new Date(), "MMMM d, yyyy")} · Datos demo · Prototipo funcional
            </p>
          </div>
          <div className="flex gap-2">
            <Select defaultValue="all">
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Client" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los clientes</SelectItem>
                <SelectItem value="gbs">GBS Logistics</SelectItem>
              </SelectContent>
            </Select>
            <DemoDisabledButton className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Actualizar
            </DemoDisabledButton>
          </div>
        </div>
      </header>

      <ScrollArea className="h-[calc(100vh-65px)]">
        <div className="p-6 space-y-6">
          {/* Today's Summary Banner */}
          <div className="bg-violet-50 border border-violet-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <CalendarCheck className="h-5 w-5 text-violet-600" />
              <h3 className="text-sm font-semibold text-violet-900">Resumen de hoy</h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-violet-600">Reuniones agendadas:</span>
                <span className="ml-2 font-bold text-violet-900">{kpis.scheduledToday}</span>
              </div>
              <div>
                <span className="text-violet-600">Reuniones realizadas:</span>
                <span className="ml-2 font-bold text-violet-900">{kpis.completedToday}</span>
              </div>
              <div>
                <span className="text-violet-600">Validación pendiente:</span>
                <span className="ml-2 font-bold text-violet-900">{kpis.pendingCPValidation + kpis.pendingClientValidation}</span>
              </div>
              <div>
                <span className="text-violet-600">Disputas:</span>
                <span className="ml-2 font-bold text-violet-900">{kpis.inDispute}</span>
              </div>
            </div>
          </div>

          {/* Main KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-10 gap-4">
            <KPICard
              title="Agendadas hoy"
              value={kpis.scheduledToday}
              icon={<Calendar className="h-5 w-5" />}
            />
            <KPICard
              title="Realizadas hoy"
              value={kpis.completedToday}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Pend. CP"
              value={kpis.pendingCPValidation}
              icon={<ClipboardCheck className="h-5 w-5" />}
              variant="warning"
            />
            <KPICard
              title="Pend. cliente"
              value={kpis.pendingClientValidation}
              icon={<Clock className="h-5 w-5" />}
              variant="warning"
            />
            <KPICard
              title="En disputa"
              value={kpis.inDispute}
              icon={<AlertTriangle className="h-5 w-5" />}
              variant="danger"
            />
            <KPICard
              title="Válidas finales"
              value={kpis.finalValid}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Reagendadas"
              value={kpis.rebooked}
              icon={<Calendar className="h-5 w-5" />}
            />
            <KPICard
              title="Avance meta"
              value={`${kpis.goalProgress}%`}
              icon={<Target className="h-5 w-5" />}
              variant="primary"
              trend={`${kpis.finalValid}/${kpis.contractGoal}`}
            />
            <KPICard
              title="Proyección"
              value={`${kpis.projectedProgress}%`}
              icon={<TrendingUp className="h-5 w-5" />}
              variant="primary"
            />
            <KPICard
              title="Esperado"
              value={kpis.expectedMeetings}
              icon={<Target className="h-5 w-5" />}
              trend="a hoy"
            />
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-muted/50">
              <TabsTrigger value="overview">Resumen</TabsTrigger>
              <TabsTrigger value="validation">Cola validación ({validationQueue.length})</TabsTrigger>
              <TabsTrigger value="disputes">Disputas ({disputes.length})</TabsTrigger>
              <TabsTrigger value="alerts">Alertas ({alerts.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-6 space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Client Progress Tracker */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Seguimiento de meta cliente</h3>
                  <div className={`p-4 rounded-lg border ${
                    clientProgress.status === "on_track" 
                      ? "bg-emerald-50 border-emerald-200" 
                      : "bg-amber-50 border-amber-200"
                  }`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white">
                          <Building2 className="h-5 w-5 text-violet-600" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-foreground">{clientProgress.name}</p>
                          <p className={`text-xs ${
                            clientProgress.status === "on_track" ? "text-emerald-600" : "text-amber-600"
                          }`}>
                            {clientProgress.status === "on_track" ? "En curso" : "En riesgo"}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-foreground">
                          {clientProgress.actual}/{clientProgress.goal}
                        </p>
                        <p className="text-xs text-muted-foreground">reuniones válidas</p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs">
                        <span>Esperado: {clientProgress.expected}</span>
                        <span>Actual: {clientProgress.actual}</span>
                        <span>Proyectado: {clientProgress.projected}</span>
                      </div>
                      <div className="h-3 bg-white rounded-full overflow-hidden flex">
                        <div 
                          className="bg-emerald-500 h-full"
                          style={{ width: `${(clientProgress.actual / clientProgress.goal) * 100}%` }}
                        />
                        <div 
                          className="bg-violet-300 h-full"
                          style={{ width: `${((clientProgress.projected - clientProgress.actual) / clientProgress.goal) * 100}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>0</span>
                        <span>Meta: {clientProgress.goal}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* SDR Performance Summary */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Performance SDR</h3>
                  <div className="space-y-3">
                    {sdrPerformance.map((sdr) => (
                      <div key={sdr.id} className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-100">
                          <Users className="h-5 w-5 text-violet-600" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">{sdr.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {sdr.completed} realizadas · {sdr.valid} válidas · {sdr.pending} pendientes
                          </p>
                        </div>
                        <div className="text-right">
                          <p className={`text-lg font-bold ${
                            sdr.validRate >= 70 ? "text-emerald-600" : sdr.validRate >= 50 ? "text-amber-600" : "text-rose-600"
                          }`}>
                            {sdr.validRate}%
                          </p>
                          <p className="text-xs text-muted-foreground">tasa válida</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Daily Meeting Follow-up */}
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="p-4 border-b border-border">
                  <h3 className="text-sm font-semibold text-foreground">Seguimiento diario de reuniones</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Reunión
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          SDR
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Estado
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Validación CP
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Validación cliente
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Final
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {meetings
                        .filter((m) => m.client === "GBS Logistics")
                        .slice(0, 8)
                        .map((meeting) => (
                          <tr key={meeting.id} className="hover:bg-muted/30 cursor-pointer">
                            <td className="px-4 py-3">
                              <div>
                                <p className="text-sm font-medium text-foreground">{meeting.company}</p>
                                <p className="text-xs text-muted-foreground">{meeting.contact}</p>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-sm text-foreground">{meeting.sdrAssigned}</span>
                            </td>
                            <td className="px-4 py-3">
                              <StatusBadge status={meeting.meetingStatus} label={meetingStatusLabels[meeting.meetingStatus]} />
                            </td>
                            <td className="px-4 py-3">
                              <StatusBadge status={meeting.cpValidation} label={cpValidationLabels[meeting.cpValidation]} />
                            </td>
                            <td className="px-4 py-3">
                              <StatusBadge status={meeting.clientValidation} label={clientValidationLabels[meeting.clientValidation]} />
                            </td>
                            <td className="px-4 py-3">
                              <StatusBadge status={meeting.finalValidation} label={finalValidationLabels[meeting.finalValidation]} />
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="validation" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="p-4 border-b border-border">
                  <h3 className="text-sm font-semibold text-foreground">Reuniones pendientes de validación</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Fecha
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Empresa
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Contacto
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          SDR
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Validación CP
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Validación cliente
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Acción
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {validationQueue.map((meeting) => (
                        <tr key={meeting.id} className="hover:bg-muted/30">
                          <td className="px-4 py-3">
                            <span className="text-sm text-foreground">
                              {format(parseISO(meeting.meetingDate), "MMM d, yyyy")}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm font-medium text-foreground">{meeting.company}</span>
                          </td>
                          <td className="px-4 py-3">
                            <div>
                              <p className="text-sm text-foreground">{meeting.contact}</p>
                              <p className="text-xs text-muted-foreground">{meeting.jobTitle}</p>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm text-foreground">{meeting.sdrAssigned}</span>
                          </td>
                          <td className="px-4 py-3">
                            <StatusBadge status={meeting.cpValidation} label={cpValidationLabels[meeting.cpValidation]} />
                          </td>
                          <td className="px-4 py-3">
                            <StatusBadge status={meeting.clientValidation} label={clientValidationLabels[meeting.clientValidation]} />
                          </td>
                          <td className="px-4 py-3">
                            <DemoDisabledButton variant="ghost" className="gap-1 text-violet-600">
                              Revisar <ArrowRight className="h-3 w-3" />
                            </DemoDisabledButton>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="disputes" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="p-4 border-b border-border">
                  <h3 className="text-sm font-semibold text-foreground">Reuniones en disputa</h3>
                </div>
                {disputes.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                            Reunión
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                            CP indica
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                            Cliente indica
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                            Comentario cliente
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                            Acción
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {disputes.map((meeting) => (
                          <tr key={meeting.id} className="hover:bg-muted/30">
                            <td className="px-4 py-3">
                              <div>
                                <p className="text-sm font-medium text-foreground">{meeting.company}</p>
                                <p className="text-xs text-muted-foreground">
                                  {meeting.contact} · {format(parseISO(meeting.meetingDate), "MMM d")}
                                </p>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <StatusBadge status={meeting.cpValidation} label={cpValidationLabels[meeting.cpValidation]} />
                            </td>
                            <td className="px-4 py-3">
                              <StatusBadge status={meeting.clientValidation} label={clientValidationLabels[meeting.clientValidation]} />
                            </td>
                            <td className="px-4 py-3">
                              <p className="text-sm text-foreground max-w-xs truncate">{meeting.clientComment}</p>
                            </td>
                            <td className="px-4 py-3">
                              <DemoDisabledButton className="gap-1 text-rose-600 border-rose-200 hover:bg-rose-50">
                                Resolver
                              </DemoDisabledButton>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <CheckCircle2 className="h-8 w-8 mb-2 text-emerald-500" />
                    <p className="text-sm">No hay disputas por resolver</p>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="alerts" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">Alertas operativas</h3>
                <div className="space-y-3">
                  {alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-4 rounded-lg border ${
                        alert.type === "danger"
                          ? "bg-rose-50 border-rose-200"
                          : alert.type === "warning"
                          ? "bg-amber-50 border-amber-200"
                          : alert.type === "success"
                          ? "bg-emerald-50 border-emerald-200"
                          : "bg-blue-50 border-blue-200"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <AlertCircle
                          className={`h-5 w-5 mt-0.5 ${
                            alert.type === "danger"
                              ? "text-rose-600"
                              : alert.type === "warning"
                              ? "text-amber-600"
                              : alert.type === "success"
                              ? "text-emerald-600"
                              : "text-blue-600"
                          }`}
                        />
                        <div className="flex-1">
                          <p
                            className={`text-sm font-medium ${
                              alert.type === "danger"
                                ? "text-rose-700"
                                : alert.type === "warning"
                                ? "text-amber-700"
                                : alert.type === "success"
                                ? "text-emerald-700"
                                : "text-blue-700"
                            }`}
                          >
                            {alert.title}
                          </p>
                          <p
                            className={`text-sm mt-1 ${
                              alert.type === "danger"
                                ? "text-rose-600"
                                : alert.type === "warning"
                                ? "text-amber-600"
                                : alert.type === "success"
                                ? "text-emerald-600"
                                : "text-blue-600"
                            }`}
                          >
                            {alert.description}
                          </p>
                          <p className="text-xs text-muted-foreground mt-2">
                            {format(parseISO(alert.timestamp), "MMM d, yyyy · h:mm a")}
                          </p>
                        </div>
                        <DemoDisabledButton variant="ghost" className="text-xs">
                          Descartar
                        </DemoDisabledButton>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </ScrollArea>
    </div>
  );
}

