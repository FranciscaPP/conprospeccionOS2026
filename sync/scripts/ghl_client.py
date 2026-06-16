from __future__ import annotations

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

    def get_contact(self, contact_id: str) -> dict[str, Any]:
        response = self.client.get(f"/contacts/{contact_id}")
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
        response = self.client.get("/conversations/search", params=params)
        response.raise_for_status()
        return response.json()

    def list_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        last_message_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if last_message_id:
            params["lastMessageId"] = last_message_id
        response = self.client.get(f"/conversations/{conversation_id}/messages", params=params)
        response.raise_for_status()
        return response.json()
