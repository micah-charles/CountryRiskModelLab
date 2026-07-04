from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import perf_counter
from typing import DefaultDict


_lock = Lock()
_started_at = perf_counter()
_requests_total: DefaultDict[tuple[str, str, int], int] = defaultdict(int)
_request_duration_seconds_sum: DefaultDict[tuple[str, str], float] = defaultdict(float)
_request_duration_seconds_count: DefaultDict[tuple[str, str], int] = defaultdict(int)


def record_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    key = (method, path, status_code)
    duration_key = (method, path)
    with _lock:
        _requests_total[key] += 1
        _request_duration_seconds_sum[duration_key] += duration_seconds
        _request_duration_seconds_count[duration_key] += 1


def metrics_text() -> str:
    lines = [
        "# HELP country_risk_app_uptime_seconds Process uptime in seconds.",
        "# TYPE country_risk_app_uptime_seconds gauge",
        f"country_risk_app_uptime_seconds {perf_counter() - _started_at:.6f}",
        "# HELP country_risk_http_requests_total Total HTTP requests by method, path, and status.",
        "# TYPE country_risk_http_requests_total counter",
    ]
    with _lock:
        for (method, path, status), value in sorted(_requests_total.items()):
            lines.append(
                f'country_risk_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}'
            )
        lines.extend(
            [
                "# HELP country_risk_http_request_duration_seconds_sum Sum of HTTP request durations.",
                "# TYPE country_risk_http_request_duration_seconds_sum counter",
            ]
        )
        for (method, path), value in sorted(_request_duration_seconds_sum.items()):
            lines.append(
                f'country_risk_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {value:.6f}'
            )
        lines.extend(
            [
                "# HELP country_risk_http_request_duration_seconds_count Count of HTTP request durations.",
                "# TYPE country_risk_http_request_duration_seconds_count counter",
            ]
        )
        for (method, path), value in sorted(_request_duration_seconds_count.items()):
            lines.append(
                f'country_risk_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {value}'
            )
    return "\n".join(lines) + "\n"

