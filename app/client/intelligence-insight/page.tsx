"use client";

import { useState, useMemo } from "react";
import { useApp } from "@/lib/app-context";
import { KPICard } from "@/components/kpi-card";
import { DemoDisabledButton } from "@/components/demo-disabled-button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Select,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  RefreshCw,
  Download,
  Users,
  Building2,
  MessageSquare,
  ThumbsUp,
  Calendar,
  CheckCircle2,
  Target,
  Lightbulb,
  TrendingUp,
  AlertTriangle,
  Zap,
  ArrowRight,
  CircleDot,
} from "lucide-react";
import { intelligenceData } from "@/lib/mock-data";

export default function IntelligenceInsightPage() {
  const { meetings } = useApp();
  const [activeTab, setActiveTab] = useState("summary");

  // Calculate real KPIs from meetings
  const kpis = useMemo(() => {
    const clientMeetings = meetings.filter((m) => m.client === "GBS Logistics");
    const finalValid = clientMeetings.filter((m) => m.finalValidation === "final_valid").length;
    
    return {
      ...intelligenceData.kpis,
      finalValidMeetings: finalValid,
      goalProgress: Math.round((finalValid / 45) * 100),
    };
  }, [meetings]);

  const funnel = intelligenceData.funnel;

  return (
    <div className="flex-1 overflow-hidden">
      {/* Header */}
      <header className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Revenue Intelligence</h1>
            <p className="text-sm text-muted-foreground">
              GBS Logistics · Junio 2026
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
          {/* Executive Insight Card */}
          <div className="bg-violet-50 border border-violet-200 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100">
                <Lightbulb className="h-5 w-5 text-violet-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-violet-900">Insight ejecutivo</h3>
                <p className="text-sm text-violet-700 mt-1">
                  {intelligenceData.executiveInsight}
                </p>
              </div>
            </div>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
            <KPICard
              title="Contactos"
              value={kpis.contactsReached}
              icon={<Users className="h-5 w-5" />}
            />
            <KPICard
              title="Empresas"
              value={kpis.companiesImpacted}
              icon={<Building2 className="h-5 w-5" />}
            />
            <KPICard
              title="Respuestas"
              value={kpis.replies}
              icon={<MessageSquare className="h-5 w-5" />}
            />
            <KPICard
              title="Resp. positivas"
              value={kpis.positiveReplies}
              icon={<ThumbsUp className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Reuniones"
              value={kpis.meetingsGenerated}
              icon={<Calendar className="h-5 w-5" />}
              variant="warning"
            />
            <KPICard
              title="Válidas finales"
              value={kpis.finalValidMeetings}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <div className="col-span-2 bg-card border border-border rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Meta contractual
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <div className="relative w-12 h-12">
                    <svg className="w-12 h-12 -rotate-90">
                      <circle
                        cx="24"
                        cy="24"
                        r="20"
                        strokeWidth="4"
                        stroke="currentColor"
                        fill="none"
                        className="text-muted"
                      />
                      <circle
                        cx="24"
                        cy="24"
                        r="20"
                        strokeWidth="4"
                        stroke="currentColor"
                        fill="none"
                        strokeDasharray={`${kpis.goalProgress * 1.25} 125`}
                        className="text-violet-600"
                      />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-foreground">
                      {kpis.goalProgress}%
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-foreground">
                      {kpis.finalValidMeetings}/45 válidas
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {45 - kpis.finalValidMeetings} restantes
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Filters */}
          <TooltipProvider>
            <div className="flex flex-wrap gap-3 items-center">
              {["Periodo", "País", "Industria", "Cargo", "Canal"].map((label) => (
                <Tooltip key={label}>
                  <TooltipTrigger render={<span className="inline-flex" />}>
                    <Select defaultValue="all">
                      <SelectTrigger className={label === "Periodo" ? "w-[180px]" : "w-[140px]"} disabled>
                        <SelectValue placeholder={`${label}: próximamente`} />
                      </SelectTrigger>
                    </Select>
                  </TooltipTrigger>
                  <TooltipContent>Próximamente</TooltipContent>
                </Tooltip>
              ))}
            </div>
          </TooltipProvider>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-muted/50">
              <TabsTrigger value="summary">Resumen</TabsTrigger>
              <TabsTrigger value="funnel">Funnel</TabsTrigger>
              <TabsTrigger value="segments">Segmentos</TabsTrigger>
              <TabsTrigger value="findings">Hallazgos</TabsTrigger>
              <TabsTrigger value="recommendations">Recomendaciones</TabsTrigger>
              <TabsTrigger value="campaigns">Campañas</TabsTrigger>
            </TabsList>

            <TabsContent value="summary" className="mt-6 space-y-6">
              {/* Summary Content */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Commercial Funnel */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Funnel comercial</h3>
                  <div className="space-y-3">
                    {[
                      { label: "Contactos", value: funnel.contacts.value, percentage: funnel.contacts.percentage, color: "bg-violet-500" },
                      { label: "Respuestas", value: funnel.replies.value, percentage: funnel.replies.percentage, color: "bg-blue-500" },
                      { label: "Positivas", value: funnel.positive.value, percentage: funnel.positive.percentage, color: "bg-emerald-500" },
                      { label: "Reuniones", value: funnel.meetings.value, percentage: funnel.meetings.percentage, color: "bg-amber-500" },
                      { label: "Válidas", value: funnel.valid.value, percentage: funnel.valid.percentage, color: "bg-rose-500" },
                    ].map((item) => (
                      <div key={item.label} className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${item.color}`} />
                        <span className="text-sm text-muted-foreground w-16">{item.label}</span>
                        <span className="text-sm font-semibold text-foreground w-12">{item.value}</span>
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.color}`}
                            style={{ width: `${Math.min(item.percentage, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground w-10 text-right">
                          {item.percentage}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top Segments */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Segmentos con mayor señal</h3>
                  <p className="text-xs text-muted-foreground mb-3">Conversión a reuniones</p>
                  <div className="space-y-3">
                    {intelligenceData.topSegments.map((segment, index) => (
                      <div key={segment.name} className="flex items-center gap-3">
                        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                          index === 0 ? "bg-amber-100" : index === 1 ? "bg-violet-100" : "bg-emerald-100"
                        }`}>
                          <TrendingUp className={`h-4 w-4 ${
                            index === 0 ? "text-amber-600" : index === 1 ? "text-violet-600" : "text-emerald-600"
                          }`} />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">{segment.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {segment.positiveReplies} positivas · {segment.meetings} reuniones
                          </p>
                        </div>
                        <span className="text-sm font-bold text-emerald-600">{segment.conversionRate}%</span>
                      </div>
                    ))}
                  </div>
                  <DemoDisabledButton variant="link" className="mt-3 p-0 text-violet-600 text-sm">
                    Ver segmentos <ArrowRight className="h-4 w-4 ml-1" />
                  </DemoDisabledButton>
                </div>

                {/* What to Watch Now */}
                <div className="bg-card border border-border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Qué mirar ahora</h3>
                  <div className="space-y-3">
                    {intelligenceData.watchNow.map((item) => (
                      <div
                        key={item.title}
                        className={`p-3 rounded-lg border ${
                          item.type === "priority"
                            ? "bg-violet-50 border-violet-200"
                            : item.type === "risk"
                            ? "bg-amber-50 border-amber-200"
                            : "bg-emerald-50 border-emerald-200"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          {item.type === "priority" ? (
                            <Zap className="h-4 w-4 text-violet-600 mt-0.5" />
                          ) : item.type === "risk" ? (
                            <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5" />
                          ) : (
                            <CheckCircle2 className="h-4 w-4 text-emerald-600 mt-0.5" />
                          )}
                          <div>
                            <p className={`text-xs font-semibold uppercase tracking-wide ${
                              item.type === "priority"
                                ? "text-violet-700"
                                : item.type === "risk"
                                ? "text-amber-700"
                                : "text-emerald-700"
                            }`}>
                              {item.type === "priority" ? "Prioridad" : item.type === "risk" ? "Riesgo" : "Acción sugerida"}
                            </p>
                            <p className={`text-sm mt-0.5 ${
                              item.type === "priority"
                                ? "text-violet-900"
                                : item.type === "risk"
                                ? "text-amber-900"
                                : "text-emerald-900"
                            }`}>
                              {item.description}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Next Decisions */}
              <div className="bg-card border border-border rounded-xl p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">Próximas decisiones</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {intelligenceData.decisions.map((decision, index) => (
                    <div
                      key={decision.title}
                      className="flex items-start gap-3 p-4 bg-muted/30 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-100">
                        {index === 0 ? (
                          <TrendingUp className="h-4 w-4 text-violet-600" />
                        ) : index === 1 ? (
                          <MessageSquare className="h-4 w-4 text-violet-600" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4 text-violet-600" />
                        )}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">{decision.title}</p>
                        <p className="text-xs text-muted-foreground mt-1">{decision.description}</p>
                      </div>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="funnel" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-foreground mb-6">Análisis detallado del funnel</h3>
                <div className="flex items-end gap-4 h-64">
                  {[
                    { label: "Contactos", value: 784, color: "bg-violet-500" },
                    { label: "Respuestas", value: 21, color: "bg-blue-500" },
                    { label: "Positivas", value: 8, color: "bg-emerald-500" },
                    { label: "Reuniones", value: 2, color: "bg-amber-500" },
                    { label: "Válidas", value: 0, color: "bg-rose-500" },
                  ].map((item, index) => {
                    const maxValue = 784;
                    const height = (item.value / maxValue) * 200;
                    return (
                      <div key={item.label} className="flex-1 flex flex-col items-center gap-2">
                        <span className="text-sm font-bold text-foreground">{item.value}</span>
                        <div
                          className={`w-full ${item.color} rounded-t-lg transition-all`}
                          style={{ height: `${Math.max(height, 4)}px` }}
                        />
                        <span className="text-xs text-muted-foreground">{item.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="segments" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Segmento
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Contactos
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Respuestas
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Reuniones
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {intelligenceData.performanceBySegment.map((segment) => (
                      <tr key={segment.segment} className="hover:bg-muted/30">
                        <td className="px-4 py-3 text-sm font-medium text-foreground">{segment.segment}</td>
                        <td className="px-4 py-3 text-sm text-foreground">{segment.contacts}</td>
                        <td className="px-4 py-3 text-sm text-foreground">{segment.replies}</td>
                        <td className="px-4 py-3 text-sm text-foreground">{segment.meetings}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </TabsContent>

            <TabsContent value="findings" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4">Hallazgos clave</h3>
                <div className="space-y-3">
                  {intelligenceData.findings.map((finding, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-muted/30 rounded-lg">
                      <CircleDot className="h-5 w-5 text-violet-600 mt-0.5" />
                      <p className="text-sm text-foreground">{finding}</p>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="recommendations" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4">Recomendaciones estratégicas</h3>
                <div className="space-y-3">
                  {intelligenceData.recommendations.map((rec, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                      <CheckCircle2 className="h-5 w-5 text-emerald-600 mt-0.5" />
                      <p className="text-sm text-emerald-900">{rec}</p>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="campaigns" className="mt-6 space-y-6">
              <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4">Performance por campaña</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {intelligenceData.performanceByChannel.map((channel) => (
                    <div key={channel.channel} className="p-4 bg-muted/30 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-foreground">{channel.channel}</span>
                        <span className="text-xs text-muted-foreground">{channel.percentage}% respuesta</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <div>
                          <p className="text-2xl font-bold text-foreground">{channel.contacts}</p>
                          <p className="text-xs text-muted-foreground">Contactos</p>
                        </div>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-2xl font-bold text-foreground">{channel.replies}</p>
                          <p className="text-xs text-muted-foreground">Respuestas</p>
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

