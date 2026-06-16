import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const {
  MEETINGS_INPUT = "docs/data/gbs-meetings.json",
  MEETINGS_OUTPUT = MEETINGS_INPUT,
  MANUAL_MEETINGS = "docs/data/gbs-manual-meetings.json",
  GOOGLE_MEET_EVIDENCE = "docs/data/gbs-meeting-evidence.json",
  GOOGLE_MEET_TRANSCRIPTS_DIR = "docs/data/google-meet-transcripts",
} = process.env;

function normalize(value = "") {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9@.]+/g, " ")
    .trim();
}

function words(value = "") {
  return normalize(value).split(/\s+/).filter((word) => word.length > 2);
}

function meetCode(url = "") {
  return String(url).match(/[a-z]{3}-[a-z]{4}-[a-z]{3}/i)?.[0]?.toLowerCase() || "";
}

async function readJson(filePath, fallback) {
  try {
    return JSON.parse(await readFile(path.resolve(filePath), "utf8"));
  } catch {
    return fallback;
  }
}

async function readLocalTranscriptFiles(rootDir) {
  const root = path.resolve(rootDir);
  const found = [];

  async function walk(dir) {
    let entries = [];
    try {
      entries = await readdir(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
        continue;
      }

      if (!/\.(txt|md|json)$/i.test(entry.name)) continue;
      const info = await stat(fullPath);
      const raw = await readFile(fullPath, "utf8");
      let text = raw;
      let metadata = {};

      if (/\.json$/i.test(entry.name)) {
        try {
          const parsed = JSON.parse(raw);
          metadata = parsed;
          text = parsed.text || parsed.transcript || parsed.content || JSON.stringify(parsed);
        } catch {
          text = raw;
        }
      }

      found.push({
        title: metadata.title || entry.name.replace(/\.[^.]+$/, ""),
        filePath: fullPath,
        dateIso: metadata.dateIso || "",
        meetingUrl: metadata.meetingUrl || "",
        url: metadata.url || "",
        recordingUrl: metadata.recordingUrl || "",
        modifiedAt: info.mtime.toISOString(),
        text,
      });
    }
  }

  await walk(root);
  return found;
}

function scoreEvidence(meeting, evidence) {
  const haystack = normalize(
    [
      evidence.title,
      evidence.filePath,
      evidence.text?.slice(0, 2000),
      evidence.url,
      evidence.meetingUrl,
      evidence.recordingUrl,
    ].join(" "),
  );
  let score = 0;

  if (meeting.dateIso && evidence.dateIso === meeting.dateIso) score += 8;
  if (meeting.dateIso && haystack.includes(meeting.dateIso)) score += 5;

  const meetingCode = meetCode(meeting.meetingUrl);
  if (meetingCode && (meetCode(evidence.meetingUrl) === meetingCode || haystack.includes(meetingCode))) score += 20;

  for (const word of words(meeting.company)) {
    if (haystack.includes(word)) score += 3;
  }
  for (const word of words(meeting.person)) {
    if (haystack.includes(word)) score += 3;
  }
  if (meeting.email && haystack.includes(normalize(meeting.email))) score += 10;

  return score;
}

function compactEvidence(text = "") {
  return String(text).replace(/\s+/g, " ").trim();
}

function detectBant(text = "") {
  const source = normalize(text);
  const checks = [
    {
      key: "Budget",
      hit: /\b(presupuesto|budget|cotizacion|cotizar|precio|tarifa|costo|costos|propuesta economica)\b/.test(source),
    },
    {
      key: "Authority",
      hit: /\b(decision|decisor|gerente|directora|director|jefe|aprobacion|aprueba|equipo comercial|comex|logistica)\b/.test(source),
    },
    {
      key: "Need",
      hit: /\b(necesidad|problema|dolor|requiere|busca|interes|exportar|importar|operacion|seguimiento|servicio)\b/.test(source),
    },
    {
      key: "Timeline",
      hit: /\b(fecha|plazo|proximo|siguiente|semana|mes|urgente|coordinar|agendar|enviar|reunion)\b/.test(source),
    },
  ];

  return checks.filter((check) => check.hit).map((check) => check.key);
}

function analyzeEvidence(meeting, evidence) {
  if (!evidence) {
    return {
      aiStatus: "Sin transcripcion",
      cpValidation: meeting.cpValidation,
      transcriptSummary: "Pendiente de transcripcion. Falta encontrar el Doc de Google Meet o pegar la transcripcion exportada.",
      evidenceSummary: meeting.evidenceSummary,
      nextStep: meeting.nextStep,
      bantDetected: [],
      evidenceUrl: "",
      recordingUrl: "",
      evidenceSource: "GHL",
    };
  }

  const text = compactEvidence(evidence.text);
  const bantDetected = detectBant(text);
  const cancelled = meeting.filter === "reagendada" || /cancelad|no se conecta|no asist|reagend/i.test(text);
  const effective = text.length > 120 && !cancelled;
  const enoughBant = bantDetected.length >= 2;

  let cpValidation = "Reunion no valida";
  if (cancelled) cpValidation = "Reagendar reunion";
  else if (effective && enoughBant) cpValidation = "Reunion valida";

  const shortText = evidence.summary || text.slice(0, 900);
  return {
    aiStatus: "Evidencia encontrada",
    cpValidation,
    transcriptSummary:
      shortText ||
      "La transcripcion esta enlazada, pero no se pudo extraer texto suficiente para resumir automaticamente.",
    evidenceSummary: evidence.evidenceSummary || [
      effective ? "Se encontro transcripcion de la reunion." : "La evidencia no confirma una reunion efectiva completa.",
      bantDetected.length ? `Variables detectadas: ${bantDetected.join(", ")}.` : "No se detectaron variables BANT suficientes.",
      cancelled ? "Corresponde revisar reagenda o no asistencia." : "Revisar con cliente si cuenta para la meta.",
    ].join(" "),
    nextStep:
      cpValidation === "Reunion valida"
        ? "Cliente revisa evidencia y confirma si cuenta para la meta."
        : cpValidation === "Reagendar reunion"
          ? "Confirmar motivo y nueva fecha de reunion."
          : "Pedir revision de evidencia antes de contarla para meta.",
    bantDetected,
    evidenceUrl: evidence.url || "",
    recordingUrl: evidence.recordingUrl || "",
    evidenceSource: evidence.sourceLabel || (evidence.filePath ? "Google Meet exportado" : "Google Drive"),
  };
}

function displayValidation(value) {
  if (value === "Reunion valida") return "Reunión válida";
  if (value === "Reunion no valida") return "Reunión no válida";
  if (value === "Reagendar reunion") return "Reagendar reunión";
  return value;
}

const payload = await readJson(MEETINGS_INPUT, null);
if (!payload?.meetings) {
  console.error(`No meetings found in ${MEETINGS_INPUT}`);
  process.exit(1);
}

const manifest = await readJson(GOOGLE_MEET_EVIDENCE, { items: [] });
const manualMeetings = await readJson(MANUAL_MEETINGS, { items: [] });
const localFiles = await readLocalTranscriptFiles(GOOGLE_MEET_TRANSCRIPTS_DIR);
const evidenceItems = [...(manifest.items || []), ...localFiles];
const meetingMap = new Map();
for (const meeting of [...payload.meetings, ...(manualMeetings.items || [])]) {
  meetingMap.set(meeting.id, meeting);
}

const enriched = [...meetingMap.values()]
  .sort((a, b) => String(a.startTime || a.dateIso || "").localeCompare(String(b.startTime || b.dateIso || "")))
  .map((meeting) => {
  const ranked = evidenceItems
    .map((item) => ({ item, score: scoreEvidence(meeting, item) }))
    .filter((match) => match.score >= 8)
    .sort((a, b) => b.score - a.score);

  const best = ranked[0]?.item;
  const analysis = analyzeEvidence(meeting, best);
  const cpValidation = displayValidation(analysis.cpValidation);
  const chips = new Set([...(meeting.chips || []), analysis.aiStatus]);

  for (const criteria of analysis.bantDetected) {
    chips.add(`BANT: ${criteria}`);
  }

  return {
    ...meeting,
    cpValidation,
    transcriptSummary: analysis.transcriptSummary,
    evidenceSummary: analysis.evidenceSummary,
    nextStep: analysis.nextStep,
    evidenceSource: analysis.evidenceSource,
    evidenceUrl: analysis.evidenceUrl,
    recordingUrl: analysis.recordingUrl,
    bantDetected: analysis.bantDetected,
    evidenceMatchScore: ranked[0]?.score || 0,
    chips: [...chips],
  };
  });

const output = {
  ...payload,
  generatedAt: new Date().toISOString(),
  evidenceSource: {
    manifest: GOOGLE_MEET_EVIDENCE,
    manualMeetings: MANUAL_MEETINGS,
    transcriptsDir: GOOGLE_MEET_TRANSCRIPTS_DIR,
    itemsFound: evidenceItems.length,
    manualMeetingsFound: manualMeetings.items?.length || 0,
  },
  meetings: enriched,
};

const outputPath = path.resolve(MEETINGS_OUTPUT);
await mkdir(path.dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");

console.log(`Enriched ${enriched.length} meetings with ${evidenceItems.length} evidence item(s).`);
console.log(`Wrote ${outputPath}`);
