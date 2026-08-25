"""Cliente HTTP síncrono hacia la API del proyecto.

A diferencia de :class:`ApiReporter` (que reporta en background), este
cliente se usa para consultas puntuales y de arranque:
- recuperar transacciones OPEN (reconciliación al reiniciar el bot)
- cancelar transacciones huérfanas
"""
from __future__ import annotations

import logging

import requests


class ApiClientError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, api_url: str, logger: logging.Logger) -> None:
        self._api_url = api_url
        self._log = logger.getChild("api_client")

    def _request(self, method: str, path: str, **kwargs) -> dict | None:
        url = f"{self._api_url}{path}"
        try:
            resp = requests.request(method, url, timeout=5, **kwargs)
        except requests.RequestException as exc:
            raise ApiClientError(f"error de red: {exc}") from exc
        if resp.status_code >= 300:
            raise ApiClientError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def get_open_transactions(self, market_type: str | None = None) -> list[dict]:
        """Transacciones OPEN (ciclos sin cerrar) registradas en la API.

        ``market_type`` permite filtrar solo spot ("SPOT") o solo futuros
        ("FUTURES") para no mezclar posiciones al reconciliar.
        """
        params = {"status": "OPEN", "limit": 50}
        if market_type:
            params["market_type"] = market_type
        data = self._request("GET", "/api/transactions", params=params)
        return data or []

    def cancel_transaction(self, transaction_id: int) -> None:
        """Marca una transacción como CANCELED (posición huérfana)."""
        self._request("POST", f"/api/transactions/{transaction_id}/cancel")
        self._log.info("Transacción %s marcada como CANCELED.", transaction_id)
