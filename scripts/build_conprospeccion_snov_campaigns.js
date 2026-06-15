const fs = require("fs");
const path = require("path");
const readline = require("readline");

const root = process.cwd();
const sourceDir = path.join(root, "CLIENTES", "GBS_LOGISTICS", "08_BASES_Y_CALIFICACION", "00_fuentes");
const apolloPath = path.join(sourceDir, "apollo", "normalizado", "apollo_cp_enriquecida_20260530_113354.csv");
const snovPath = path.join(sourceDir, "snov", "normalizado", "snov_cp_enriquecida_20260530_113354.csv");
const outDir = path.join(root, "data", "outputs", "Conprospeccion_Campanas", "snov_ready");
fs.mkdirSync(outDir, { recursive: true });

const CAMPAIGNS = [
  {
    id: "P1_INDUSTRIAL",
    name: "CP - P1 Industrial B2B oportunidades",
    priority: 1,
    subject: "{{first_name}}, oportunidades comerciales para {{company}}",
    segments: [
      "Seguridad industrial",
      "Mantenimiento industrial",
      "Instalacion industrial",
      "Energia",
      "Eficiencia energetica",
      "Monitoreo industrial",
      "Proveedores industriales B2B",
    ],
  },
  {
    id: "P2_FINANCIERO_B2B",
    name: "CP - P2 Servicios financieros B2B",
    priority: 2,
    subject: "{{first_name}}, empresas que podrian necesitar {{company}}",
    segments: ["Factoring", "Leasing", "Seguros corporativos", "Servicios financieros B2B"],
  },
  {
    id: "P3_RRHH_B2B",
    name: "CP - P3 RRHH y staffing B2B",
    priority: 3,
    subject: "{{first_name}}, oportunidades para servicios de RRHH B2B",
    segments: ["Reclutamiento especializado", "Staffing", "RRHH B2B"],
  },
  {
    id: "P4_CONSULTORIA_ESPECIALIZADA",
    name: "CP - P4 Compliance capacitacion consultoria",
    priority: 4,
    subject: "{{first_name}}, oportunidades para consultoria especializada",
    segments: ["Compliance", "Certificaciones", "Capacitacion corporativa", "Consultoria especializada B2B"],
  },
];

function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "," && !quoted) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

function csvEscape(value) {
  const s = String(value ?? "");
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function writeCsv(file, rows, columns) {
  const text = [columns.join(","), ...rows.map((r) => columns.map((c) => csvEscape(r[c])).join(","))].join("\n");
  fs.writeFileSync(file, text, "utf8");
}

function clean(v) {
  const s = String(v ?? "").trim();
  return /^(nan|none|null|n\/a|-|undefined)$/i.test(s) ? "" : s;
}

function ascii(v) {
  return clean(v).normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function lower(v) {
  return ascii(v).toLowerCase();
}

function hasEmail(email) {
  return /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/.test(clean(email));
}

function isCorporateEmail(email) {
  if (!hasEmail(email)) return false;
  const d = clean(email).toLowerCase().split("@").pop();
  return !/^(gmail|hotmail|yahoo|outlook|icloud|live|msn|aol|protonmail|mail)\./.test(d);
}

function websiteDomain(website) {
  let w = clean(website).toLowerCase().replace(/^https?:\/\//, "").replace(/^www\./, "");
  return w ? w.split("/")[0] : "";
}

function domainFrom(email, website) {
  const e = clean(email).toLowerCase();
  if (hasEmail(e)) {
    const d = e.split("@").pop();
    if (!/^(gmail|hotmail|yahoo|outlook|icloud|live|msn|aol|protonmail|mail)\./.test(d)) return d;
  }
  return websiteDomain(website);
}

function normCompany(company) {
  return lower(company)
    .replace(/[^\p{L}\p{N} ]/gu, " ")
    .replace(/\b(s\.?a\.?|spa|sac|srl|ltda|limitada|inc|corp|company|co|llc|gmbh|sas|sa de cv|sapi)\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function normCountry(v) {
  const s = lower(v);
  if (/chile|\bcl\b/.test(s)) return "Chile";
  if (/peru|\bpe\b/.test(s)) return "Peru";
  if (/mexico|\bmx\b/.test(s)) return "Mexico";
  if (/colombia/.test(s)) return "Colombia";
  if (/argentina/.test(s)) return "Argentina";
  if (/spain|espana/.test(s)) return "Espana";
  if (/united states|usa|estados unidos/.test(s)) return "USA";
  return s ? s.replace(/\b\w/g, (c) => c.toUpperCase()) : "";
}

function normSize(size) {
  const s = clean(size);
  if (!s) return { label: "Desconocido", max: null };
  if (/self/i.test(s)) return { label: "1-10", max: 10 };
  const nums = [...s.matchAll(/\d+/g)].map((m) => Number(m[0]));
  if (!nums.length) return { label: s, max: null };
  const n = Math.max(...nums);
  if (n <= 10) return { label: "1-10", max: 10 };
  if (n <= 50) return { label: "11-50", max: 50 };
  if (n <= 200) return { label: "51-200", max: 200 };
  if (n <= 500) return { label: "201-500", max: 500 };
  if (n <= 1000) return { label: "501-1000", max: 1000 };
  return { label: "1000+", max: 1001 };
}

function splitName(full, first, last) {
  const f = clean(first);
  const l = clean(last);
  if (f || l) return { first: f, last: l };
  const parts = clean(full).split(/\s+/).filter(Boolean);
  return { first: parts[0] || "", last: parts.slice(1).join(" ") };
}

function isTargetCountry(country) {
  return ["Chile", "Mexico", "Peru"].includes(country);
}

function isAllowedSize(sizeMax) {
  return sizeMax === null || sizeMax <= 200;
}

function isExcludedIndustry(row) {
  const t = lower(`${row.company} ${row.industry} ${row.title} ${row.website}`);
  return /marketing digital|digital marketing|advertising agency|agencia de marketing|marketing agency|software factory|desarrollo de software|software development|web design|diseno web|diseño web|saas|software as a service/.test(t);
}

function roleSegment(title) {
  const t = lower(title);
  if (/founder|co-founder|cofounder|ceo|chief executive|managing director|gerente general|general manager|director comercial|gerente comercial|business development manager|revenue manager|growth manager|socio|partner|country manager|commercial director|sales director|head of sales|director of sales/.test(t)) {
    return "Senior comercial o direccion";
  }
  if (/intern|practicante|assistant|asistente|trainee|junior|student|analyst|analista|executive assistant|coordinator|coordinador|vendedor|salesperson|representative|representante|supervisor|specialist|especialista/.test(t)) {
    return "Junior excluido";
  }
  return "No prioritario";
}

function classifyOffer(row) {
  const t = lower(`${row.company} ${row.industry} ${row.title} ${row.website}`);
  const matches = [];
  const has = (segment, re) => {
    if (re.test(t)) matches.push(segment);
  };

  has("Seguridad industrial", /seguridad industrial|safety|hse|ehs|prevencion de riesgos|prevencion|riesgos laborales|occupational safety|industrial safety|salud ocupacional/);
  has("Mantenimiento industrial", /mantenimiento industrial|industrial maintenance|maintenance|mantencion|mro|asset maintenance|reparacion industrial|servicio tecnico industrial/);
  has("Instalacion industrial", /instalacion industrial|instalaciones industriales|montaje industrial|industrial installation|assembly|commissioning|facility installation|engineering services/);
  has("Energia", /energia|energy|power|electric|electrical|solar|renewable|utilities|oil|gas|eolica|electromecan/);
  has("Eficiencia energetica", /eficiencia energetica|energy efficiency|energy management|ahorro energetico|auditoria energetica/);
  has("Monitoreo industrial", /monitoreo industrial|monitoring|condition monitoring|iot industrial|scada|telemetria|sensor|predictive maintenance|automation|automatizacion|instrumentacion/);
  has("Proveedores industriales B2B", /industrial|manufacturing|machinery|equipment|mining|metalmecan|automatizacion|automation|engineering|proveedor industrial|suministros industriales|herramientas|industrial supplies/);

  has("Factoring", /factoring|invoice financing|financiamiento de facturas|anticipo de facturas/);
  has("Leasing", /leasing|arrendamiento financiero|asset finance/);
  has("Seguros corporativos", /seguro|insurance|broker de seguros|risk management|beneficios corporativos|corredora de seguros/);
  has("Servicios financieros B2B", /financial services|servicios financieros|fintech|credito|credit|capital|financing|financiamiento|payment|pagos|cobranza|lending/);

  has("Reclutamiento especializado", /recruit|reclutamiento|seleccion de personal|headhunt|talent acquisition|executive search/);
  has("Staffing", /staffing|outsourcing de personal|temporary staffing|personal temporal|servicios transitorios/);
  has("RRHH B2B", /human resources|recursos humanos|rrhh|people|talent|payroll|nomina|remuneraciones|beneficios/);

  has("Compliance", /compliance|cumplimiento|regulatory|regulatorio|risk advisory|auditoria|audit|governance|iso 37001|iso 27001|aml|kyc|data protection/);
  has("Certificaciones", /certificacion|certification|iso 9001|iso 14001|iso 45001|norma iso|certificadora|quality certification/);
  has("Capacitacion corporativa", /capacitacion|training|corporate training|formacion|e-learning|elearning|academy|learning/);
  has("Consultoria especializada B2B", /consulting|consultoria|advisory|asesoria|professional services|servicios profesionales|management consulting|business consulting/);

  for (const campaign of CAMPAIGNS) {
    const hit = matches.find((m) => campaign.segments.includes(m));
    if (hit) return { campaign_id: campaign.id, campaign_name: campaign.name, segment: hit, priority: campaign.priority };
  }
  return null;
}

function demandCategory(row) {
  const t = lower(`${row.company} ${row.industry} ${row.title}`);
  if (/mining|miner|industrial|manufacturing|machinery|construction|building|energy|logistics|transport|warehousing|oil|gas|automotive|equipment/.test(t)) return "industrial";
  if (/retail|consumer|food|beverage|wholesale|distribution|restaurants|apparel/.test(t)) return "retail";
  if (/financial|bank|insurance|fintech|factoring|leasing/.test(t)) return "finance";
  if (/health|medical|pharma|clinic|hospital/.test(t)) return "health";
  if (/technology|software|telecom|internet|it services/.test(t)) return "tech";
  return "general";
}

function suggestionTargetsFor(campaignId) {
  if (campaignId === "P1_INDUSTRIAL") return new Set(["industrial", "retail", "logistics", "health"]);
  if (campaignId === "P2_FINANCIERO_B2B") return new Set(["industrial", "retail", "logistics", "general"]);
  if (campaignId === "P3_RRHH_B2B") return new Set(["industrial", "retail", "logistics", "finance", "health"]);
  if (campaignId === "P4_CONSULTORIA_ESPECIALIZADA") return new Set(["industrial", "finance", "health", "retail", "logistics"]);
  return new Set(["general"]);
}

function motiveFor(campaignId, company) {
  const ind = clean(company.industry);
  if (campaignId === "P1_INDUSTRIAL") {
    if (/mining|miner/i.test(ind)) return "Opera en mineria y puede requerir servicios industriales especializados.";
    if (/energy|energia|electric/i.test(ind)) return "Opera en energia y puede requerir soporte tecnico u operacional.";
    return "Tiene operacion industrial y puede requerir proveedores B2B especializados.";
  }
  if (campaignId === "P2_FINANCIERO_B2B") return "Empresa B2B que puede requerir financiamiento, leasing o cobertura corporativa.";
  if (campaignId === "P3_RRHH_B2B") return "Empresa con operacion intensiva y posible necesidad de talento especializado.";
  if (campaignId === "P4_CONSULTORIA_ESPECIALIZADA") return "Opera en un sector regulado o tecnico y puede requerir consultoria especializada.";
  return "Puede requerir servicios B2B similares.";
}

async function readCsv(file, mapper) {
  const rows = [];
  const rl = readline.createInterface({ input: fs.createReadStream(file, { encoding: "utf8" }), crlfDelay: Infinity });
  let headers = null;
  for await (const line of rl) {
    if (!headers) {
      headers = parseCsvLine(line.replace(/^\uFEFF/, ""));
      continue;
    }
    if (!line.trim()) continue;
    const values = parseCsvLine(line);
    const rec = {};
    headers.forEach((h, i) => { rec[h] = values[i] ?? ""; });
    const row = mapper(rec);
    if (row) rows.push(row);
  }
  return rows;
}

function apolloMapper(r) {
  const email = clean(r.Email);
  const company = clean(r["Company Name"]) || clean(r.cp_company_name);
  const website = clean(r.Website);
  const industry = clean(r.Industry) || clean(r.cp_industry_normalized);
  const country = normCountry(clean(r["Company Country"]) || clean(r.Country) || clean(r.cp_country_normalized));
  const size = normSize(clean(r["# Employees"]) || clean(r.cp_company_size_normalized));
  const name = splitName("", clean(r["First Name"]), clean(r["Last Name"]));
  return {
    source: "Apollo",
    first_name: name.first,
    last_name: name.last,
    email,
    email_status: clean(r["Email Status"]),
    verified_email: /verified|valid/i.test(clean(r["Email Status"])),
    title: clean(r.Title) || clean(r.cp_title_normalized),
    company,
    company_key: normCompany(company),
    domain: domainFrom(email, website),
    industry,
    country,
    size: size.label,
    size_max: size.max,
    website,
    company_linkedin: clean(r["Company Linkedin Url"]),
    person_linkedin: clean(r["Person Linkedin Url"]),
  };
}

function snovMapper(r) {
  const email = clean(r.Email);
  const company = clean(r["Nombre de la empresa"]) || clean(r.cp_company_name);
  const website = clean(r["URL de la empresa"]) || clean(r["Sitio web de la empresa (campo personalizado)"]);
  const industry = clean(r["Sector de la empresa"]) || clean(r.Sector) || clean(r.cp_industry_normalized);
  const country = normCountry(clean(r["País de la empresa"]) || clean(r["País"]) || clean(r.cp_country_normalized));
  const size = normSize(clean(r["Tamaño de la empresa"]) || clean(r["Tamaño Empresa (campo personalizado)"]) || clean(r.cp_company_size_normalized));
  const name = splitName(clean(r["Nombre completo"]), clean(r.Nombre), clean(r.Apellido));
  return {
    source: "Snov",
    first_name: name.first,
    last_name: name.last,
    email,
    email_status: clean(r["Estado del email"]),
    verified_email: /valid|verified/i.test(clean(r["Estado del email"])),
    title: clean(r.Cargo) || clean(r.cp_title_normalized),
    company,
    company_key: normCompany(company),
    domain: domainFrom(email, website),
    industry,
    country,
    size: size.label,
    size_max: size.max,
    website,
    company_linkedin: clean(r["Redes sociales de la empresa"]) || clean(r["Linkedin Empresa (campo personalizado)"]),
    person_linkedin: clean(r.LinkedIn) || clean(r["Linkedin Personal (campo personalizado)"]),
  };
}

function companyKey(row) {
  const webDomain = websiteDomain(row.website);
  return webDomain ? `domain:${webDomain}` : row.domain ? `domain:${row.domain}` : `name:${row.company_key}`;
}

function scoreContact(row, offer) {
  let score = 0;
  score += offer.priority === 1 ? 40 : offer.priority === 2 ? 32 : offer.priority === 3 ? 28 : 24;
  score += row.country === "Chile" ? 18 : row.country === "Mexico" ? 15 : row.country === "Peru" ? 14 : 0;
  score += row.size === "1-10" ? 14 : row.size === "11-50" ? 16 : row.size === "51-200" ? 8 : row.size === "Desconocido" ? 6 : 0;
  score += row.verified_email ? 8 : 3;
  score += /founder|co-founder|ceo|gerente general|general manager|managing director|socio|partner/i.test(row.title) ? 16 : 10;
  score += row.domain ? 4 : 0;
  return score;
}

function makeEmailBody(row, suggestions) {
  return [
    `Hola ${row.first_name},`,
    "",
    "Te comparto algunas empresas que podrían necesitar servicios similares a los que ustedes ofrecen:",
    "",
    `• ${suggestions[0].empresa} – ${suggestions[0].motivo}`,
    "",
    `• ${suggestions[1].empresa} – ${suggestions[1].motivo}`,
    "",
    `• ${suggestions[2].empresa} – ${suggestions[2].motivo}`,
    "",
    "En Conprospección ayudamos a identificar este tipo de oportunidades comerciales y entregamos visibilidad sobre qué industrias, cargos y segmentos generan mejores resultados comerciales.",
    "",
    "Además, si lo necesitan, también implementamos el proceso completo de prospección.",
    "",
    "¿Te interesa que te comparta algunas oportunidades adicionales?",
    "",
    "Francisca Polanco",
    "CEO | Conprospección",
  ].join("\n");
}

(async () => {
  console.log("Leyendo fuentes completas...");
  const all = [...await readCsv(apolloPath, apolloMapper), ...await readCsv(snovPath, snovMapper)]
    .filter((r) => isCorporateEmail(r.email) && r.company_key && r.company);

  const allCompaniesMap = new Map();
  for (const row of all) {
    const key = companyKey(row);
    if (!allCompaniesMap.has(key)) {
      allCompaniesMap.set(key, { ...row, demand_category: demandCategory(row), contact_rows: 0 });
    }
    allCompaniesMap.get(key).contact_rows += 1;
  }
  const allCompanies = [...allCompaniesMap.values()];

  const targetByCompany = new Map();
  const excludedReasons = new Map();
  for (const row of all) {
    const key = companyKey(row);
    if (targetByCompany.has(key)) continue;

    if (!isTargetCountry(row.country)) {
      excludedReasons.set(key, "Pais no prioritario");
      continue;
    }
    if (!isAllowedSize(row.size_max)) {
      excludedReasons.set(key, "Empresa >200 empleados");
      continue;
    }
    if (isExcludedIndustry(row)) {
      excludedReasons.set(key, "Industria excluida");
      continue;
    }
    const offer = classifyOffer(row);
    if (!offer) {
      excludedReasons.set(key, "Sin match de segmento prioritario");
      continue;
    }
    if (roleSegment(row.title) !== "Senior comercial o direccion") {
      excludedReasons.set(key, "Cargo no prioritario o junior");
      continue;
    }
    targetByCompany.set(key, offer);
  }

  const rowsByCompany = new Map();
  for (const row of all) {
    const key = companyKey(row);
    const offer = targetByCompany.get(key);
    if (!offer) continue;
    if (roleSegment(row.title) !== "Senior comercial o direccion") continue;
    if (!isTargetCountry(row.country) || !isAllowedSize(row.size_max) || isExcludedIndustry(row)) continue;
    row.offer = offer;
    row.score = scoreContact(row, offer);
    if (!rowsByCompany.has(key)) rowsByCompany.set(key, []);
    rowsByCompany.get(key).push(row);
  }

  const usedEmails = new Set();
  const selected = [];
  for (const [key, rows] of rowsByCompany.entries()) {
    rows.sort((a, b) => b.score - a.score || (b.verified_email ? 1 : 0) - (a.verified_email ? 1 : 0));
    const topTwo = [];
    for (const row of rows) {
      const emailKey = row.email.toLowerCase();
      if (usedEmails.has(emailKey)) continue;
      topTwo.push(row);
      usedEmails.add(emailKey);
      if (topTwo.length >= 2) break;
    }
    selected.push(...topTwo);
  }

  const suggestionPools = new Map();
  for (const campaign of CAMPAIGNS) {
    const wanted = suggestionTargetsFor(campaign.id);
    suggestionPools.set(
      campaign.id,
      allCompanies
        .filter((c) => wanted.has(c.demand_category) && c.company && !isExcludedIndustry(c))
        .sort((a, b) => (b.contact_rows || 0) - (a.contact_rows || 0)),
    );
  }

  const byCampaign = new Map(CAMPAIGNS.map((c) => [c.id, []]));
  const companySuggestionCache = new Map();
  for (const row of selected) {
    const key = companyKey(row);
    if (!companySuggestionCache.has(key)) {
      const pool = suggestionPools.get(row.offer.campaign_id);
      const suggestions = [];
      const seen = new Set([key]);
      for (const c of pool) {
        const ckey = companyKey(c);
        if (seen.has(ckey)) continue;
        if (c.country && row.country && c.country !== row.country && suggestions.length < 2) continue;
        seen.add(ckey);
        suggestions.push({ empresa: c.company, motivo: motiveFor(row.offer.campaign_id, c) });
        if (suggestions.length >= 5) break;
      }
      if (suggestions.length < 3) {
        for (const c of pool) {
          const ckey = companyKey(c);
          if (seen.has(ckey)) continue;
          seen.add(ckey);
          suggestions.push({ empresa: c.company, motivo: motiveFor(row.offer.campaign_id, c) });
          if (suggestions.length >= 5) break;
        }
      }
      companySuggestionCache.set(key, suggestions);
    }
    const suggestions = companySuggestionCache.get(key);
    if (suggestions.length < 3) continue;
    const out = {
      email: row.email,
      first_name: row.first_name,
      last_name: row.last_name,
      company: row.company,
      title: row.title,
      country: row.country,
      industry: row.industry,
      website: row.website,
      company_linkedin: row.company_linkedin,
      person_linkedin: row.person_linkedin,
      campaign_name: row.offer.campaign_name,
      campaign_id: row.offer.campaign_id,
      segmento_prioritario: row.offer.segment,
      empresa_sugerida_1: suggestions[0].empresa,
      motivo_1: suggestions[0].motivo,
      empresa_sugerida_2: suggestions[1].empresa,
      motivo_2: suggestions[1].motivo,
      empresa_sugerida_3: suggestions[2].empresa,
      motivo_3: suggestions[2].motivo,
      empresa_sugerida_4: suggestions[3]?.empresa || "",
      motivo_4: suggestions[3]?.motivo || "",
      empresa_sugerida_5: suggestions[4]?.empresa || "",
      motivo_5: suggestions[4]?.motivo || "",
      subject: CAMPAIGNS.find((c) => c.id === row.offer.campaign_id).subject,
    };
    byCampaign.get(row.offer.campaign_id).push(out);
  }

  const columns = [
    "email",
    "first_name",
    "last_name",
    "company",
    "title",
    "country",
    "industry",
    "website",
    "company_linkedin",
    "person_linkedin",
    "segmento_prioritario",
    "empresa_sugerida_1",
    "motivo_1",
    "empresa_sugerida_2",
    "motivo_2",
    "empresa_sugerida_3",
    "motivo_3",
    "empresa_sugerida_4",
    "motivo_4",
    "empresa_sugerida_5",
    "motivo_5",
    "subject",
  ];

  const summary = [];
  const allFinal = [];
  for (const campaign of CAMPAIGNS) {
    const rows = byCampaign.get(campaign.id).sort((a, b) => a.country.localeCompare(b.country) || a.company.localeCompare(b.company));
    allFinal.push(...rows);
    const file = path.join(outDir, `${campaign.id}_${campaign.name.replace(/[^A-Za-z0-9]+/g, "_")}.csv`);
    writeCsv(file, rows, columns);
    const companies = new Set(rows.map((r) => `${r.company}|${r.website || r.email.split("@").pop()}`));
    const countries = [...new Set(rows.map((r) => r.country).filter(Boolean))].sort();
    const industries = [...new Set(rows.map((r) => r.segmento_prioritario).filter(Boolean))].sort();
    summary.push({
      campaign_id: campaign.id,
      campaign_name: campaign.name,
      subject: campaign.subject,
      csv_file: file,
      companies: companies.size,
      contacts: rows.length,
      countries: countries.join(", "),
      industries: industries.join("; "),
      suggested_companies_generated: rows.length * 3,
    });
  }
  writeCsv(path.join(outDir, "ALL_campaign_contacts_snov_import.csv"), allFinal, columns);

  const emailTemplate = [
    "Hola {{first_name}},",
    "",
    "Te comparto algunas empresas que podrían necesitar servicios similares a los que ustedes ofrecen:",
    "",
    "• {{empresa_sugerida_1}} – {{motivo_1}}",
    "",
    "• {{empresa_sugerida_2}} – {{motivo_2}}",
    "",
    "• {{empresa_sugerida_3}} – {{motivo_3}}",
    "",
    "En Conprospección ayudamos a identificar este tipo de oportunidades comerciales y entregamos visibilidad sobre qué industrias, cargos y segmentos generan mejores resultados comerciales.",
    "",
    "Además, si lo necesitan, también implementamos el proceso completo de prospección.",
    "",
    "¿Te interesa que te comparta algunas oportunidades adicionales?",
    "",
    "Francisca Polanco",
    "CEO | Conprospección",
  ].join("\n");

  fs.writeFileSync(path.join(outDir, "snov_email_template.txt"), emailTemplate, "utf8");
  fs.writeFileSync(path.join(outDir, "campaign_summary.json"), JSON.stringify({
    generated_at: new Date().toISOString(),
    source_dir: sourceDir,
    total_source_contacts_with_email: all.length,
    total_selected_contacts: allFinal.length,
    total_selected_companies: new Set(allFinal.map((r) => `${r.company}|${r.website || r.email.split("@").pop()}`)).size,
    exclusion_notes: {
      countries: "Solo Chile, Mexico, Peru.",
      size: "Excluye >200 empleados cuando existe informacion de tamano.",
      roles: "Solo founders, CEOs, gerencia general, socios, partners y cargos comerciales/revenue/growth senior.",
      industries: "Excluye marketing agencies, software factory, desarrollo de software, SaaS generico, diseno web y marketing digital.",
    },
    campaigns: summary,
  }, null, 2), "utf8");

  const report = [];
  report.push("# Campanas Conprospeccion listas para Snov", "");
  report.push(`Generado: ${new Date().toISOString()}`, "");
  report.push("## Campanas finales", "");
  report.push(["campaign_id", "campaign_name", "companies", "contacts", "countries", "industries", "suggested_companies_generated", "csv_file"].join(","));
  for (const row of summary) {
    report.push([
      row.campaign_id,
      row.campaign_name,
      row.companies,
      row.contacts,
      row.countries,
      row.industries,
      row.suggested_companies_generated,
      row.csv_file,
    ].map(csvEscape).join(","));
  }
  report.push("", "## Template Snov", "", emailTemplate, "");
  report.push("## Problemas detectados", "");
  report.push("- La creacion/carga en Snov debe hacerse por UI en esta operacion.");
  report.push("- Algunas empresas no tienen tamano informado; se conservaron si cumplian pais, cargo, industria y email.");
  report.push("- Las sugerencias se generaron solo con empresas reales existentes en las bases disponibles.");
  report.push("- Se excluyeron empresas grandes cuando el tamano disponible indicaba mas de 200 empleados.");
  report.push("", "## Recomendacion de lanzamiento", "");
  report.push("Lanzar primero P1 Industrial B2B oportunidades: es el segmento de mayor prioridad estrategica y el mensaje de oportunidades concretas tiene mejor encaje con venta de identificacion de oportunidades, bases estrategicas e inteligencia comercial.");
  fs.writeFileSync(path.join(outDir, "informe_campanas_snov_ready.md"), report.join("\n"), "utf8");

  console.log(JSON.stringify({
    outDir,
    total_selected_contacts: allFinal.length,
    campaigns: summary.map((s) => ({ id: s.campaign_id, contacts: s.contacts, companies: s.companies })),
  }, null, 2));
})();
