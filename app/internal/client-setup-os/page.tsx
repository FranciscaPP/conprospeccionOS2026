"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  Database,
  Globe,
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
  Target,
  UserCheck,
  Users,
  Zap,
} from "lucide-react";
import { useApp } from "@/lib/app-context";
import { KPICard } from "@/components/kpi-card";
import { DemoDisabledButton } from "@/components/demo-disabled-button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const setupSteps = [
  { label: "Onboarding recibido", status: "Listo", owner: "Ops", date: "02 Jun" },
  { label: "ICP revisado", status: "En revisión", owner: "Estrategia", date: "04 Jun" },
  { label: "Dominios listos", status: "Pendiente", owner: "Infra", date: "Por definir" },
  { label: "Correos listos", status: "Pendiente", owner: "Infra", date: "Por definir" },
  { label: "Warmup listo", status: "Pendiente", owner: "Growth Ops", date: "Por definir" },
  { label: "BBDD cargada", status: "En revisión", owner: "Research", date: "06 Jun" },
  { label: "Campañas listas", status: "Riesgo", owner: "Outbound", date: "08 Jun" },
  { label: "SDR asignado", status: "Listo", owner: "Sales Ops", date: "05 Jun" },
  { label: "GHL listo", status: "Riesgo", owner: "CRM Ops", date: "Por definir" },
  { label: "Lanzamiento", status: "Pendiente", owner: "Ops Lead", date: "Por definir" },
];

const segments = [
  { name: "Chile / Minería / Comercio Exterior", status: "Prioritario", country: "Chile", industry: "Minería", roles: "Jefe COMEX, Supply Chain", size: "50-500", db: "GBS Chile minería v1", campaign: "GBS Mining Door to Door", sdr: "Camila Rojas", learning: "Mejor señal inicial; dolor claro en repuestos críticos." },
  { name: "Chile / Tecnología / Supply Chain", status: "Exploración", country: "Chile", industry: "Tecnología", roles: "Operaciones, Supply Chain", size: "20-200", db: "Pendiente enriquecer", campaign: "Pendiente", sdr: "Nicolás Vera", learning: "Validar si importan hardware o solo servicios." },
  { name: "Perú / Retail / Operaciones", status: "Pausado", country: "Perú", industry: "Retail", roles: "Operaciones, Compras", size: "100-1000", db: "Retail PE legacy", campaign: "GBS Retail Peru", sdr: "Sin asignar", learning: "Baja respuesta; revisar nomenclatura y volumen real." },
  { name: "México / Manufactura / Compras", status: "Pendiente BBDD", country: "México", industry: "Manufactura", roles: "Compras, Abastecimiento", size: "100-500", db: "No creada", campaign: "No creada", sdr: "Sin asignar", learning: "Potencial para fase 2 si GBS confirma cobertura." },
];

const targetAccounts = [
  ["Andina Metals", "andinametals.cl", "Onboarding", "Validada"],
  ["Kaufmann", "kaufmann.cl", "Histórico", "En revisión"],
  ["TecnoParts", "tecnoparts.cl", "Apollo mock", "Validada"],
  ["Pacific Foods", "pacificfoods.cl", "CSV legacy", "Pendiente segmento"],
];

const excludedAccounts = [
  ["Cliente actual A", "Cliente actual", "Bloqueada"],
  ["Forwarder Competidor", "Competidor", "Bloqueada"],
  ["Cuenta histórica B", "Cliente histórico", "Revisar"],
];

const infra = [
  ["Dominio", "gbs-logistics.pro", "Hostinger", "General", "Pendiente compra"],
  ["Correo", "contacto@gbs-logistics.pro", "Zapmail", "General", "Pendiente crear"],
  ["Correo", "camila@gbs-logistics.pro", "Zapmail", "Minería Chile", "Pendiente crear"],
  ["Firma", "GBS Door to Door", "Plantilla interna", "Todos", "En revisión"],
  ["Warmup", "camila@gbs-logistics.pro", "Snov.io", "Minería Chile", "No iniciado"],
];

const databases = [
  ["GBS Chile minería v1", "CSV histórico", "Chile / Minería", "482", "En revisión", "Media", "Normalizar cargos y dominios duplicados."],
  ["Retail PE legacy", "Snov", "Perú / Retail", "318", "Mala calidad", "Baja", "Antigua, sin país consistente."],
  ["GBS target accounts", "Onboarding", "General", "42", "Reutilizable", "Alta", "Empresas indicadas por cliente."],
  ["Apollo import 2026-06", "Apollo mock", "Pendiente segmentar", "210", "Pendiente segmentar", "Media", "No cargar a Snov hasta separar ICP."],
];

const campaigns = [
  ["GBS Mining Door to Door", "Snov", "Chile / Minería", "210", "Reutilizable", "Media", "Ajustar asunto y CTA."],
  ["GBS Retail Peru", "Snov", "Perú / Retail", "180", "En revisión", "Baja", "Mala nomenclatura y fit débil."],
  ["Campana GBS 1", "Histórico", "Sin segmento", "96", "Pendiente segmentar", "Indefinida", "Alerta: campaña sin segmento."],
  ["GHL follow-up imports", "GHL", "General", "74", "Pendiente cargar GHL", "Media", "Verificar riesgo de configuración mezclada."],
];

const sdrs = [
  ["Camila Rojas", "SDR", "GBS Logistics", "Chile / Minería", "Asignada"],
  ["Nicolás Vera", "SDR", "GBS Logistics", "Chile / Tecnología", "Asignada"],
  ["Sin asignar", "SDR", "GBS Logistics", "Perú / Retail", "Pendiente"],
];

function statusClass(status: string) {
  const value = status.toLowerCase();
  if (value.includes("listo") || value.includes("validada") || value.includes("asignada") || value.includes("reutilizable")) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (value.includes("riesgo") || value.includes("mala") || value.includes("bloqueada")) return "bg-rose-100 text-rose-700 border-rose-200";
  if (value.includes("revisión") || value.includes("revisar")) return "bg-orange-100 text-orange-700 border-orange-200";
  if (value.includes("pendiente")) return "bg-amber-100 text-amber-700 border-amber-200";
  if (value.includes("pausado") || value.includes("exploración") || value.includes("prioritario")) return "bg-violet-100 text-violet-700 border-violet-200";
  return "bg-muted text-muted-foreground border-border";
}

function StatusPill({ children }: { children: string }) {
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${statusClass(children)}`}>{children}</span>;
}

function DataTable({ columns, rows }: { columns: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-sm">
        <thead>
          <tr className="border-b">
            {columns.map((column) => <th key={column} className="px-3 pb-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{column}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row[0]}-${index}`} className="border-b last:border-0">
              {row.map((cell, cellIndex) => (
                <td key={`${cell}-${cellIndex}`} className="px-3 py-3 align-top text-foreground">
                  {cellIndex >= row.length - 3 && (cell.includes("Pendiente") || cell.includes("Listo") || cell.includes("Validada") || cell.includes("Riesgo") || cell.includes("Reutilizable") || cell.includes("Mala") || cell.includes("Bloqueada") || cell.includes("Asignada") || cell.includes("revisión")) ? <StatusPill>{cell}</StatusPill> : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SegmentCard({ segment }: { segment: typeof segments[number] }) {
  return (
    <Card>
      <CardHeader className="border-b">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{segment.name}</CardTitle>
            <CardDescription>{segment.country} · {segment.industry} · {segment.size}</CardDescription>
          </div>
          <StatusPill>{segment.status}</StatusPill>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <Info label="Cargos" value={segment.roles} />
        <Info label="BBDD" value={segment.db} />
        <Info label="Campaña" value={segment.campaign} />
        <Info label="SDR" value={segment.sdr} />
        <div className="md:col-span-2 rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
          <span className="font-semibold text-foreground">Aprendizaje: </span>{segment.learning}
        </div>
      </CardContent>
    </Card>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}

export default function ClientSetupOSPage() {
  const { setRole } = useApp();
  const [query, setQuery] = useState("");
  const ready = setupSteps.filter((step) => step.status === "Listo").length;
  const risks = setupSteps.filter((step) => step.status === "Riesgo").length;
  const filteredCampaigns = useMemo(() => {
    return campaigns.filter((row) => row.join(" ").toLowerCase().includes(query.toLowerCase()));
  }, [query]);

  useEffect(() => {
    setRole("internal");
  }, [setRole]);

  return (
    <div className="flex-1 overflow-hidden">
      <header className="border-b border-border bg-card px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <Badge variant="secondary" className="border-violet-200 bg-violet-50 text-violet-700">Operaciones internas</Badge>
              <Badge variant="outline">GBS piloto</Badge>
            </div>
            <h1 className="text-xl font-semibold text-foreground">Client Setup OS</h1>
            <p className="text-sm text-muted-foreground">
              GBS Logistics · MVP visual · datos mock · sin APIs ni datos productivos
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
            <DemoDisabledButton className="gap-2 text-xs sm:text-sm"><RefreshCw className="h-4 w-4" />Actualizar</DemoDisabledButton>
            <DemoDisabledButton className="gap-2 bg-primary text-xs text-primary-foreground hover:bg-primary/90 sm:text-sm"><CheckCircle2 className="h-4 w-4" />Marcar revisión</DemoDisabledButton>
          </div>
        </div>
      </header>

      <ScrollArea className="h-[calc(100vh-121px)] md:h-[calc(100vh-65px)]">
        <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
          <div className="grid grid-cols-1 gap-3 min-[430px]:grid-cols-2 lg:grid-cols-6">
            <KPICard title="Checklist listo" value={`${ready}/10`} icon={<ClipboardCheck className="h-5 w-5" />} variant="primary" />
            <KPICard title="Segmentos ICP" value={segments.length} icon={<Target className="h-5 w-5" />} variant="success" />
            <KPICard title="Empresas objetivo" value={targetAccounts.length} icon={<Building2 className="h-5 w-5" />} />
            <KPICard title="BBDD auditadas" value={databases.length} icon={<Database className="h-5 w-5" />} />
            <KPICard title="Campañas" value={campaigns.length} icon={<BarChart3 className="h-5 w-5" />} variant="warning" />
            <KPICard title="Riesgos setup" value={risks} icon={<AlertTriangle className="h-5 w-5" />} variant="danger" />
          </div>

          <Card>
            <CardContent className="flex flex-col gap-3 py-4 lg:flex-row lg:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar campaña, segmento o estado" className="pl-9" />
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="gap-1"><Globe className="h-3 w-3" />Cliente: GBS Logistics</Badge>
                <Badge variant="outline" className="gap-1"><ShieldCheck className="h-3 w-3" />Estado: Todos</Badge>
                <Badge variant="outline" className="gap-1"><UserCheck className="h-3 w-3" />Responsable: Ops</Badge>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="resumen" className="space-y-4">
            <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <TabsList className="inline-flex h-auto min-w-max justify-start">
              <TabsTrigger value="resumen">Resumen</TabsTrigger>
              <TabsTrigger value="icp">ICP</TabsTrigger>
              <TabsTrigger value="empresas">Empresas</TabsTrigger>
              <TabsTrigger value="infra">Infraestructura</TabsTrigger>
              <TabsTrigger value="bbdd">BBDD</TabsTrigger>
              <TabsTrigger value="campanas">Campañas</TabsTrigger>
              <TabsTrigger value="sdr">SDR</TabsTrigger>
              <TabsTrigger value="historial">Historial</TabsTrigger>
            </TabsList>
            </div>

            <TabsContent value="resumen" className="space-y-4">
              <div className="grid gap-4 xl:grid-cols-[1.35fr_.65fr]">
                <Card>
                  <CardHeader>
                    <CardTitle>Checklist de lanzamiento</CardTitle>
                    <CardDescription>Estado operativo completo para GBS Logistics</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-3 md:grid-cols-2">
                    {setupSteps.map((step) => (
                      <div key={step.label} className="rounded-lg border bg-muted/30 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm font-semibold text-foreground">{step.label}</p>
                          <StatusPill>{step.status}</StatusPill>
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">{step.owner} · {step.date}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Riesgos detectados</CardTitle>
                    <CardDescription>Clasificación previa a conectar APIs</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {[
                      ["Campañas legacy sin segmentar", "Hay campañas históricas que deben clasificarse antes de reutilizarse."],
                      ["GHL pendiente", "La asignación de usuarios y pipelines queda simulada hasta fase de integración."],
                      ["ICP iterativo", "Cada subsegmento tiene BBDD, campaña, SDR, estado y aprendizaje propio."],
                    ].map(([title, text]) => (
                      <div key={title} className="rounded-lg border bg-muted/30 p-3">
                        <p className="text-sm font-semibold text-foreground">{title}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{text}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="icp" className="grid gap-4 xl:grid-cols-2">
              {segments.map((segment) => <SegmentCard key={segment.name} segment={segment} />)}
            </TabsContent>

            <TabsContent value="empresas" className="grid gap-4 xl:grid-cols-2">
              <Card><CardHeader><CardTitle>Empresas objetivo</CardTitle></CardHeader><CardContent><DataTable columns={["Empresa", "Dominio", "Fuente", "Estado"]} rows={targetAccounts} /></CardContent></Card>
              <Card><CardHeader><CardTitle>Empresas excluidas</CardTitle></CardHeader><CardContent><DataTable columns={["Empresa", "Motivo", "Estado"]} rows={excludedAccounts} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="infra">
              <Card><CardHeader><CardTitle>Dominios, correos, firmas y warmup</CardTitle><CardDescription>Preparado para Hostinger, Zapmail y Snov en fase 2</CardDescription></CardHeader><CardContent><DataTable columns={["Tipo", "Nombre", "Proveedor", "Segmento", "Estado"]} rows={infra} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="bbdd">
              <Card><CardHeader><CardTitle>Bases de datos existentes</CardTitle><CardDescription>Auditoría visual de fuentes y calidad</CardDescription></CardHeader><CardContent><DataTable columns={["Nombre", "Fuente", "Segmento", "Prospectos", "Estado", "Calidad", "Observaciones"]} rows={databases} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="campanas">
              <Card><CardHeader><CardTitle>Campañas y BBDD existentes</CardTitle><CardDescription>{filteredCampaigns.length} visibles según búsqueda</CardDescription></CardHeader><CardContent><DataTable columns={["Nombre", "Fuente", "Segmento", "Prospectos", "Estado", "Calidad", "Observaciones"]} rows={filteredCampaigns} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="sdr">
              <Card><CardHeader><CardTitle>Usuarios SDR y asignación cliente</CardTitle><CardDescription>GBS Logistics · mock operativo</CardDescription></CardHeader><CardContent><DataTable columns={["Usuario", "Rol", "Cliente", "Segmento", "Estado"]} rows={sdrs} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="historial">
              <Card>
                <CardHeader><CardTitle>Historial de setup</CardTitle><CardDescription>Estados y observaciones del piloto</CardDescription></CardHeader>
                <CardContent className="space-y-3">
                  {[
                    "Onboarding GBS recibido desde portal cliente",
                    "Se normaliza slug operativo gbs_logistics",
                    "Se detectan campañas legacy para auditar",
                    "Pendiente compra de dominios y creación de correos",
                  ].map((event, index) => (
                    <div key={event} className="rounded-lg border bg-muted/30 p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-primary">0{index + 2} Jun</p>
                      <p className="mt-1 text-sm font-semibold text-foreground">{event}</p>
                      <p className="text-xs text-muted-foreground">Usuario: Operaciones · Observación de piloto visual</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </ScrollArea>
    </div>
  );
}
