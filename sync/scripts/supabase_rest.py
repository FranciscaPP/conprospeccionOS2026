from __future__ import annotations

from typing import Any

import httpx


class SupabaseRestClient:
    def __init__(self, url: str, key: str):
        base_url = url.rstrip("/").removesuffix("/rest/v1")
        self.client = httpx.Client(
            base_url=f"{base_url}/rest/v1",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

    def upsert(self, table: str, rows: list[dict[str, Any]], conflict: str) -> list[dict[str, Any]]:
        response = self.client.post(
            f"/{table}",
            params={"on_conflict": conflict},
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
            json=rows,
        )
        response.raise_for_status()
        return response.json()

    def select(self, table: str, columns: str, **params: str) -> list[dict[str, Any]]:
        query = {"select": columns, **params}
        response = self.client.get(f"/{table}", params=query)
        response.raise_for_status()
        return response.json()

    def select_all(self, table: str, columns: str, page_size: int = 1000, **params: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            query = {"select": columns, "limit": str(page_size), "offset": str(offset), **params}
            response = self.client.get(f"/{table}", params=query)
            response.raise_for_status()
            page = response.json()
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return rows

    def insert(self, table: str, row: dict[str, Any]) -> None:
        response = self.client.post(f"/{table}", headers={"Prefer": "return=minimal"}, json=row)
        response.raise_for_status()

    def insert_returning(
        self,
        table: str,
        row: dict[str, Any],
        *,
        conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> list[dict[str, Any]]:
        params = {"on_conflict": conflict} if conflict else None
        resolution = "ignore-duplicates" if ignore_duplicates else "merge-duplicates"
        response = self.client.post(
            f"/{table}",
            params=params,
            headers={"Prefer": f"resolution={resolution},return=representation"},
            json=row,
        )
        response.raise_for_status()
        return response.json()

    def update(self, table: str, values: dict[str, Any], **params: str) -> list[dict[str, Any]]:
        response = self.client.patch(
            f"/{table}",
            params=params,
            headers={"Prefer": "return=representation"},
            json=values,
        )
        response.raise_for_status()
        return response.json()

    def rpc(self, function: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        response = self.client.post(
            f"/rpc/{function}",
            headers={"Prefer": "return=representation"},
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, list) else [result]
