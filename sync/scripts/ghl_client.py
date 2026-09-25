from __future__ import annotations

import time as _time
from typing import Any

import httpx


class GHLClient:
    def __init__(self, token: str, version: str = "2021-07-28"):
        self.client = httpx.Client(
            base_url="https://services.leadconnectorhq.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Version": version,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        self._custom_fields_cache: dict[str, list[dict[str, Any]]] = {}

    def _get(self, url: str, params: dict[str, Any] | None = None, retries: int = 3) -> httpx.Response:
        """GET con reintentos ante cortes de red/timeout transitorios."""
        last_exc: Exception | None = None
        retryable_status = {401, 429, 500, 502, 503, 504}  # GHL a veces tira 401/5xx falsos bajo carga
        for attempt in range(retries + 1):
            try:
                response = self.client.get(url, params=params)
                response.raise_for_status()
                return response
            except (httpx.TransportError, httpx.RemoteProtocolError) as exc:
                last_exc = exc
                if attempt < retries:
                    _time.sleep(1.5 * (attempt + 1))
                    continue
                raise
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code in retryable_status and attempt < retries:
                    _time.sleep(1.5 * (attempt + 1))
                    continue
                raise
        raise last_exc  # pragma: no cover

    def get_location(self, location_id: str) -> dict[str, Any]:
        response = self.client.get(f"/locations/{location_id}")
        response.raise_for_status()
        return response.json()

    def list_contacts_sample(self, location_id: str, limit: int = 1) -> dict[str, Any]:
        response = self.client.get("/contacts/", params={"locationId": location_id, "limit": limit})
        response.raise_for_status()
        return response.json()

    def list_opportunities_sample(self, location_id: str, limit: int = 1) -> dict[str, Any]:
        response = self.client.get("/opportunities/search", params={"location_id": location_id, "limit": limit})
        response.raise_for_status()
        return response.json()

    def list_contacts_page(
        self,
        location_id: str,
        limit: int = 100,
        start_after: int | None = None,
        start_after_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"locationId": location_id, "limit": limit}
        if start_after is not None:
            params["startAfter"] = start_after
        if start_after_id:
            params["startAfterId"] = start_after_id
        response = self.client.get("/contacts/", params=params)
        response.raise_for_status()
        return response.json()

    def search_contacts_page(
        self,
        location_id: str,
        search_after: list | None = None,
        page_limit: int = 100,
    ) -> dict[str, Any]:
        """POST /contacts/search — paginacion robusta via searchAfter (trae customFields)."""
        body: dict[str, Any] = {"locationId": location_id, "pageLimit": page_limit}
        if search_after:
            body["searchAfter"] = search_after
        last_exc = None
        for attempt in range(4):
            try:
                r = self.client.post("/contacts/search", json=body)
                r.raise_for_status()
                return r.json()
            except (httpx.TransportError, httpx.RemoteProtocolError) as exc:
                last_exc = exc
                import time as _t; _t.sleep(1.5 * (attempt + 1))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    import time as _t; _t.sleep(1.5 * (attempt + 1)); continue
                raise
        raise last_exc  # pragma: no cover

    def get_contact(self, contact_id: str) -> dict[str, Any]:
        response = self.client.get(f"/contacts/{contact_id}")
        response.raise_for_status()
        return response.json()

    def list_custom_fields(self, location_id: str) -> dict[str, Any]:
        response = self.client.get(f"/locations/{location_id}/customFields")
        response.raise_for_status()
        return response.json()

    def list_opportunities_page(
        self,
        location_id: str,
        limit: int = 100,
        start_after: int | None = None,
        start_after_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"location_id": location_id, "limit": limit}
        if start_after is not None:
            params["startAfter"] = start_after
        if start_after_id:
            params["startAfterId"] = start_after_id
        response = self.client.get("/opportunities/search", params=params)
        response.raise_for_status()
        return response.json()

    def list_calendars(self, location_id: str) -> dict[str, Any]:
        response = self.client.get("/calendars/", params={"locationId": location_id})
        response.raise_for_status()
        return response.json()

    def list_calendar_events(
        self,
        location_id: str,
        start_time: str,
        end_time: str,
        calendar_id: str | None = None,
        user_id: str | None = None,
        group_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "locationId": location_id,
            "startTime": start_time,
            "endTime": end_time,
        }
        if calendar_id:
            params["calendarId"] = calendar_id
        if user_id:
            params["userId"] = user_id
        if group_id:
            params["groupId"] = group_id
        response = self.client.get("/calendars/events", params=params)
        response.raise_for_status()
        return response.json()

    def list_pipelines(self, location_id: str) -> dict[str, Any]:
        response = self.client.get("/opportunities/pipelines", params={"locationId": location_id})
        response.raise_for_status()
        return response.json()

    def list_users(self, location_id: str) -> dict[str, Any]:
        response = self.client.get("/users/", params={"locationId": location_id})
        response.raise_for_status()
        return response.json()

    def search_conversations(
        self,
        location_id: str,
        limit: int = 100,
        start_after_date: int | None = None,
        start_after_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"locationId": location_id, "limit": limit}
        if start_after_date is not None:
            params["startAfterDate"] = start_after_date
        if start_after_id:
            params["startAfterId"] = start_after_id
        return self._get("/conversations/search", params=params).json()

    def list_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        last_message_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if last_message_id:
            params["lastMessageId"] = last_message_id
        return self._get(f"/conversations/{conversation_id}/messages", params=params).json()

    def find_contact_by_email(self, location_id: str, email: str) -> dict[str, Any] | None:
        response = self.client.get("/contacts/", params={"locationId": location_id, "query": email, "limit": 5})
        response.raise_for_status()
        contacts = response.json().get("contacts") or []
        email_norm = email.strip().lower()
        for contact in contacts:
            if (contact.get("email") or "").strip().lower() == email_norm:
                return contact
        return None

    def _raw_custom_fields(self, location_id: str) -> list[dict[str, Any]]:
        if location_id not in self._custom_fields_cache:
            payload = self.list_custom_fields(location_id)
            fields = payload.get("customFields", payload) if isinstance(payload, dict) else payload
            self._custom_fields_cache[location_id] = fields
        return self._custom_fields_cache[location_id]

    def custom_field_id_map(self, location_id: str) -> dict[str, str]:
        from snov_ghl_matching import resolve_custom_field_ids
        return resolve_custom_field_ids(self._raw_custom_fields(location_id))

    def custom_field_options(self, location_id: str, field_id: str) -> list[str]:
        for field in self._raw_custom_fields(location_id):
            if field.get("id") == field_id:
                return field.get("picklistOptions") or []
        return []

    def create_contact(self, location_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = {"locationId": location_id, **payload}
        response = self.client.post("/contacts/", json=body)
        response.raise_for_status()
        return response.json()

    def update_contact(self, contact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.put(f"/contacts/{contact_id}", json=payload)
        response.raise_for_status()
        return response.json()

    def update_custom_field(self, contact_id: str, field_id: str, value: Any) -> dict[str, Any]:
        return self.update_contact(contact_id, {"customFields": [{"id": field_id, "value": value}]})

    def create_task(self, contact_id: str, title: str, due_date_iso: str, body: str = "") -> dict[str, Any]:
        payload = {"title": title, "body": body, "dueDate": due_date_iso, "completed": False}
        response = self.client.post(f"/contacts/{contact_id}/tasks", json=payload)
        response.raise_for_status()
        return response.json()

    def free_slots(self, calendar_id: str, start_ms: int, end_ms: int, timezone: str) -> dict[str, Any]:
        response = self.client.get(
            f"/calendars/{calendar_id}/free-slots",
            params={"startDate": start_ms, "endDate": end_ms, "timezone": timezone},
        )
        response.raise_for_status()
        return response.json()

    def create_appointment(self, calendar_id: str, location_id: str, contact_id: str, start_iso: str) -> dict[str, Any]:
        # NUNCA verificado en vivo (crearia una cita real) — ver Task 24 del
        # plan 2026-09-24-snov-replies-to-ghl-plan.md. Forma tomada de la
        # documentacion publica de GHL v2 (POST /calendars/events/appointments),
        # pero no confirmada contra la API real. Probar con cuidado antes de
        # confiar en esto, avisando a Norma primero (crea una cita real en su
        # calendario de trabajo).
        body = {
            "calendarId": calendar_id,
            "locationId": location_id,
            "contactId": contact_id,
            "startTime": start_iso,
        }
        response = self.client.post("/calendars/events/appointments", json=body)
        response.raise_for_status()
        return response.json()
