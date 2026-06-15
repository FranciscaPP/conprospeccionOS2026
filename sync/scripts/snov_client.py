from __future__ import annotations

from datetime import date
from typing import Any

import httpx


class SnovClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client = httpx.Client(base_url="https://api.snov.io", timeout=60)
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: str | None = None

    def access_token(self) -> str:
        if self._access_token:
            return self._access_token
        response = self.client.post(
            "/v1/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"Snov no devolvio access_token: {payload}")
        self._access_token = token
        return token

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params = {"access_token": self.access_token()}
        if extra:
            params.update(extra)
        return params

    def campaigns(self) -> list[dict[str, Any]]:
        response = self.client.get("/v1/get-user-campaigns", params=self._params())
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("data", [])

    def prospects_in_list(self, list_id: str, page: int = 1, per_page: int = 5000) -> dict[str, Any]:
        response = self.client.post(
            "/v1/prospect-list",
            data=self._params({"listId": list_id, "page": page, "perPage": per_page}),
        )
        response.raise_for_status()
        return response.json()

    def prospect_by_id(self, prospect_id: str) -> dict[str, Any]:
        response = self.client.post("/v1/get-prospect-by-id", data=self._params({"id": prospect_id}))
        response.raise_for_status()
        return response.json()

    def prospect_by_email(self, email: str) -> dict[str, Any]:
        response = self.client.post("/v1/get-prospect-by-email", data=self._params({"email": email}))
        response.raise_for_status()
        return response.json()

    def campaign_analytics(
        self,
        campaign_ids: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        campaign_owner: list[str] | None = None,
    ) -> Any:
        params: dict[str, Any] = {}
        if campaign_ids:
            params["campaign_id"] = ",".join(campaign_ids)
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if campaign_owner:
            params["campaign_owner"] = ",".join(campaign_owner)
        response = self.client.get("/v2/statistics/campaign-analytics", params=self._params(params))
        response.raise_for_status()
        return response.json()

    def campaign_progress(self, campaign_id: str) -> dict[str, Any]:
        response = self.client.get(f"/v2/campaigns/{campaign_id}/progress", params=self._params())
        response.raise_for_status()
        return response.json()

    def replies(self, campaign_id: str, offset: int = 0) -> list[dict[str, Any]]:
        response = self.client.get("/v1/get-emails-replies", params=self._params({"campaignId": campaign_id, "offset": offset}))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("data", [])

    def opens(self, campaign_id: str, offset: int = 0) -> list[dict[str, Any]]:
        response = self.client.get("/v1/get-emails-opened", params=self._params({"campaignId": campaign_id, "offset": offset}))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("data", [])

    def clicks(self, campaign_id: str, offset: int = 0) -> list[dict[str, Any]]:
        response = self.client.get("/v1/get-emails-clicked", params=self._params({"campaignId": campaign_id, "offset": offset}))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("data", [])

    def sent(self, campaign_id: str, offset: int = 0) -> list[dict[str, Any]]:
        response = self.client.get("/v1/emails-sent", params=self._params({"campaignId": campaign_id, "offset": offset}))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("data", [])

    def finished(self, campaign_id: str, offset: int = 0) -> list[dict[str, Any]]:
        response = self.client.get("/v1/prospect-finished", params=self._params({"campaignId": campaign_id, "offset": offset}))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("data", [])
