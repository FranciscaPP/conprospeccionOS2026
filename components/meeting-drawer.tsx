"use client";

import { useApp } from "@/lib/app-context";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusBadge } from "@/components/status-badge";
import {
  Building2,
  User,
  Briefcase,
  Calendar,
  MessageSquare,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";
import { format } from "date-fns";
import { useState, useEffect } from "react";
import type { Meeting, BANTCriteria, ClientValidation, CommercialStatus, FinalValidation, CPValidation } from "@/lib/types";
import {
  cpValidationLabels,
  clientValidationLabels,
  finalValidationLabels,
  commercialStatusLabels,
  meetingStatusLabels,
  bantLabels,
} from "@/lib/types";

interface MeetingDrawerProps {
  meeting: Meeting | null;
  open: boolean;
  onClose: () => void;
  mode: "client" | "internal";
}

export function MeetingDrawer({ meeting, open, onClose, mode }: MeetingDrawerProps) {
  const { updateMeeting } = useApp();
  const [formData, setFormData] = useState<Partial<Meeting>>({});

  useEffect(() => {
    if (meeting) {
      setFormData(meeting);
    }
  }, [meeting]);

  if (!meeting) return null;

  const handleSave = () => {
    if (meeting) {
      // Reglas mínimas para mantener la demo coherente al guardar.
      let finalValidation = formData.finalValidation || meeting.finalValidation;
      
      if (formData.cpValidation === "valid_cp" && formData.clientValidation === "not_valid_client") {
        finalValidation = "in_dispute";
      }
      else if (formData.clientValidation === "waiting_client_validation") {
        finalValidation = "pending";
      }
      else if (formData.cpValidation === "valid_cp" && formData.clientValidation === "valid_client") {
        finalValidation = "final_valid";
      }
      
      updateMeeting(meeting.id, {
        ...formData,
        finalValidation,
        disputeFlag: finalValidation === "in_dispute",
        pendingClientFlag: formData.clientValidation === "waiting_client_validation",
      });
      onClose();
    }
  };

  const bantOptions: BANTCriteria[] = ["budget", "authority", "need", "timeline"];

  const toggleBANT = (criteria: BANTCriteria, field: "cpBANT" | "clientBANT") => {
    const currentBANT = (formData[field] as BANTCriteria[]) || [];
    const newBANT = currentBANT.includes(criteria)
      ? currentBANT.filter((c) => c !== criteria)
      : [...currentBANT, criteria];
    setFormData({ ...formData, [field]: newBANT });
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[480px] sm:max-w-[480px] p-0">
        <SheetHeader className="p-6 pb-4 border-b border-border">
          <div className="flex items-start justify-between">
            <div>
              <SheetTitle className="text-lg font-semibold">{meeting.company}</SheetTitle>
              <p className="text-sm text-muted-foreground mt-1">
                {format(new Date(meeting.meetingDate), "EEEE, MMMM d, yyyy · HH:mm")}
              </p>
            </div>
            <StatusBadge
              status={meeting.finalValidation}
              label={finalValidationLabels[meeting.finalValidation]}
            />
          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-180px)]">
          <div className="p-6 space-y-6">
            {/* Meeting Info */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Información de la reunión
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Contacto</Label>
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">{meeting.contact}</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Fecha y hora</Label>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">
                      {format(new Date(meeting.meetingDate), "MMM d, yyyy · HH:mm")}
                    </span>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Cargo</Label>
                  <div className="flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">{meeting.jobTitle}</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Estado reunión</Label>
                  <StatusBadge
                    status={meeting.meetingStatus}
                    label={meetingStatusLabels[meeting.meetingStatus]}
                    size="sm"
                  />
                </div>
              </div>
              
              {mode === "internal" && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">SDR asignado</Label>
                  <p className="text-sm font-medium">{meeting.sdrAssigned}</p>
                </div>
              )}

              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Resumen de reunión</Label>
                <p className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
                  {meeting.meetingSummary}
                </p>
              </div>
            </div>

            <Separator />

            {/* Conprospección Validation */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-violet-600" />
                Evaluación Conprospección
              </h3>
              
              {mode === "internal" ? (
                <>
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Validación CP</Label>
                    <Select
                      value={formData.cpValidation}
                      onValueChange={(value) =>
                        value && setFormData({ ...formData, cpValidation: value as CPValidation })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(cpValidationLabels).map(([value, label]) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">BANT CP</Label>
                    <div className="flex flex-wrap gap-2">
                      {bantOptions.map((criteria) => (
                        <button
                          key={criteria}
                          onClick={() => toggleBANT(criteria, "cpBANT")}
                          className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-colors ${
                            (formData.cpBANT as BANTCriteria[] || []).includes(criteria)
                              ? "bg-violet-100 text-violet-700 border-violet-300"
                              : "bg-muted text-muted-foreground border-border hover:bg-muted/80"
                          }`}
                        >
                          {bantLabels[criteria].charAt(0)} - {bantLabels[criteria]}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Validación CP</Label>
                    <StatusBadge
                      status={meeting.cpValidation}
                      label={cpValidationLabels[meeting.cpValidation]}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">BANT CP</Label>
                    <div className="flex flex-wrap gap-2">
                      {meeting.cpBANT.map((criteria) => (
                        <span
                          key={criteria}
                          className="px-3 py-1.5 text-xs font-medium rounded-full bg-violet-100 text-violet-700 border border-violet-300"
                        >
                          {bantLabels[criteria].charAt(0)} - {bantLabels[criteria]}
                        </span>
                      ))}
                      {meeting.cpBANT.length === 0 && (
                        <span className="text-sm text-muted-foreground">Sin datos</span>
                      )}
                    </div>
                  </div>
                </>
              )}

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Comentario CP</Label>
                <p className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
                  {meeting.cpComment || "Sin comentario"}
                </p>
              </div>
            </div>

            <Separator />

            {/* Client Validation */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-amber-600" />
                Validación del cliente
              </h3>

              {mode === "client" ? (
                <>
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Tu validación</Label>
                    <Select
                      value={formData.clientValidation}
                      onValueChange={(value) =>
                        value && setFormData({ ...formData, clientValidation: value as ClientValidation })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(clientValidationLabels).map(([value, label]) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Tu evaluación BANT</Label>
                    <div className="flex flex-wrap gap-2">
                      {bantOptions.map((criteria) => (
                        <button
                          key={criteria}
                          onClick={() => toggleBANT(criteria, "clientBANT")}
                          className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-colors ${
                            (formData.clientBANT as BANTCriteria[] || []).includes(criteria)
                              ? "bg-amber-100 text-amber-700 border-amber-300"
                              : "bg-muted text-muted-foreground border-border hover:bg-muted/80"
                          }`}
                        >
                          {bantLabels[criteria].charAt(0)} - {bantLabels[criteria]}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Tu comentario</Label>
                    <Textarea
                      value={formData.clientComment || ""}
                      onChange={(e) =>
                        setFormData({ ...formData, clientComment: e.target.value })
                      }
                      placeholder="Agrega tus comentarios sobre esta reunión..."
                      rows={3}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Validación cliente</Label>
                    <StatusBadge
                      status={meeting.clientValidation}
                      label={clientValidationLabels[meeting.clientValidation]}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">BANT cliente</Label>
                    <div className="flex flex-wrap gap-2">
                      {meeting.clientBANT.map((criteria) => (
                        <span
                          key={criteria}
                          className="px-3 py-1.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700 border border-amber-300"
                        >
                          {bantLabels[criteria].charAt(0)} - {bantLabels[criteria]}
                        </span>
                      ))}
                      {meeting.clientBANT.length === 0 && (
                        <span className="text-sm text-muted-foreground">Sin datos</span>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Comentario cliente</Label>
                    <p className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
                      {meeting.clientComment || "Sin comentario"}
                    </p>
                  </div>
                </>
              )}
            </div>

            <Separator />

            {/* Final Validation */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground">Validación final</h3>
              
              {mode === "internal" ? (
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Estado de validación final</Label>
                  <Select
                    value={formData.finalValidation}
                    onValueChange={(value) =>
                      value && setFormData({ ...formData, finalValidation: value as FinalValidation })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(finalValidationLabels).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    La validación final se calcula según la validación CP y del cliente.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Estado actual</Label>
                  <StatusBadge
                    status={meeting.finalValidation}
                    label={finalValidationLabels[meeting.finalValidation]}
                  />
                  <p className="text-xs text-muted-foreground">
                    La validación final se determina con ambas validaciones.
                  </p>
                </div>
              )}
            </div>

            <Separator />

            {/* Commercial Status */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground">Estado comercial</h3>
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Estado</Label>
                <Select
                  value={formData.commercialStatus}
                  onValueChange={(value) =>
                    value && setFormData({ ...formData, commercialStatus: value as CommercialStatus })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(commercialStatusLabels).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Próximo paso</Label>
                <Input
                  value={formData.nextStep || ""}
                  onChange={(e) => setFormData({ ...formData, nextStep: e.target.value })}
                  placeholder="Define la siguiente acción..."
                />
              </div>
            </div>

            {mode === "internal" && (
              <>
                <Separator />
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground">Notas internas</h3>
                  <Textarea
                    value={formData.internalNotes || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, internalNotes: e.target.value })
                    }
                    placeholder="Agrega notas internas..."
                    rows={3}
                  />
                </div>
              </>
            )}
          </div>
        </ScrollArea>

        <div className="border-t border-border p-4 flex gap-3">
          <Button variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button onClick={handleSave} className="flex-1 bg-violet-600 hover:bg-violet-700 text-white">
            Guardar cambios
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

