"use client";

import { useMemo, useState } from "react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  RefreshCw,
  Download,
  Phone,
  Mail,
  MessageCircle,
  Calendar,
  CheckCircle2,
  Target,
  TrendingUp,
  Users,
  Clock,
  Award,
  DollarSign,
  BarChart3,
  Globe,
  Factory,
  Building2,
} from "lucide-react";
import { sdrs, sdrActivities, campaigns, clientContracts } from "@/lib/mock-data";
import { format, parseISO } from "date-fns";

export default function SDRPerformancePage() {
  const { meetings } = useApp();
  const [selectedSDR, setSelectedSDR] = useState<string>("all");
  const [activeTab, setActiveTab] = useState("overview");
  const contract = clientContracts[0];

  // Calculate SDR metrics
  const sdrMetrics = useMemo(() => {
    return sdrs.map((sdr) => {
      const sdrMeetings = meetings.filter((m) => m.sdrAssigned === sdr.name);
      const sdrActivity = sdrActivities.filter((a) => a.sdrId === sdr.id);
      
      // Activity totals
      const callsMade = sdrActivity.reduce((sum, a) => sum + a.callsMade, 0);
      const callMinutes = sdrActivity.reduce((sum, a) => sum + a.callMinutes, 0);
      const emailsSent = sdrActivity.reduce((sum, a) => sum + a.emailsSent, 0);
      const whatsappMessages = sdrActivity.reduce((sum, a) => sum + a.whatsappMessages, 0);
      const linkedinMessages = sdrActivity.reduce((sum, a) => sum + a.linkedinMessages, 0);
      
      // Meeting metrics
      const meetingsBooked = sdrMeetings.length;
      const meetingsCompleted = sdrMeetings.filter((m) => m.meetingStatus === "completed").length;
      const finalValid = sdrMeetings.filter((m) => m.finalValidation === "final_valid").length;
      const clientWon = sdrMeetings.filter((m) => m.commercialStatus === "client_won").length;
      
      // Conversion rates
      const callHours = callMinutes / 60;
      const meetingsPerCallHour = callHours > 0 ? (meetingsBooked / callHours).toFixed(2) : "0";
      const totalContacts = callsMade + emailsSent + linkedinMessages;
      const meetingsPer100Contacts = totalContacts > 0 ? ((meetingsBooked / totalContacts) * 100).toFixed(1) : "0";
      const validMeetingRate = meetingsCompleted > 0 ? Math.round((finalValid / meetingsCompleted) * 100) : 0;
      
      // Estimated payment calculation
      const variablePayment = finalValid * sdr.variableRate;
      const bonusPayment = finalValid >= sdr.bonusThreshold ? sdr.bonusAmount : 0;
      const totalPayment = sdr.baseSalary + variablePayment + bonusPayment;
      
      return {
        ...sdr,
        callsMade,
        callMinutes,
        emailsSent,
        whatsappMessages,
        linkedinMessages,
        meetingsBooked,
        meetingsCompleted,
        finalValid,
        clientWon,
        meetingsPerCallHour,
        meetingsPer100Contacts,
        validMeetingRate,
        variablePayment,
        bonusPayment,
        totalPayment,
      };
    });
  }, [meetings]);

  // Filter metrics based on selected SDR
  const displayMetrics = selectedSDR === "all" 
    ? sdrMetrics 
    : sdrMetrics.filter((s) => s.id === selectedSDR);

  // Aggregated totals
  const totals = useMemo(() => {
    const metrics = selectedSDR === "all" ? sdrMetrics : sdrMetrics.filter((s) => s.id === selectedSDR);
    return {
      callsMade: metrics.reduce((sum, s) => sum + s.callsMade, 0),
      callMinutes: metrics.reduce((sum, s) => sum + s.callMinutes, 0),
      emailsSent: metrics.reduce((sum, s) => sum + s.emailsSent, 0),
      whatsappMessages: metrics.reduce((sum, s) => sum + s.whatsappMessages, 0),
      linkedinMessages: metrics.reduce((sum, s) => sum + s.linkedinMessages, 0),
      meetingsBooked: metrics.reduce((sum, s) => sum + s.meetingsBooked, 0),
      meetingsCompleted: metrics.reduce((sum, s) => sum + s.meetingsCompleted, 0),
      finalValid: metrics.reduce((sum, s) => sum + s.finalValid, 0),
      clientWon: metrics.reduce((sum, s) => sum + s.clientWon, 0),
    };
  }, [sdrMetrics, selectedSDR]);

  // Daily activity data for charts
  const dailyActivity = useMemo(() => {
    const filtered = selectedSDR === "all" 
      ? sdrActivities 
      : sdrActivities.filter((a) => a.sdrId === selectedSDR);
    
    const byDate: Record<string, { calls: number; emails: number; meetings: number }> = {};
    filtered.forEach((a) => {
      if (!byDate[a.date]) {
        byDate[a.date] = { calls: 0, emails: 0, meetings: 0 };
      }
      byDate[a.date].calls += a.callsMade;
      byDate[a.date].emails += a.emailsSent;
      byDate[a.date].meetings += a.meetingsBooked;
    });
    
    return Object.entries(byDate)
      .map(([date, data]) => ({ date, ...data }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [selectedSDR]);

  // Performance by client
  const performanceByClient = useMemo(() => {
    const filtered = selectedSDR === "all"
      ? meetings
      : meetings.filter((m) => sdrs.find((s) => s.id === selectedSDR)?.name === m.sdrAssigned);
    
    const byClient: Record<string, { meetings: number; valid: number; won: number }> = {};
    filtered.forEach((m) => {
      if (!byClient[m.client]) {
        byClient[m.client] = { meetings: 0, valid: 0, won: 0 };
      }
      byClient[m.client].meetings++;
      if (m.finalValidation === "final_valid") byClient[m.client].valid++;
      if (m.commercialStatus === "client_won") byClient[m.client].won++;
    });
    
    return Object.entries(byClient).map(([client, data]) => ({ client, ...data }));
  }, [meetings, selectedSDR]);

  // SDR Ranking
  const ranking = useMemo(() => {
    return [...sdrMetrics].sort((a, b) => b.finalValid - a.finalValid);
  }, [sdrMetrics]);

  return (
    <div className="flex-1 overflow-hidden">
      {/* Header */}
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Performance SDR</h1>
            <p className="text-sm text-muted-foreground">
              Conprospección OS · Analítica SDR detallada · Junio 2026
            </p>
          </div>
          <div className="flex gap-2">
            <Select value={selectedSDR} onValueChange={(value) => value && setSelectedSDR(value)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Seleccionar SDR" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los SDR</SelectItem>
                {sdrs.map((sdr) => (
                  <SelectItem key={sdr.id} value={sdr.id}>
                    {sdr.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <DemoDisabledButton className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Actualizar
            </DemoDisabledButton>
            <DemoDisabledButton className="gap-2">
              <Download className="h-4 w-4" />
              Exportar
            </DemoDisabledButton>
          </div>
        </div>
      </header>

      <ScrollArea className="h-[calc(100vh-65px)]">
        <div className="p-6 space-y-6">
          {/* Activity KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <KPICard
              title="Llamadas"
              value={totals.callsMade}
              icon={<Phone className="h-5 w-5" />}
            />
            <KPICard
              title="Minutos llamada"
              value={totals.callMinutes}
              icon={<Clock className="h-5 w-5" />}
              trend={`${(totals.callMinutes / 60).toFixed(1)}h`}
            />
            <KPICard
              title="Emails enviados"
              value={totals.emailsSent}
              icon={<Mail className="h-5 w-5" />}
            />
            <KPICard
              title="WhatsApp"
              value={totals.whatsappMessages}
              icon={<MessageCircle className="h-5 w-5" />}
            />
            <KPICard
              title="LinkedIn"
              value={totals.linkedinMessages}
              icon={<Users className="h-5 w-5" />}
            />
            <KPICard
              title="Outreach total"
              value={totals.callsMade + totals.emailsSent + totals.linkedinMessages}
              icon={<TrendingUp className="h-5 w-5" />}
              variant="primary"
            />
          </div>

          {/* Meeting KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <KPICard
              title="Reuniones agendadas"
              value={totals.meetingsBooked}
              icon={<Calendar className="h-5 w-5" />}
            />
            <KPICard
              title="Reuniones realizadas"
              value={totals.meetingsCompleted}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Válidas finales"
              value={totals.finalValid}
              icon={<Target className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Clientes ganados"
              value={totals.clientWon}
              icon={<Award className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Tasa válida"
              value={`${totals.meetingsCompleted > 0 ? Math.round((totals.finalValid / totals.meetingsCompleted) * 100) : 0}%`}
              icon={<BarChart3 className="h-5 w-5" />}
              variant="primary"
            />
            <KPICard
              title="Tasa cierre"
              value={`${totals.finalValid > 0 ? Math.round((totals.clientWon / totals.finalValid) * 100) : 0}%`}
              icon={<TrendingUp className="h-5 w-5" />}
              variant="primary"
            />
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-muted/50">
              <TabsTrigger value="overview">Resumen</TabsTrigger>
              <TabsTrigger value="ranking">Ranking SDR</TabsTrigger>
              <TabsTrigger value="trends">Tendencias diarias</TabsTrigger>
              <TabsTrigger value="breakdown">Detalle performance</TabsTrigger>
              <TabsTrigger value="payment">Pago estimado</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-6 space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Conversion Metrics */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Métricas de conversión</h3>
                  <div className="space-y-4">
                    {displayMetrics.map((sdr) => (
                      <div key={sdr.id} className="p-4 bg-muted/30 rounded-lg">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-100">
                              <Users className="h-5 w-5 text-violet-600" />
                            </div>
                            <div>
                              <p className="text-sm font-semibold text-foreground">{sdr.name}</p>
                              <p className="text-xs text-muted-foreground">{sdr.assignedClients.join(", ")}</p>
                            </div>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div className="p-2 bg-white rounded-lg">
                            <p className="text-lg font-bold text-violet-600">{sdr.meetingsPerCallHour}</p>
                            <p className="text-xs text-muted-foreground">Reuniones/hora llamada</p>
                          </div>
                          <div className="p-2 bg-white rounded-lg">
                            <p className="text-lg font-bold text-emerald-600">{sdr.meetingsPer100Contacts}%</p>
                            <p className="text-xs text-muted-foreground">Reuniones/100 contactos</p>
                          </div>
                          <div className="p-2 bg-white rounded-lg">
                            <p className="text-lg font-bold text-blue-600">{sdr.validMeetingRate}%</p>
                            <p className="text-xs text-muted-foreground">Tasa reunión válida</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Activity vs Results */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Actividad vs resultados</h3>
                  <div className="space-y-4">
                    {displayMetrics.map((sdr) => (
                      <div key={sdr.id} className="p-4 bg-muted/30 rounded-lg">
                        <p className="text-sm font-semibold text-foreground mb-3">{sdr.name}</p>
                        <div className="space-y-3">
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-muted-foreground">Volumen actividad</span>
                              <span className="text-foreground font-medium">
                                {sdr.callsMade + sdr.emailsSent + sdr.linkedinMessages} contactos
                              </span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-violet-500"
                                style={{ width: `${Math.min(((sdr.callsMade + sdr.emailsSent + sdr.linkedinMessages) / 800) * 100, 100)}%` }}
                              />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-muted-foreground">Reuniones agendadas</span>
                              <span className="text-foreground font-medium">{sdr.meetingsBooked} reuniones</span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-blue-500"
                                style={{ width: `${Math.min((sdr.meetingsBooked / 10) * 100, 100)}%` }}
                              />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-muted-foreground">Válidas finales</span>
                              <span className="text-foreground font-medium">{sdr.finalValid} válidas</span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-emerald-500"
                                style={{ width: `${Math.min((sdr.finalValid / 8) * 100, 100)}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="ranking" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="p-4 border-b border-border">
                  <h3 className="text-sm font-semibold text-foreground">Ranking SDR por reuniones válidas finales</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Rank
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          SDR
                        </th>
                        <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Llamadas
                        </th>
                        <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Emails
                        </th>
                        <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Reuniones
                        </th>
                        <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Realizadas
                        </th>
                        <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Válidas finales
                        </th>
                        <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Tasa válida
                        </th>
                        <th className="text-center px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Cliente ganado
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {ranking.map((sdr, index) => (
                        <tr key={sdr.id} className="hover:bg-muted/30">
                          <td className="px-4 py-3">
                            <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
                              index === 0 ? "bg-amber-100 text-amber-600" :
                              index === 1 ? "bg-slate-100 text-slate-600" :
                              index === 2 ? "bg-orange-100 text-orange-600" :
                              "bg-muted text-muted-foreground"
                            } font-bold text-sm`}>
                              {index + 1}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-100">
                                <Users className="h-5 w-5 text-violet-600" />
                              </div>
                              <div>
                                <p className="text-sm font-medium text-foreground">{sdr.name}</p>
                                <p className="text-xs text-muted-foreground">{sdr.email}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="text-sm text-foreground">{sdr.callsMade}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="text-sm text-foreground">{sdr.emailsSent}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="text-sm text-foreground">{sdr.meetingsBooked}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="text-sm text-foreground">{sdr.meetingsCompleted}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="text-sm font-bold text-emerald-600">{sdr.finalValid}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`text-sm font-medium ${
                              sdr.validMeetingRate >= 70 ? "text-emerald-600" :
                              sdr.validMeetingRate >= 50 ? "text-amber-600" :
                              "text-rose-600"
                            }`}>
                              {sdr.validMeetingRate}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="text-sm font-bold text-violet-600">{sdr.clientWon}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="trends" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">Daily Activity Trend</h3>
                <div className="space-y-4">
                  {dailyActivity.map((day) => (
                    <div key={day.date} className="flex items-center gap-4">
                      <span className="text-sm text-muted-foreground w-24">
                        {format(parseISO(day.date), "MMM d")}
                      </span>
                      <div className="flex-1 flex gap-2">
                        <div className="flex-1">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-muted-foreground">Llamadas</span>
                            <span className="text-foreground">{day.calls}</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-violet-500"
                              style={{ width: `${Math.min((day.calls / 150) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex-1">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-muted-foreground">Emails</span>
                            <span className="text-foreground">{day.emails}</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500"
                              style={{ width: `${Math.min((day.emails / 200) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex-1">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-muted-foreground">Reuniones</span>
                            <span className="text-foreground">{day.meetings}</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-500"
                              style={{ width: `${Math.min((day.meetings / 8) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="breakdown" className="mt-6 space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Performance by Client */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Performance por cliente</h3>
                  <div className="space-y-3">
                    {performanceByClient.map((item) => (
                      <div key={item.client} className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                        <Building2 className="h-5 w-5 text-muted-foreground" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">{item.client}</p>
                          <p className="text-xs text-muted-foreground">
                            {item.meetings} reuniones · {item.valid} válidas · {item.won} ganadas
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-emerald-600">
                            {item.meetings > 0 ? Math.round((item.valid / item.meetings) * 100) : 0}%
                          </p>
                          <p className="text-xs text-muted-foreground">tasa válida</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Performance by Campaign */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Performance por campaña</h3>
                  <div className="space-y-3">
                    {campaigns.slice(0, 5).map((campaign) => (
                      <div key={campaign.id} className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                        <Factory className="h-5 w-5 text-muted-foreground" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">{campaign.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {campaign.industry} · {campaign.country}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-violet-600">{campaign.validMeetings}</p>
                          <p className="text-xs text-muted-foreground">reuniones válidas</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="payment" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">Cálculo de pago estimado</h3>
                <div className="space-y-4">
                  {displayMetrics.map((sdr) => (
                    <div key={sdr.id} className="p-4 bg-muted/30 rounded-lg">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-100">
                            <Users className="h-6 w-6 text-violet-600" />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-foreground">{sdr.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {sdr.finalValid} reuniones válidas · {sdr.finalValid >= sdr.bonusThreshold ? "Bono calificado" : `${sdr.bonusThreshold - sdr.finalValid} más para bono`}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-emerald-600">
                            ${(sdr.totalPayment / 1000).toFixed(0)}K
                          </p>
                          <p className="text-xs text-muted-foreground">total estimado</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-4">
                        <div className="p-3 bg-white rounded-lg text-center">
                          <p className="text-lg font-bold text-foreground">
                            ${(sdr.baseSalary / 1000).toFixed(0)}K
                          </p>
                          <p className="text-xs text-muted-foreground">Sueldo base</p>
                        </div>
                        <div className="p-3 bg-white rounded-lg text-center">
                          <p className="text-lg font-bold text-violet-600">
                            ${(sdr.variablePayment / 1000).toFixed(0)}K
                          </p>
                          <p className="text-xs text-muted-foreground">Variable ({sdr.finalValid} x $50K)</p>
                        </div>
                        <div className="p-3 bg-white rounded-lg text-center">
                          <p className={`text-lg font-bold ${sdr.bonusPayment > 0 ? "text-amber-600" : "text-muted-foreground"}`}>
                            ${(sdr.bonusPayment / 1000).toFixed(0)}K
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Bono {sdr.bonusPayment > 0 ? "(Calificado)" : `(Necesita ${sdr.bonusThreshold})`}
                          </p>
                        </div>
                        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-center">
                          <p className="text-lg font-bold text-emerald-600">
                            ${(sdr.totalPayment / 1000).toFixed(0)}K
                          </p>
                          <p className="text-xs text-emerald-700">Pago total</p>
                        </div>
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

