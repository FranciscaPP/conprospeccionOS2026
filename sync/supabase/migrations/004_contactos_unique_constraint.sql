drop index if exists public.contactos_ghl_contact_id_uidx;

create unique index if not exists contactos_ghl_contact_id_uidx
  on public.contactos(ghl_contact_id);
