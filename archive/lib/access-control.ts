export type ActiveClientSlug = "clickie" | "gbs" | "bambutech";

export type AgencyRole = "agency_admin" | "sdr_leader" | "client_admin" | "client_viewer";

export type AccessProfile = {
  id: string;
  label: string;
  role: AgencyRole;
  clientSlugs: ActiveClientSlug[];
};

export const ACTIVE_CLIENTS: Array<{
  slug: ActiveClientSlug;
  displayName: string;
  monthlyGoal: number;
  validationPath: string;
}> = [
  {
    slug: "clickie",
    displayName: "CLICKIE",
    monthlyGoal: 6,
    validationPath: "/client/meeting-validation?client=clickie",
  },
  {
    slug: "gbs",
    displayName: "GBS LOGISTICS",
    monthlyGoal: 45,
    validationPath: "/client/meeting-validation?client=gbs",
  },
  {
    slug: "bambutech",
    displayName: "BAMBUTECH",
    monthlyGoal: 12,
    validationPath: "/client/meeting-validation?client=bambutech",
  },
];

export const ACCESS_PROFILES: AccessProfile[] = [
  {
    id: "agency-owner",
    label: "Agencia / administracion",
    role: "agency_admin",
    clientSlugs: ["clickie", "gbs", "bambutech"],
  },
  {
    id: "sdr-leader",
    label: "SDR lider",
    role: "sdr_leader",
    clientSlugs: ["clickie", "gbs", "bambutech"],
  },
  {
    id: "client-clickie",
    label: "Cliente Clickie",
    role: "client_admin",
    clientSlugs: ["clickie"],
  },
  {
    id: "client-gbs",
    label: "Cliente GBS",
    role: "client_admin",
    clientSlugs: ["gbs"],
  },
  {
    id: "client-bambutech",
    label: "Cliente BambuTech",
    role: "client_admin",
    clientSlugs: ["bambutech"],
  },
];

export function normalizeClientSlug(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

export function clientSlugFromName(value: string): ActiveClientSlug | null {
  const normalized = normalizeClientSlug(value);
  if (normalized.includes("clickie")) return "clickie";
  if (normalized.includes("gbs")) return "gbs";
  if (normalized.includes("bambu")) return "bambutech";
  return null;
}

export function isActiveClientName(value: string) {
  return clientSlugFromName(value) !== null;
}

export function getClientAccess(slug: string | null | undefined) {
  const activeSlug = slug ? clientSlugFromName(slug) : null;
  return activeSlug ? ACTIVE_CLIENTS.find((client) => client.slug === activeSlug) ?? null : null;
}
