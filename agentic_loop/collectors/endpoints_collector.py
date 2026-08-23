import os
import re

import requests


# Matches Flask route decorators like @app.get("/health") and @ai_mode_bp.post("/ask").
ROUTE_PATTERN = re.compile(r"@\w+\.(get|post|put|delete)\(\"([^\"]+)\"\)")
REQUEST_TIMEOUT = 3  # seconds


def _probe(base_url: str, method: str, path: str) -> str:
    url = f"{base_url}{path}"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        elapsed_ms = int(response.elapsed.total_seconds() * 1000)
        return f"{method.upper()} {path} returned {response.status_code} in {elapsed_ms}ms"
    except requests.exceptions.ConnectionError:
        return f"{method.upper()} {path} [CONNECTION REFUSED - service not running]"
    except requests.exceptions.Timeout:
        return f"{method.upper()} {path} [TIMEOUT]"
    except Exception as exc:  # noqa: BLE001
        return f"{method.upper()} {path} [ERROR: {type(exc).__name__}]"


def collect(app_dir, repo_root) -> tuple[bool, str]:
    """Collect live shared-api endpoint evidence via real HTTP requests.

    Routes are discovered from source, then only side-effect-free GET routes
    without path parameters are probed so validation cannot mutate seed data.
    """
    base_url = os.getenv("SHARED_API_URL", "http://localhost:16002")

    route_files = [
        app_dir / "shared" / "backend" / "app.py",
        app_dir / "ai-services" / "ai-mode" / "routes.py",
    ]

    missing = [str(path.relative_to(app_dir)) for path in route_files if not path.exists()]
    if missing:
        return False, "Missing shared-api route files: " + ", ".join(missing)

    routes: list[tuple[str, str]] = []
    for route_file in route_files:
        content = route_file.read_text(encoding="utf-8")
        for method, route in ROUTE_PATTERN.findall(content):
            routes.append((method, route))

    if not routes:
        return False, "No Flask routes found in shared-api route files."

    probes: list[str] = []
    connection_failures = 0
    for method, route in sorted(set(routes)):
        if method == "get" and "<" not in route:
            result = _probe(base_url, method, route)
            probes.append(result)
            if "CONNECTION REFUSED" in result:
                connection_failures += 1

    total_routes = len(set(routes))
    if probes and connection_failures == len(probes):
        return False, (
            "Shared API not running. Start the stack with docker-compose up --build, "
            "then rerun the loop."
        )

    return True, (
        f"Live endpoint evidence: discovered {total_routes} shared-api routes; "
        f"probed {len(probes)} read-only GET routes: " + "; ".join(probes) + "."
    )
