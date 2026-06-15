const fs = require("fs");
const path = require("path");
const readline = require("readline");

const root = process.cwd();
const apolloPath = path.join(root, "CLIENTES", "GBS_LOGISTICS", "08_BASES_Y_CALIFICACION", "00_fuentes", "apollo", "normalizado", "apollo_cp_enriquecida_20260530_113354.csv");
const snovPath = path.join(root, "CLIENTES", "GBS_LOGISTICS", "08_BASES_Y_CALIFICACION", "00_fuentes", "snov", "normalizado", "snov_cp_enriquecida_20260530_113354.csv");
const outDir = path.join(root, "data", "outputs", "Conprospeccion_Campanas");
fs.mkdirSync(outDir, { recursive: true });

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

function csvEscape(v) {
  const s = String(v ?? "");
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function toCsv(rows, columns) {
  return [
    columns.map(csvEscape).join(","),
    ...rows.map((r) => columns.map((c) => csvEscape(r[c])).join(",")),
  ].join("\n");
}

function clean(v) {
  const s = String(v ?? "").trim();
  return /^(nan|none|null|n\/a|-)$/i.test(s) ? "" : s;
}

function hasEmail(email) {
  return /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/.test(clean(email));
}

function domainFrom(email, website) {
  const e = clean(email).toLowerCase();
  if (hasEmail(e)) {
    const d = e.split("@").pop();
    if (!/^(gmail|hotmail|yahoo|outlook|icloud|live|msn|aol|protonmail)\./.test(d)) return d;
  }
  let w = clean(website).toLowerCase().replace(/^https?:\/\//, "").replace(/^www\./, "");
  return w ? w.split("/")[0] : "";
}

function normCompany(company) {
  return clean(company)
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N} ]/gu, " ")
    .replace(/\b(s\.?a\.?|spa|sac|srl|ltda|limitada|inc|corp|company|co|llc|gmbh|sas)\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function normSize(size) {
  const s = clean(size);
  if (!s) return "Desconocido";
  const nums = [...s.matchAll(/\d+/g)].map((m) => Number(m[0]));
  if (!nums.length) return s;
  const n = Math.max(...nums);
  if (n <= 10) return "1-10";
  if (n <= 50) return "11-50";
  if (n <= 200) return "51-200";
  if (n <= 500) return "201-500";
  if (n <= 1000) return "501-1000";
  return "1000+";
}

function normCountry(country) {
  const s = clean(country).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  if (/chile/.test(s)) return "Chile";
  if (/peru/.test(s)) return "Peru";
  if (/colombia/.test(s)) return "Colombia";
  if (/argentina/.test(s)) return "Argentina";
  if (/mexico/.test(s)) return "Mexico";
  if (/brazil|brasil/.test(s)) return "Brasil";
  if (/spain|espana/.test(s)) return "Espana";
  if (/united states|usa|eeuu/.test(s)) return "USA";
  return s ? s.replace(/\b\w/g, (c) => c.toUpperCase()) : "Desconocido";
}

function industrySegment(industry, company) {
  const t = `${industry} ${company}`.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  if (/software|saas|technology|information technology|internet|cloud|computer|it services|telecom|digital|e-commerce|ecommerce/.test(t)) return "Tecnologia, SaaS y servicios IT";
  if (/marketing|advertising|publicidad|media|agency|agencia|market research|events services/.test(t)) return "Marketing, agencias y medios";
  if (/consulting|professional services|management consulting|business consulting|outsourcing|bpo|servicios profesionales/.test(t)) return "Consultoria y servicios B2B";
  if (/financial|bank|banking|fintech|factoring|insurance|seguros|capital markets|investment|credit|credito/.test(t)) return "Finanzas, fintech y seguros";
  if (/staffing|recruiting|human resources|headhunt|talent|rrhh|recursos humanos/.test(t)) return "RRHH, staffing y reclutamiento";
  if (/logistics|transport|freight|supply chain|warehousing|forwarder|courier|cadena de suministro/.test(t)) return "Logistica, transporte y supply chain";
  if (/real estate|construction|building|architecture|inmobili|construccion/.test(t)) return "Inmobiliaria, construccion e infraestructura";
  if (/retail|consumer goods|wholesale|distribution|distributor|apparel|food|beverage|wine|supermarket|restaurants/.test(t)) return "Retail, consumo y distribucion";
  if (/industrial|machinery|manufacturing|mining|automotive|medical devices|equipment|engineering/.test(t)) return "Industrial, manufactura y equipamiento";
  if (/education|higher education|training|capacitacion/.test(t)) return "Educacion y capacitacion";
  return "Otros sectores";
}

function titleSegment(title) {
  const t = clean(title).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  if (/ceo|founder|co-founder|owner|socio|gerente general|general manager|managing director|country manager|president/.test(t)) return "Dueno, founder o gerencia general";
  if (/sales|comercial|commercial|business development|revenue|growth|account executive|ventas|partnership/.test(t)) return "Comercial, ventas, growth o revenue";
  if (/marketing|demand generation|go-to-market|brand|crm|customer acquisition/.test(t)) return "Marketing, demanda o CRM";
  if (/operations|operaciones|supply chain|logistics|procurement|compras/.test(t)) return "Operaciones, compras o supply chain";
  if (/finance|finanzas|administration|administracion|cfo/.test(t)) return "Finanzas o administracion";
  if (/\bhr\b|human resources|people|talent|recruit/.test(t)) return "RRHH o talento";
  if (/director|manager|head|jefe|gerente|lead/.test(t)) return "Gerencia funcional";
  return t ? "Otros cargos" : "Sin cargo";
}

const industryFit = {
  "Tecnologia, SaaS y servicios IT": 30,
  "Marketing, agencias y medios": 30,
  "Consultoria y servicios B2B": 28,
  "Finanzas, fintech y seguros": 27,
  "RRHH, staffing y reclutamiento": 26,
  "Logistica, transporte y supply chain": 23,
  "Inmobiliaria, construccion e infraestructura": 20,
  "Industrial, manufactura y equipamiento": 18,
  "Retail, consumo y distribucion": 16,
  "Educacion y capacitacion": 14,
  "Otros sectores": 8,
};

const titleFit = {
  "Comercial, ventas, growth o revenue": 30,
  "Dueno, founder o gerencia general": 28,
  "Marketing, demanda o CRM": 26,
  "RRHH o talento": 20,
  "Gerencia funcional": 16,
  "Finanzas o administracion": 12,
  "Operaciones, compras o supply chain": 10,
  "Otros cargos": 5,
  "Sin cargo": 0,
};

const countryFit = { Chile: 12, Peru: 10, Colombia: 9, Mexico: 8, Argentina: 7 };
const sizeFit = { "1-10": 5, "11-50": 12, "51-200": 14, "201-500": 12, "501-1000": 8, "1000+": 6, Desconocido: 6 };

function score(row) {
  return Math.min(
    100,
    (industryFit[row.industry_segment] ?? 8) +
      (titleFit[row.title_segment] ?? 5) +
      (countryFit[row.country] ?? 4) +
      (sizeFit[row.size] ?? 6) +
      (row.verified_email ? 8 : 3) +
      (row.domain ? 4 : 0),
  );
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
    if (row && row.has_email && row.company_key) rows.push(row);
  }
  return rows;
}

function apolloMapper(r) {
  const email = clean(r.Email);
  const company = clean(r["Company Name"]) || clean(r.cp_company_name);
  const industry = clean(r.Industry) || clean(r.cp_industry_normalized);
  const country = clean(r["Company Country"]) || clean(r.Country);
  const website = clean(r.Website);
  const row = {
    source: "Apollo",
    company,
    company_key: normCompany(company),
    contact: `${clean(r["First Name"])} ${clean(r["Last Name"])}`.trim(),
    title: clean(r.Title),
    industry,
    country: normCountry(country),
    size: normSize(clean(r["# Employees"])),
    email,
    has_email: hasEmail(email),
    email_status: clean(r["Email Status"]),
    verified_email: /verified|valid/i.test(clean(r["Email Status"])),
    website,
    linkedin: clean(r["Person Linkedin Url"]),
  };
  row.domain = domainFrom(row.email, row.website);
  row.industry_segment = industrySegment(row.industry, row.company);
  row.title_segment = titleSegment(row.title);
  row.cp_fit_score = score(row);
  return row;
}

function snovMapper(r) {
  const email = clean(r.Email);
  const company = clean(r["Nombre de la empresa"]) || clean(r.cp_company_name);
  const industry = clean(r["Sector de la empresa"]) || clean(r.Sector) || clean(r.cp_industry_normalized);
  const country = clean(r["País de la empresa"]) || clean(r["Pais de la empresa"]) || clean(r["País"]) || clean(r.Pais);
  const website = clean(r["URL de la empresa"]);
  const row = {
    source: "Snov",
    company,
    company_key: normCompany(company),
    contact: clean(r["Nombre completo"]),
    title: clean(r.Cargo),
    industry,
    country: normCountry(country),
    size: normSize(clean(r["Tamaño de la empresa"]) || clean(r["Tamano de la empresa"])),
    email,
    has_email: hasEmail(email),
    email_status: clean(r["Estado del email"]),
    verified_email: /valid|verified/i.test(clean(r["Estado del email"])),
    website,
    linkedin: clean(r.LinkedIn),
  };
  row.domain = domainFrom(row.email, row.website);
  row.industry_segment = industrySegment(row.industry, row.company);
  row.title_segment = titleSegment(row.title);
  row.cp_fit_score = score(row);
  return row;
}

function inc(map, key, n = 1) {
  map.set(key || "Desconocido", (map.get(key || "Desconocido") || 0) + n);
}

function topMap(map, limit = 20) {
  return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit).map(([name, count]) => ({ name, count }));
}

function topCounts(rows, field, limit = 3) {
  const m = new Map();
  rows.forEach((r) => inc(m, r[field]));
  return topMap(m, limit).map((x) => `${x.name} (${x.count})`).join("; ");
}

(async () => {
  console.log("Leyendo Apollo...");
  const apollo = await readCsv(apolloPath, apolloMapper);
  console.log(`Apollo con email valido: ${apollo.length}`);
  console.log("Leyendo Snov...");
  const snov = await readCsv(snovPath, snovMapper);
  console.log(`Snov con email valido: ${snov.length}`);

  const all = [...apollo, ...snov];
  const companyMap = new Map();
  const industryContactMap = new Map();
  const industryCompanyKeys = new Map();
  const industryScore = new Map();
  const industryVerified = new Map();
  const sizeMap = new Map();
  const countryMap = new Map();
  const roleMap = new Map();

  for (const row of all) {
    const key = row.domain ? `domain:${row.domain}` : `name:${row.company_key}`;
    if (!companyMap.has(key)) companyMap.set(key, []);
    companyMap.get(key).push(row);
    inc(industryContactMap, row.industry_segment);
    if (!industryCompanyKeys.has(row.industry_segment)) industryCompanyKeys.set(row.industry_segment, new Set());
    industryCompanyKeys.get(row.industry_segment).add(key);
    inc(industryScore, row.industry_segment, row.cp_fit_score);
    if (row.verified_email) inc(industryVerified, row.industry_segment);
    inc(sizeMap, row.size);
    inc(countryMap, row.country);
    inc(roleMap, row.title_segment);
  }

  const companies = [];
  for (const [key, rows] of companyMap.entries()) {
    rows.sort((a, b) => b.cp_fit_score - a.cp_fit_score);
    const top = rows[0];
    const emails = new Set(rows.map((r) => r.email.toLowerCase()));
    const verified = new Set(rows.filter((r) => r.verified_email).map((r) => r.email.toLowerCase()));
    const avg = rows.reduce((s, r) => s + r.cp_fit_score, 0) / rows.length;
    const companyScore = Math.round(((avg * 0.4 + top.cp_fit_score * 0.6 + Math.min(emails.size, 5)) + Number.EPSILON) * 10) / 10;
    companies.push({
      company: top.company,
      domain: top.domain,
      source: [...new Set(rows.map((r) => r.source))].join("+"),
      recommended_segment: top.industry_segment,
      predominant_country: top.country,
      predominant_size: top.size,
      contacts_with_email: emails.size,
      verified_emails: verified.size,
      top_role_segments: topCounts(rows, "title_segment", 3),
      industry_evidence: topCounts(rows, "industry_segment", 2),
      country_evidence: topCounts(rows, "country", 3),
      size_evidence: topCounts(rows, "size", 2),
      sample_contact: top.contact,
      sample_title: top.title,
      sample_email: top.email,
      website: top.website,
      score_conprospeccion: companyScore,
      duplicate_contact_rows: rows.length,
    });
  }

  const recommended = companies
    .filter((c) => c.recommended_segment !== "Otros sectores" && c.contacts_with_email >= 1 && c.score_conprospeccion >= 55)
    .sort((a, b) => b.score_conprospeccion - a.score_conprospeccion || b.contacts_with_email - a.contacts_with_email);

  const companyCols = [
    "company", "domain", "source", "recommended_segment", "predominant_country", "predominant_size",
    "contacts_with_email", "verified_emails", "top_role_segments", "industry_evidence", "country_evidence",
    "size_evidence", "sample_contact", "sample_title", "sample_email", "website", "score_conprospeccion",
    "duplicate_contact_rows",
  ];
  fs.writeFileSync(path.join(outDir, "empresas_recomendadas_conprospeccion.csv"), toCsv(recommended, companyCols), "utf8");

  const industryStats = topMap(industryContactMap, 30).map(({ name, count }) => ({
    segmento: name,
    contactos_email: count,
    empresas: industryCompanyKeys.get(name)?.size ?? 0,
    score_promedio: Math.round((industryScore.get(name) / count) * 10) / 10,
    email_verificado_pct: Math.round(((industryVerified.get(name) || 0) / count) * 1000) / 10,
  }));

  const topSegments = [...recommended.reduce((m, c) => {
    if (!m.has(c.recommended_segment)) m.set(c.recommended_segment, []);
    m.get(c.recommended_segment).push(c);
    return m;
  }, new Map()).entries()].map(([segmento, rows]) => ({
    segmento,
    empresas_recomendadas: rows.length,
    contactos_email: rows.reduce((s, r) => s + r.contacts_with_email, 0),
    score_promedio: Math.round((rows.reduce((s, r) => s + r.score_conprospeccion, 0) / rows.length) * 10) / 10,
    paises_principales: topCounts(rows, "predominant_country", 3),
    tamano_predominante: topMap(rows.reduce((m, r) => (inc(m, r.predominant_size), m), new Map()), 1)[0]?.name || "",
  })).sort((a, b) => b.score_promedio - a.score_promedio || b.empresas_recomendadas - a.empresas_recomendadas).slice(0, 10);

  const duplicateCompanies = companies
    .filter((c) => c.duplicate_contact_rows > 1)
    .sort((a, b) => b.duplicate_contact_rows - a.duplicate_contact_rows)
    .slice(0, 20)
    .map((c) => ({
      company: c.company,
      domain: c.domain,
      source: c.source,
      duplicate_contact_rows: c.duplicate_contact_rows,
      contacts_with_email: c.contacts_with_email,
      recommended_segment: c.recommended_segment,
    }));

  const campaigns = [
    { campana: "Prospeccion para empresas tech y SaaS", segmento: "Tecnologia, SaaS y servicios IT", motivo: "Alto dolor de crecimiento outbound, ciclos B2B y uso natural de datos comerciales." },
    { campana: "Leads listos para agencias B2B", segmento: "Marketing, agencias y medios", motivo: "Agencias venden crecimiento y necesitan bases por nicho para clientes o nuevas cuentas." },
    { campana: "Inteligencia comercial para consultoras B2B", segmento: "Consultoria y servicios B2B", motivo: "Servicios de alto ticket con necesidad constante de prospeccion dirigida." },
    { campana: "Bases verificadas para fintech, factoring y seguros", segmento: "Finanzas, fintech y seguros", motivo: "Mercados con equipos comerciales activos y compra frecuente de data por vertical." },
    { campana: "Prospeccion para RRHH y recruiting", segmento: "RRHH, staffing y reclutamiento", motivo: "Necesitan identificar empresas contratantes y decisores por cargo e industria." },
  ];

  const report = [];
  report.push("# Informe ejecutivo - Campanas Conprospeccion", "");
  report.push(`Fecha de analisis: ${new Date().toISOString().slice(0, 19).replace("T", " ")}`, "");
  report.push("## Fuentes usadas");
  report.push(`- Apollo enriquecido: ${apolloPath}`);
  report.push(`- Snov enriquecido: ${snovPath}`, "");
  report.push("## Resumen");
  report.push(`- Registros con email valido analizados: ${all.length}`);
  report.push(`- Empresas consolidadas con email: ${companies.length}`);
  report.push(`- Empresas recomendadas: ${recommended.length}`);
  report.push(`- Grupos de empresa/dominio duplicados: ${companies.filter((c) => c.duplicate_contact_rows > 1).length}`, "");
  report.push("## Industrias con mas registros con email", "```csv");
  report.push(toCsv(industryStats.slice(0, 15), ["segmento", "contactos_email", "empresas", "score_promedio", "email_verificado_pct"]));
  report.push("```", "");
  report.push("## Tamano de empresa predominante", "```csv");
  report.push(toCsv(topMap(sizeMap, 20).map((x) => ({ tamano: x.name, contactos_email: x.count })), ["tamano", "contactos_email"]));
  report.push("```", "");
  report.push("## Paises disponibles", "```csv");
  report.push(toCsv(topMap(countryMap, 20).map((x) => ({ pais: x.name, contactos_email: x.count })), ["pais", "contactos_email"]));
  report.push("```", "");
  report.push("## Cargos disponibles", "```csv");
  report.push(toCsv(topMap(roleMap, 20).map((x) => ({ cargo_segmento: x.name, contactos_email: x.count })), ["cargo_segmento", "contactos_email"]));
  report.push("```", "");
  report.push("## Empresas duplicadas principales", "```csv");
  report.push(toCsv(duplicateCompanies, ["company", "domain", "source", "duplicate_contact_rows", "contacts_with_email", "recommended_segment"]));
  report.push("```", "");
  report.push("## Top 10 segmentos recomendados", "```csv");
  report.push(toCsv(topSegments, ["segmento", "empresas_recomendadas", "contactos_email", "score_promedio", "paises_principales", "tamano_predominante"]));
  report.push("```", "");
  report.push("## Top 5 campanas para lanzar inmediatamente", "```csv");
  report.push(toCsv(campaigns, ["campana", "segmento", "motivo"]));
  report.push("```", "");
  report.push("## Criterio de recomendacion");
  report.push("Se priorizaron empresas con email valido, cargos comerciales/gerenciales/marketing, industrias donde la compra de bases e inteligencia comercial es una necesidad directa, paises LATAM accionables y tamanos 11-500 empleados. El CSV final esta deduplicado por dominio cuando existe, o por nombre normalizado de empresa.");

  fs.writeFileSync(path.join(outDir, "informe_ejecutivo_conprospeccion.md"), report.join("\n"), "utf8");
  fs.writeFileSync(path.join(outDir, "resumen_analisis.json"), JSON.stringify({
    output_dir: outDir,
    report: path.join(outDir, "informe_ejecutivo_conprospeccion.md"),
    recommended_csv: path.join(outDir, "empresas_recomendadas_conprospeccion.csv"),
    contacts_with_email: all.length,
    companies_with_email: companies.length,
    recommended_companies: recommended.length,
  }, null, 2), "utf8");
  console.log(`Listo: ${outDir}`);
})();
