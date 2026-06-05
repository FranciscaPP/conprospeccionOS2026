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
} from "lucide-react";
import { format } from "date-fns";
import type { Meeting } from "@/lib/types";
import {
  meetingStatusLabels,
  cpValidationLabels,
  clientValidationLabels,
  finalValidationLabels,
  commercialStatusLabels,
} from "@/lib/types";

export default function MeetingValidationPage() {
  const { meetings } = useApp();
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [companyFilter, setCompanyFilter] = useState<string>("all");

  // Filter meetings for GBS Logistics only
  const clientMeetings = useMemo(() => {
    return meetings.filter((m) => m.client === "GBS Logistics");
  }, [meetings]);

  // Calculate KPIs
  const kpis = useMemo(() => {
    const total = clientMeetings.length;
    const pendingValidation = clientMeetings.filter(
      (m) => m.clientValidation === "waiting_client_validation"
    ).length;
    const validated = clientMeetings.filter(
      (m) => m.clientValidation === "valid_client" || m.clientValidation === "not_valid_client"
    ).length;
    const inDispute = clientMeetings.filter((m) => m.finalValidation === "in_dispute").length;
    const finalValid = clientMeetings.filter((m) => m.finalValidation === "final_valid").length;
    const goal = 45;
    const progress = Math.round((finalValid / goal) * 100);

    return { total, pendingValidation, validated, inDispute, finalValid, goal, progress };
  }, [clientMeetings]);

  // Apply filters
  const filteredMeetings = useMemo(() => {
    return clientMeetings.filter((meeting) => {
      const matchesSearch =
        searchQuery === "" ||
        meeting.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
        meeting.contact.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus =
        statusFilter === "all" || meeting.finalValidation === statusFilter;

      const matchesCompany =
        companyFilter === "all" || meeting.company === companyFilter;

      return matchesSearch && matchesStatus && matchesCompany;
    });
  }, [clientMeetings, searchQuery, statusFilter, companyFilter]);

  // Get unique companies for filter
  const companies = useMemo(() => {
    return [...new Set(clientMeetings.map((m) => m.company))];
  }, [clientMeetings]);

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
            <h1 className="text-xl font-semibold text-foreground">Validación de reuniones</h1>
            <p className="text-sm text-muted-foreground">Junio 2026 · GBS Logistics · Datos demo · Prototipo funcional</p>
          </div>
          <DemoDisabledButton className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </DemoDisabledButton>
        </div>
      </header>

      <ScrollArea className="h-[calc(100vh-65px)]">
        <div className="p-6 space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <KPICard
              title="Reuniones"
              value={kpis.total}
              icon={<Calendar className="h-5 w-5" />}
            />
            <KPICard
              title="Pendientes"
              value={kpis.pendingValidation}
              icon={<Clock className="h-5 w-5" />}
              variant="warning"
            />
            <KPICard
              title="Validadas"
              value={kpis.validated}
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
              title="Válidas finales"
              value={kpis.finalValid}
              icon={<CheckCircle2 className="h-5 w-5" />}
              variant="success"
            />
            <KPICard
              title="Avance de meta"
              value={`${kpis.finalValid}/${kpis.goal}`}
              trend={`${kpis.progress}%`}
              icon={<Target className="h-5 w-5" />}
              variant="primary"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar empresa o contacto"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={(value) => value && setStatusFilter(value)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Estado: todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Estado: todos</SelectItem>
                <SelectItem value="pending">Pendiente</SelectItem>
                <SelectItem value="final_valid">Válida final</SelectItem>
                <SelectItem value="final_not_valid">No válida final</SelectItem>
                <SelectItem value="in_dispute">En disputa</SelectItem>
                <SelectItem value="rescheduled">Rescheduled</SelectItem>
              </SelectContent>
            </Select>
            <Select value={companyFilter} onValueChange={(value) => value && setCompanyFilter(value)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Empresa: todas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Empresa: todas</SelectItem>
                {companies.map((company) => (
                  <SelectItem key={company} value={company}>
                    {company}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Goal Progress Bar */}
          <div className="bg-card rounded-xl border border-border p-4">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="text-sm font-medium text-foreground">Avance de meta contractual</h3>
                <p className="text-xs text-muted-foreground">
                  Reuniones válidas finales sobre la meta del contrato
                </p>
              </div>
              <span className="text-lg font-bold text-violet-600">
                {kpis.finalValid}/{kpis.goal} · {kpis.progress}%
              </span>
            </div>
            <Progress value={kpis.progress} className="h-2" />
          </div>

          {/* Meeting Table */}
          <div className="bg-card rounded-xl border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Empresa / contacto
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Fecha y hora
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Estado reunión
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Validación CP
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Validación cliente
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Validación final
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Estado comercial
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
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
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-violet-100">
                            <span className="text-xs font-semibold text-violet-700">
                              {meeting.company.charAt(0)}
                            </span>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-foreground">{meeting.company}</p>
                            <p className="text-xs text-muted-foreground">
                              {meeting.contact} · {meeting.jobTitle}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-sm text-foreground">
                          {format(new Date(meeting.meetingDate), "MMM d, yyyy")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(meeting.meetingDate), "HH:mm")}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={meeting.meetingStatus}
                          label={meetingStatusLabels[meeting.meetingStatus]}
                          size="sm"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={meeting.cpValidation}
                          label={cpValidationLabels[meeting.cpValidation]}
                          size="sm"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={meeting.clientValidation}
                          label={clientValidationLabels[meeting.clientValidation]}
                          size="sm"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={meeting.finalValidation}
                          label={finalValidationLabels[meeting.finalValidation]}
                          size="sm"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={meeting.commercialStatus}
                          label={commercialStatusLabels[meeting.commercialStatus]}
                          size="sm"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <Button variant="ghost" size="sm" className="gap-1 text-violet-600">
                          Edit <ChevronRight className="h-4 w-4" />
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
        mode="client"
      />
    </div>
  );
}

