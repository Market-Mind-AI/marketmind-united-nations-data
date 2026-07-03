import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import UNDataClientError, UNDataTimeoutError
from app.core.logging import logger


class UNDataClient:
    def __init__(self) -> None:
        self._base_url = settings.undata_api_base_url
        self._timeout = settings.default_timeout
        self._retries = settings.default_retries
        self._backoff = settings.default_backoff

    def get_indicators(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/indicators")

    def get_indicator(self, indicator_id: int) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/indicators/{indicator_id}")

    def get_locations(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/locations/tvAlphabetical")

    def get_location(self, location_id: int) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/locations/{location_id}")

    def get_sources(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/sources")

    def get_time_dimensions(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/dimensions/times?timeType=single")

    def get_data(
        self,
        indicator_id: int,
        location_id: int,
        year: int,
        variant_id: int = 4,
        age_id: int = 188,
        sex_id: int = 3,
        category_id: int = 0,
    ) -> list[dict[str, Any]]:
        url = (
            f"{self._base_url}/data/indicators/{indicator_id}"
            f"/locations/{location_id}/years/{year}"
            f"/vars/{variant_id}/ages/{age_id}/sexes/{sex_id}/cats/{category_id}"
        )
        return self._get(url)

    def get_data_range(
        self,
        indicator_id: int,
        location_id: int,
        start_year: int,
        end_year: int,
        variant_id: int = 4,
        age_id: int = 188,
        sex_id: int = 3,
        category_id: int = 0,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        all_data: list[dict[str, Any]] = []
        all_raw: list[dict[str, Any]] = []
        for year in range(start_year, end_year + 1):
            rows = self.get_data(indicator_id, location_id, year, variant_id, age_id, sex_id, category_id)
            all_raw.extend(rows)
            for row in rows:
                if row.get("value") is not None:
                    all_data.append(row)
        return all_data, all_raw

    def _get(self, url: str) -> list[dict[str, Any]]:
        last_error: Exception | None = None

        for attempt in range(1, self._retries + 1):
            try:
                logger.info(f"undata_client | GET {url} | attempt={attempt}/{self._retries}")
                with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "data" in data:
                        return data["data"]
                    return [data] if data else []
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"undata_client | timeout | attempt={attempt}/{self._retries} | url={url}")
                if attempt < self._retries:
                    time.sleep(self._backoff * attempt)
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(f"undata_client | http_error={e.response.status_code} | attempt={attempt}/{self._retries}")
                if attempt < self._retries:
                    time.sleep(self._backoff * attempt)
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(f"undata_client | error={e} | attempt={attempt}/{self._retries}")
                if attempt < self._retries:
                    time.sleep(self._backoff * attempt)

        if isinstance(last_error, httpx.TimeoutException):
            raise UNDataTimeoutError(f"Timeout after {self._retries} retries: {last_error}") from last_error
        raise UNDataClientError(f"Failed after {self._retries} retries: {last_error}") from last_error
