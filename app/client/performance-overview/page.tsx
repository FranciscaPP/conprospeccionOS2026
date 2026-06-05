"use client";

import { useMemo } from "react";
import { useApp } from "@/lib/app-context";
import { KPICard } from "@/components/kpi-card";
import { DemoDisabledButton } from "@/components/demo-disabled-button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  RefreshCw,
  Download,
  Target,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Calendar,
  TrendingUp,
  TrendingDown,
  Building2,
  Globe,
  Factory,
  ArrowRight,
  CalendarClock,
  Briefcase,
} from "lucide-react";
import { clientContracts, campaigns, alerts } from "@/lib/mock-data";
import { format, differenceInDays, parseISO } from "date-fns";

export default function ClientPerformanceOverviewPage() {
  const { meetings } = useApp();
  const contract = clientContracts[0];

  // Calculate all KPIs from meetings
  const kpis = useMemo(() => {
    const clientMeetings = meetings.filter((m) => m.client === "GBS Logistics");
    const finalValid = clientMeetings.filter((m) => m.finalValidation === "final_valid").length;
    const pendingValidation = clientMeetings.filter(
      (m) => m.clientValidation === "waiting_client_validation" || m.cpValidation === "waiting_validation"
    ).length;
    const inDispute = clientMeetings.filter((m) => m.finalValidation === "in_dispute").length;
    const futureScheduled = clientMeetings.filter(
      (m) => m.meetingStatus === "scheduled" && new Date(m.meetingDate) > new Date()
    ).length;
    
    // Calculate progress percentages
    const goalProgress = Math.round((finalValid / contract.contractGoal) * 100);
    const projectedTotal = finalValid + futureScheduled;
    const projectedProgress = Math.round((projectedTotal / contract.contractGoal) * 100);
    
    // Calculate expected progress based on elapsed time
    const contractStart = parseISO(contract.activeProspectingStartDate);
    const contractEnd = parseISO(contract.contractEndDate);
    const today = new Date();
    const totalDays = differenceInDays(contractEnd, contractStart);
    const elapsedDays = differenceInDays(today, contractStart);
    const expectedProgress = Math.round((elapsedDays / totalDays) * 100);
    const expectedMeetings = Math.round((elapsedDays / totalDays) * contract.contractGoal);
    
    // Gap to target
    const gapToTarget = finalValid - expectedMeetings;

    return {
      finalValid,
      pendingValidation,
      inDispute,
      futureScheduled,
      goalProgress,
      projectedProgress,
      projectedTotal,
      expectedProgress,
      expectedMeetings,
      gapToTarget,
      contractGoal: contract.contractGoal,
    };
  }, [meetings, contract]);

  // Commercial outcomes
  const commercialOutcomes = useMemo(() => {
    const clientMeetings = meetings.filter((m) => m.client === "GBS Logistics" && m.finalValidation === "final_valid");
    return {
      clientWon: clientMeetings.filter((m) => m.commercialStatus === "client_won").length,
      negotiation: clientMeetings.filter((m) => m.commercialStatus === "negotiation").length,
      proposalSent: clientMeetings.filter((m) => ["proposal_sent", "proposal_followup", "requested_proposal"].includes(m.commercialStatus)).length,
      pending: clientMeetings.filter((m) => ["pending_followup", "next_step_scheduled"].includes(m.commercialStatus)).length,
      lost: clientMeetings.filter((m) => m.commercialStatus === "client_lost").length,
    };
  }, [meetings]);

  // Upcoming meetings
  const upcomingMeetings = useMemo(() => {
    return meetings
      .filter((m) => m.client === "GBS Logistics" && m.meetingStatus === "scheduled")
      .sort((a, b) => new Date(a.meetingDate).getTime() - new Date(b.meetingDate).getTime())
      .slice(0, 5);
  }, [meetings]);

  // Client alerts
  const clientAlerts = alerts.filter((a) => a.clientId === "GBS");

  return (
    <div className="flex-1 overflow-hidden">
      {/* Header */}
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Resumen de performance</h1>
            <p className="text-sm text-muted-foreground">
              {contract.clientName} · {contract.currentPeriod} · Meta contractual: {contract.contractGoal} reuniones · Datos demo · Prototipo funcional
            </p>
          </div>
          <div className="flex gap-2">
            <DemoDisabledButton className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Actualizar
            </DemoDisabledButton>
            <DemoDisabledButton className="gap-2">
              <Download className="h-4 w-4" />
              Exportar PDF
            </DemoDisabledButton>
          </div>
        </div>
      </header>

      <ScrollArea className="h-[calc(100vh-65px)]">
        <div className="p-6 space-y-6">
          {/* Contract Info Banner */}
          <div className="bg-violet-50 border border-violet-200 rounded-xl p-4">
            <div className="flex flex-wrap items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <CalendarClock className="h-4 w-4 text-violet-600" />
                <span className="text-violet-700">
                  <span className="font-medium">Prospección activa:</span>{" "}
                  {format(parseISO(contract.activeProspectingStartDate), "MMM d, yyyy")}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-violet-600" />
                <span className="text-violet-700">
                  <span className="font-medium">Contrato:</span>{" "}
                  {format(parseISO(contract.contractStartDate), "MMM d")} -{" "}
                  {format(parseISO(contract.contractEndDate), "MMM d, yyyy")}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-violet-600" />
                <span className="text-violet-700">
                  <span className="font-medium">Meta:</span> {contract.contractGoal} reuniones válidas finales
                </span>
              </div>
            </div>
          </div>

          {/* Main KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <KPICard
              title="Válidas finales"
              value={kpis.finalValid}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Validación pendiente"
              value={kpis.pendingValidation}
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
              title="Futuras agendadas"
              value={kpis.futureScheduled}
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
              title="Avance proyectado"
              value={`${kpis.projectedProgress}%`}
              icon={<TrendingUp className="h-5 w-5" />}
              variant="primary"
              trend={`${kpis.projectedTotal}/${kpis.contractGoal}`}
            />
          </div>

          {/* Progress Comparison Card */}
          <div className="bg-card border border-border rounded-xl p-6">
            <h3 className="text-sm font-semibold text-foreground mb-6">Comparación de avance de meta</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {/* Expected */}
              <div className="text-center p-4 bg-muted/30 rounded-lg">
                <div className="relative w-24 h-24 mx-auto mb-3">
                  <svg className="w-24 h-24 -rotate-90">
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      strokeWidth="8"
                      stroke="currentColor"
                      fill="none"
                      className="text-muted"
                    />
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      strokeWidth="8"
                      stroke="currentColor"
                      fill="none"
                      strokeDasharray={`${kpis.expectedProgress * 2.51} 251`}
                      className="text-slate-500"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-foreground">
                    {kpis.expectedProgress}%
                  </span>
                </div>
                <p className="text-sm font-medium text-foreground">Avance esperado</p>
                <p className="text-2xl font-bold text-slate-600 mt-1">{kpis.expectedMeetings}</p>
                <p className="text-xs text-muted-foreground">reuniones a hoy</p>
              </div>

              {/* Actual */}
              <div className="text-center p-4 bg-muted/30 rounded-lg">
                <div className="relative w-24 h-24 mx-auto mb-3">
                  <svg className="w-24 h-24 -rotate-90">
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      strokeWidth="8"
                      stroke="currentColor"
                      fill="none"
                      className="text-muted"
                    />
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      strokeWidth="8"
                      stroke="currentColor"
                      fill="none"
                      strokeDasharray={`${kpis.goalProgress * 2.51} 251`}
                      className={kpis.gapToTarget >= 0 ? "text-emerald-500" : "text-amber-500"}
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-foreground">
                    {kpis.goalProgress}%
                  </span>
                </div>
                <p className="text-sm font-medium text-foreground">Avance actual</p>
                <p className={`text-2xl font-bold mt-1 ${kpis.gapToTarget >= 0 ? "text-emerald-600" : "text-amber-600"}`}>
                  {kpis.finalValid}
                </p>
                <p className="text-xs text-muted-foreground">reuniones válidas finales</p>
              </div>

              {/* Projected */}
              <div className="text-center p-4 bg-muted/30 rounded-lg">
                <div className="relative w-24 h-24 mx-auto mb-3">
                  <svg className="w-24 h-24 -rotate-90">
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      strokeWidth="8"
                      stroke="currentColor"
                      fill="none"
                      className="text-muted"
                    />
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      strokeWidth="8"
                      stroke="currentColor"
                      fill="none"
                      strokeDasharray={`${kpis.projectedProgress * 2.51} 251`}
                      className="text-violet-500"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-foreground">
                    {kpis.projectedProgress}%
                  </span>
                </div>
                <p className="text-sm font-medium text-foreground">Avance proyectado</p>
                <p className="text-2xl font-bold text-violet-600 mt-1">{kpis.projectedTotal}</p>
                <p className="text-xs text-muted-foreground">válidas + agendadas</p>
              </div>

              {/* Goal */}
              <div className="text-center p-4 bg-violet-50 border border-violet-200 rounded-lg">
                <div className="relative w-24 h-24 mx-auto mb-3">
                  <svg className="w-24 h-24 -rotate-90">
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      strokeWidth="8"
                      stroke="currentColor"
                      fill="none"
                      className="text-violet-200"
                    />
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      strokeWidth="8"
                      stroke="currentColor"
                      fill="none"
                      strokeDasharray="251 251"
                      className="text-violet-500"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-violet-700">
                    100%
                  </span>
                </div>
                <p className="text-sm font-medium text-violet-700">Meta contractual</p>
                <p className="text-2xl font-bold text-violet-600 mt-1">{kpis.contractGoal}</p>
                <p className="text-xs text-violet-600">reuniones totales</p>
              </div>
            </div>

            {/* Gap indicator */}
            <div className={`mt-6 p-4 rounded-lg flex items-center justify-between ${
              kpis.gapToTarget >= 0 ? "bg-emerald-50 border border-emerald-200" : "bg-amber-50 border border-amber-200"
            }`}>
              <div className="flex items-center gap-3">
                {kpis.gapToTarget >= 0 ? (
                  <TrendingUp className="h-5 w-5 text-emerald-600" />
                ) : (
                  <TrendingDown className="h-5 w-5 text-amber-600" />
                )}
                <div>
                  <p className={`text-sm font-medium ${kpis.gapToTarget >= 0 ? "text-emerald-700" : "text-amber-700"}`}>
                    Brecha contra avance esperado
                  </p>
                  <p className={`text-xs ${kpis.gapToTarget >= 0 ? "text-emerald-600" : "text-amber-600"}`}>
                    {kpis.gapToTarget >= 0
                      ? `Estás ${kpis.gapToTarget} reunión${kpis.gapToTarget !== 1 ? "es" : ""} sobre lo esperado`
                      : `Estás ${Math.abs(kpis.gapToTarget)} reunión${Math.abs(kpis.gapToTarget) !== 1 ? "es" : ""} bajo lo esperado`}
                  </p>
                </div>
              </div>
              <span className={`text-2xl font-bold ${kpis.gapToTarget >= 0 ? "text-emerald-600" : "text-amber-600"}`}>
                {kpis.gapToTarget >= 0 ? "+" : ""}{kpis.gapToTarget}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Campaign Performance */}
            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Performance por campaña</h3>
              <div className="space-y-3">
                {campaigns.map((campaign) => (
                  <div key={campaign.id} className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-foreground">{campaign.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {campaign.contactsReached} contactos · {campaign.replies} respuestas · {campaign.meetings} reuniones
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-emerald-600">{campaign.validMeetings}</p>
                      <p className="text-xs text-muted-foreground">válidas</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Performance by Country */}
            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Performance por país</h3>
              <div className="space-y-3">
                {[
                  { country: "Chile", contacts: 420, meetings: 6, valid: 5 },
                  { country: "Peru", contacts: 180, meetings: 2, valid: 1 },
                  { country: "Colombia", contacts: 120, meetings: 1, valid: 0 },
                  { country: "Argentina", contacts: 64, meetings: 0, valid: 0 },
                ].map((item) => (
                  <div key={item.country} className="flex items-center gap-3">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-foreground w-24">{item.country}</span>
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-violet-500"
                        style={{ width: `${(item.valid / 5) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-foreground w-8 text-right">{item.valid}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Performance by Industry */}
            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Performance por industria</h3>
              <div className="space-y-3">
                {[
                  { industry: "Mining & Metals", meetings: 4, valid: 3 },
                  { industry: "Retail", meetings: 3, valid: 2 },
                  { industry: "Pharma", meetings: 2, valid: 1 },
                  { industry: "Automotive", meetings: 2, valid: 1 },
                  { industry: "Food & Beverage", meetings: 1, valid: 0 },
                ].map((item) => (
                  <div key={item.industry} className="flex items-center gap-3">
                    <Factory className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-foreground w-32">{item.industry}</span>
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500"
                        style={{ width: `${(item.valid / 3) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-foreground w-8 text-right">{item.valid}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Commercial Outcome */}
            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Resultado comercial</h3>
              <div className="grid grid-cols-5 gap-3">
                <div className="text-center p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                  <p className="text-2xl font-bold text-emerald-600">{commercialOutcomes.clientWon}</p>
                  <p className="text-xs text-emerald-700 mt-1">Ganado</p>
                </div>
                <div className="text-center p-3 bg-violet-50 border border-violet-200 rounded-lg">
                  <p className="text-2xl font-bold text-violet-600">{commercialOutcomes.negotiation}</p>
                  <p className="text-xs text-violet-700 mt-1">Negociación</p>
                </div>
                <div className="text-center p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">{commercialOutcomes.proposalSent}</p>
                  <p className="text-xs text-blue-700 mt-1">Propuesta</p>
                </div>
                <div className="text-center p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-2xl font-bold text-amber-600">{commercialOutcomes.pending}</p>
                  <p className="text-xs text-amber-700 mt-1">Seguimiento</p>
                </div>
                <div className="text-center p-3 bg-rose-50 border border-rose-200 rounded-lg">
                  <p className="text-2xl font-bold text-rose-600">{commercialOutcomes.lost}</p>
                  <p className="text-xs text-rose-700 mt-1">Perdido</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Upcoming Meetings */}
            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Próximas reuniones</h3>
              {upcomingMeetings.length > 0 ? (
                <div className="space-y-3">
                  {upcomingMeetings.map((meeting) => (
                    <div key={meeting.id} className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100">
                        <Calendar className="h-5 w-5 text-violet-600" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">{meeting.company}</p>
                        <p className="text-xs text-muted-foreground">
                          {meeting.contact} · {meeting.jobTitle}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-foreground">
                          {format(parseISO(meeting.meetingDate), "MMM d")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {format(parseISO(meeting.meetingDate), "h:mm a")}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <Calendar className="h-8 w-8 mb-2" />
                  <p className="text-sm">No hay próximas reuniones agendadas</p>
                </div>
              )}
            </div>

            {/* Risk Alerts */}
            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-foreground mb-4">Alertas de riesgo</h3>
              <div className="space-y-3">
                {clientAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-3 rounded-lg border ${
                      alert.type === "danger"
                        ? "bg-rose-50 border-rose-200"
                        : alert.type === "warning"
                        ? "bg-amber-50 border-amber-200"
                        : alert.type === "success"
                        ? "bg-emerald-50 border-emerald-200"
                        : "bg-blue-50 border-blue-200"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <AlertTriangle
                        className={`h-4 w-4 mt-0.5 ${
                          alert.type === "danger"
                            ? "text-rose-600"
                            : alert.type === "warning"
                            ? "text-amber-600"
                            : alert.type === "success"
                            ? "text-emerald-600"
                            : "text-blue-600"
                        }`}
                      />
                      <div>
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
                          className={`text-xs mt-0.5 ${
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
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}

