import time
import httpx

from app.core.config import settings
from app.domain.schemas import ProbeResult


class HttpProbeClient:
    def __init__(self, timeout_seconds: int | None = None):
        self.timeout_seconds = timeout_seconds or settings.status_timeout_seconds

    def probe(self, url: str) -> ProbeResult:
        start = time.perf_counter()

        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = client.get(url)

            elapsed_ms = int((time.perf_counter() - start) * 1000)

            parsed_json = None
            response_text = None

            try:
                parsed_json = response.json()
            except Exception:
                response_text = response.text[:1000] if response.text else None

            return ProbeResult(
                ok=200 <= response.status_code < 300,
                latency_ms=elapsed_ms,
                http_status=response.status_code,
                error=None,
                json_body=parsed_json if isinstance(parsed_json, dict) else None,
                text_body=response_text,
            )

        except httpx.TimeoutException:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return ProbeResult(
                ok=False,
                latency_ms=elapsed_ms,
                http_status=None,
                error="Request timed out.",
                json_body=None,
                text_body=None,
            )
        except httpx.RequestError as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return ProbeResult(
                ok=False,
                latency_ms=elapsed_ms,
                http_status=None,
                error=f"Request error: {exc}",
                json_body=None,
                text_body=None,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return ProbeResult(
                ok=False,
                latency_ms=elapsed_ms,
                http_status=None,
                error=f"Unexpected error: {exc}",
                json_body=None,
                text_body=None,
            )