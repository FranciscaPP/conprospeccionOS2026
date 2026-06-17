import { NextResponse } from "next/server";
import {
  buildSupabaseMeetingSelect,
  type ClientRow,
  mapSupabaseRowsToMeetings,
  MEETINGS_START_DATE,
  type SdrRow,
  type SupabaseMeetingRow,
} from "@/lib/supabase-meetings";

export const dynamic = "force-dynamic";

function getSupabaseConfig() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key =
    process.env.SUPABASE_SECRET_KEY ||
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    process.env.SUPABASE_SERVICE_KEY ||
    process.env.SUPABASE_KEY;

  if (!url || !key) {
    throw new Error("Faltan SUPABASE_URL y SUPABASE_SECRET_KEY/SUPABASE_SERVICE_ROLE_KEY en el entorno.");
  }

  return {
    restUrl: `${url.replace(/\/$/, "").replace(/\/rest\/v1$/, "")}/rest/v1`,
    key,
  };
}

async function supabaseGet<T>(
  table: string,
  params: Record<string, string>,
  config: { restUrl: string; key: string }
): Promise<T[]> {
  const search = new URLSearchParams(params);
  const response = await fetch(`${config.restUrl}/${table}?${search.toString()}`, {
    headers: {
      apikey: config.key,
      Authorization: `Bearer ${config.key}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Supabase ${table} ${response.status}: ${body.slice(0, 300)}`);
  }

  return response.json() as Promise<T[]>;
}

async function patchSupabaseRows(
  params: Record<string, string>,
  payload: Record<string, unknown>,
  config: { restUrl: string; key: string }
) {
  const search = new URLSearchParams(params);
  const response = await fetch(`${config.restUrl}/reuniones?${search.toString()}`, {
    method: "PATCH",
    headers: {
      apikey: config.key,
      Authorization: `Bearer ${config.key}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const responseBody = await response.text();
    throw new Error(`Supabase reuniones ${response.status}: ${responseBody.slice(0, 300)}`);
  }

  return response.json() as Promise<SupabaseMeetingRow[]>;
}

export async function GET() {
  try {
    const config = getSupabaseConfig();
    const today = new Date();
    const endOfCurrentMonth = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() + 1, 0, 23, 59, 59));
    const endDate = endOfCurrentMonth.toISOString();

    const [rows, clients, sdrs] = await Promise.all([
      supabaseGet<SupabaseMeetingRow>(
        "reuniones",
        {
          select: buildSupabaseMeetingSelect(),
          fecha_reunion: `gte.${MEETINGS_START_DATE}`,
          and: `(fecha_reunion.lte.${endDate})`,
          order: "fecha_reunion.asc,hora_reunion.asc",
          limit: "5000",
        },
        config
      ),
      supabaseGet<ClientRow>(
        "clientes",
        {
          select: "slug,nombre,pais_prospeccion",
          limit: "500",
        },
        config
      ),
      supabaseGet<SdrRow>(
        "sdrs",
        {
          select: "slug,nombre",
          limit: "500",
        },
        config
      ),
    ]);

    return NextResponse.json(mapSupabaseRowsToMeetings(rows, clients, sdrs));
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Error desconocido cargando reuniones reales.",
        meetings: [],
      },
      { status: 500 }
    );
  }
}

function validationPatch(finalValidation: string | undefined) {
  if (finalValidation === "final_valid") {
    return {
      estado_validacion: "valida",
      es_valida: true,
      reagendada: false,
      pendiente_validacion: false,
    };
  }

  if (finalValidation === "final_not_valid") {
    return {
      estado_validacion: "no_valida",
      es_valida: false,
      reagendada: false,
      pendiente_validacion: false,
    };
  }

  if (finalValidation === "rescheduled") {
    return {
      estado_validacion: "reagendar",
      reagendada: true,
      pendiente_validacion: false,
    };
  }

  if (finalValidation === "in_dispute") {
    return {
      estado_validacion: "en_disputa",
      es_valida: null,
      reagendada: false,
      pendiente_validacion: false,
    };
  }

  if (finalValidation === "under_review") {
    return {
      estado_validacion: "observada_cliente",
      es_valida: null,
      reagendada: false,
      pendiente_validacion: false,
    };
  }

  if (finalValidation === "pending") {
    return {
      estado_validacion: "pendiente_validacion",
      es_valida: null,
      reagendada: false,
      pendiente_validacion: true,
    };
  }

  return {};
}

function commercialPatch(commercialStatus: string | undefined, nextStep: string | undefined) {
  const patch: Record<string, unknown> = {};
  if (typeof commercialStatus === "string" && commercialStatus.trim()) {
    patch.comercial_estado = commercialStatus.trim();
  }
  if (typeof nextStep === "string") {
    patch.comercial_proximo_paso = nextStep;
  }
  return patch;
}

function clientNotesPatch(comment: string | undefined, reasons: string[] | undefined) {
  const patch: Record<string, unknown> = {};
  if (typeof comment === "string" && comment.trim()) {
    patch.observacion = comment.trim();
  }
  if (Array.isArray(reasons) && reasons.length) {
    patch.motivo_no_valida = reasons.filter(Boolean).join(" + ");
  }
  return patch;
}

function meetingStatusPatch(meetingStatus: string | undefined) {
  if (!meetingStatus) return {};
  return {
    estado_reunion:
      meetingStatus === "scheduled"
        ? "confirmed"
        : meetingStatus === "completed"
          ? "completed"
          : meetingStatus,
    no_show: meetingStatus === "no_show",
    cancelada: meetingStatus === "cancelled",
    reagendada: meetingStatus === "rescheduled" ? true : undefined,
  };
}

export async function PATCH(request: Request) {
  try {
    const config = getSupabaseConfig();
    const body = (await request.json()) as {
      id?: string;
      finalValidation?: string;
      meetingStatus?: string;
      commercialStatus?: string;
      nextStep?: string;
      comment?: string;
      reasons?: string[];
    };

    if (!body.id) {
      return NextResponse.json({ error: "Falta id de reunión." }, { status: 400 });
    }

    const payload = Object.fromEntries(
      Object.entries({
        ...validationPatch(body.finalValidation),
        ...meetingStatusPatch(body.meetingStatus),
        ...commercialPatch(body.commercialStatus, body.nextStep),
        ...clientNotesPatch(body.comment, body.reasons),
      }).filter(([, value]) => value !== undefined)
    );

    if (Object.keys(payload).length === 0) {
      return NextResponse.json({ error: "No hay cambios para guardar." }, { status: 400 });
    }

    let updatedRows = await patchSupabaseRows({ ghl_appointment_id: `eq.${body.id}` }, payload, config);
    if (updatedRows.length === 0 && /^\d+$/.test(body.id)) {
      updatedRows = await patchSupabaseRows({ id: `eq.${body.id}` }, payload, config);
    }

    if (updatedRows.length === 0) {
      return NextResponse.json({ error: "No se encontró la reunión para guardar." }, { status: 404 });
    }

    return NextResponse.json({ ok: true, updated: updatedRows.length });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Error desconocido guardando reunión." },
      { status: 500 }
    );
  }
}
