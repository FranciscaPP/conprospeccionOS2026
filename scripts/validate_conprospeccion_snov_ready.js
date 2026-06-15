const fs = require("fs");

const p = "data/outputs/Conprospeccion_Campanas/snov_ready/ALL_campaign_contacts_snov_import.csv";

function parse(line) {
  const out = [];
  let cur = "";
  let q = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (q && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        q = !q;
      }
    } else if (ch === "," && !q) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

const lines = fs.readFileSync(p, "utf8").trim().split(/\r?\n/);
const headers = parse(lines[0]);
const rows = lines.slice(1).map((line) => Object.fromEntries(parse(line).map((v, i) => [headers[i], v])));
const emails = rows.map((r) => r.email.toLowerCase());
const byCompany = new Map();
for (const r of rows) {
  const key = (r.website || r.email.split("@")[1] || r.company)
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split("/")[0];
  byCompany.set(key, (byCompany.get(key) || 0) + 1);
}

const over = [...byCompany.entries()].filter(([, n]) => n > 2);
console.log(JSON.stringify({
  rows: rows.length,
  uniqueEmails: new Set(emails).size,
  emailDuplicates: emails.length - new Set(emails).size,
  companiesOver2: over.length,
  overSample: over.slice(0, 5),
  columns: headers,
}, null, 2));
