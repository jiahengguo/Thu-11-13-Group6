"""Local-only B02 workbench; not a production HTTP server or authentication system."""
import argparse
import json
import re
import secrets
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from importlib.util import find_spec
from tripmate.fixtures.b03 import FIXTURE_TIME
from tripmate.fixtures import FixtureRepository
from tripmate.persistence.platform import PlatformStore
from .settings import Settings, has_model_key


class WorkbenchError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def planning_is_available():
    return find_spec("tripmate.planning") is not None


class Workbench:
    def __init__(self, settings, llm_factory=None):
        self.settings = settings
        self.store = PlatformStore(settings.database)
        self.fixtures = FixtureRepository(settings.database)
        if settings.mode == "FIXTURE":
            self.fixtures.ensure_seeded()
        self.llm_factory = llm_factory
        # Planning's isolated fixture demonstration is kept in a different
        # database, even when Moore's module is eventually merged.
        self.planning_db = settings.database.with_name(
            settings.database.stem + ".planning-demo" + settings.database.suffix)
        if self.planning_db.resolve() == settings.database.resolve():
            raise ValueError("Planning demonstration database must be separate")
        self.token = secrets.token_urlsafe(32)
        self.busy = BoundedSemaphore(1)

    def status(self):
        return {"stage": "B02 local workbench", "executionMode": self.settings.mode,
                "database": "CONNECTED" if self.store.healthy() else "UNAVAILABLE",
                "modelConfigured": has_model_key(), "csrfToken": self.token,
                "fixtureTime": FIXTURE_TIME,
                "fixtureCatalog": "SEE_/api/fixtures" if self.settings.mode == "FIXTURE" else "DISABLED",
                "integration": {"operations": "STUB", "supplier": "STUB",
                                "exception": "STUB", "planning": "ISOLATED_FIXTURE" if planning_is_available() else "NOT_INSTALLED"}}

    def planning(self, body):
        if self.settings.mode != "FIXTURE":
            raise WorkbenchError("NOT_IMPLEMENTED", "Enable FIXTURE mode for the isolated planning demonstration")
        if not planning_is_available():
            raise WorkbenchError("PLANNING_NOT_INSTALLED", "Travel Planning is a separate branch. Merge it before running the optional demo.")
        from tripmate.agents.planning import TravelPlanningAgent
        from tripmate.planning.fixtures import fixture_runtime
        mode, budget = body.get("mode", "VALUE"), body.get("budget", "900.00")
        if mode not in {"VALUE", "COMFORT", "BUDGET"}:
            raise ValueError("Choose VALUE, COMFORT or BUDGET")
        if not isinstance(budget, str) or not re.fullmatch(r"\d{1,7}\.\d{2}", budget):
            raise ValueError("Budget must be an AUD decimal string such as 450.00")
        case, _, runtime = fixture_runtime(mode, budget, str(self.planning_db))
        try:
            result = TravelPlanningAgent(runtime).handle_case(case)
            versions = [runtime.repository.get_version(s["subjectId"])["version"]
                        for s in result["subjects"] if s["subjectType"] == "ItineraryVersion"]
        finally:
            runtime.repository.close()
        evidence = self.store.record("PLANNING_FIXTURE", result["status"],
                                     {"runId": result["runId"], "caseId": case["caseId"],
                                      "executionMode": "FIXTURE", "modelExecution": "NONE",
                                      "mode": mode, "budget": budget})
        return {"result": result, "versions": versions, "evidence": evidence,
                "notice": "Isolated simulated data and permissions; no booking or customer acceptance."}

    def fixture_catalog(self):
        if self.settings.mode != "FIXTURE":
            raise WorkbenchError("NOT_IMPLEMENTED", "Fixture catalog requires FIXTURE mode")
        return self.fixtures.summary()

    def reset_fixtures(self):
        if self.settings.mode != "FIXTURE":
            raise WorkbenchError("NOT_IMPLEMENTED", "Reset is disabled outside FIXTURE mode")
        # B03 may only touch fixture_* in the shared workbench database.
        # The optional Planning demonstration lives in a different database.
        result = self.fixtures.reset()
        if self.planning_db.exists():
            with closing(sqlite3.connect(str(self.planning_db), timeout=10)) as db, db:
                db.execute("BEGIN IMMEDIATE")
                allowed = {"planning_traces", "planning_acceptances", "planning_selected", "planning_runs", "planning_versions"}
                existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for table in sorted(existing & allowed):
                    db.execute("DELETE FROM " + table)
        return result

    def smoke(self):
        details = {"businessData": "SYNTHETIC_SMOKE", "modelExecution": "NOT_STARTED"}
        if not has_model_key():
            details.update(code="MODEL_NOT_CONFIGURED", message="Set ELEC5620_API_KEY in local .env; never enter it in this page.")
            return self.store.record("LLM_SMOKE", "BLOCKED", details)
        try:
            llm_factory = self.llm_factory
            if llm_factory is None:
                try:
                    from tripmate.adapters.campus import CampusLLMService
                except ImportError:
                    details.update(code="MODEL_ADAPTER_NOT_INSTALLED", message="Campus model adapter is on the separate Travel Planning branch; merge it to enable the smoke check.")
                    return self.store.record("LLM_SMOKE", "BLOCKED", details)
                llm_factory = CampusLLMService
            client = llm_factory(timeout=20)
            details["modelExecution"] = "LIVE_ATTEMPT"
            result = client.extract("Supplier demonstration: city Sydney; currency AUD.", {
                "type": "object", "properties": {"city": {"const": "Sydney"}, "currency": {"const": "AUD"}},
                "required": ["city", "currency"], "additionalProperties": False})
            if result != {"city": "Sydney", "currency": "AUD"}:
                raise WorkbenchError("LLM_INVALID_OUTPUT", "Smoke response did not match the expected synthetic facts")
            details.update(modelExecution="LIVE", message="Synthetic structured extraction succeeded.")
            outcome = "SUCCESS"
        except Exception as exc:
            # Do not persist exception text: third-party adapters may echo secrets.
            details.update(code=getattr(exc, "code", "MODEL_CHECK_FAILED"),
                           message="Model check failed; verify configuration, adapter and campus/VPN connectivity.")
            outcome = "BLOCKED"
        return self.store.record("LLM_SMOKE", outcome, details)


def make_server(settings, port=8765, llm_factory=None):
    app = Workbench(settings, llm_factory)
    static = Path(__file__).with_name("static")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Do not log submitted text, query strings or headers.

        def send(self, status, payload, content_type="application/json; charset=utf-8"):
            data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(data)

        def local_request(self):
            hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            return host in hosts and (origin is None or origin == "http://" + host)

        def do_GET(self):
            if not self.local_request():
                return self.send(403, {"error": "LOCAL_ONLY"})
            path = urlsplit(self.path).path
            assets = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/style.css": ("style.css", "text/css; charset=utf-8")}
            try:
                if path in assets:
                    name, mime = assets[path]
                    return self.send(200, (static / name).read_bytes(), mime)
                if path == "/api/status":
                    return self.send(200, app.status())
                if path == "/api/checks":
                    return self.send(200, {"checks": app.store.recent()})
                if path == "/api/fixtures":
                    return self.send(200, app.fixture_catalog())
                return self.send(404, {"error": "NOT_FOUND"})
            except WorkbenchError as exc:
                return self.send(422, {"error": exc.code, "message": str(exc)})
            except (OSError, sqlite3.Error):
                return self.send(503, {"error": "STORAGE_UNAVAILABLE", "message": "Check database access and available disk space."})

        def do_POST(self):
            if not self.local_request() or not secrets.compare_digest(self.headers.get("X-TripMate-Token", ""), app.token):
                return self.send(403, {"error": "LOCAL_TOKEN_REQUIRED"})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.send(415, {"error": "JSON_REQUIRED"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 8192:
                    return self.send(413, {"error": "BODY_SIZE_INVALID"})
                self.connection.settimeout(10)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object")
            except (ValueError, OSError):
                return self.send(400, {"error": "INVALID_JSON"})
            if not app.busy.acquire(blocking=False):
                return self.send(409, {"error": "CHECK_RUNNING", "message": "Wait for the current check to finish."})
            try:
                if self.path == "/api/planning-demo":
                    if set(body) - {"mode", "budget"}:
                        raise ValueError("Unexpected demo fields")
                    return self.send(200, app.planning(body))
                if self.path == "/api/fixtures/reset":
                    if body:
                        raise ValueError("Fixture reset accepts no user content")
                    return self.send(200, app.reset_fixtures())
                if self.path == "/api/model-smoke":
                    if body:
                        raise ValueError("Smoke check accepts no user content")
                    return self.send(200, app.smoke())
                return self.send(404, {"error": "NOT_FOUND"})
            except WorkbenchError as exc:
                return self.send(422, {"error": exc.code, "message": str(exc)})
            except ValueError as exc:
                if hasattr(exc, "code"):
                    return self.send(422, {"error": exc.code, "message": str(exc)})
                return self.send(400, {"error": "INVALID_INPUT", "message": str(exc)})
            except (sqlite3.Error, OSError):
                return self.send(503, {"error": "STORAGE_UNAVAILABLE", "message": "Save failed; no success is claimed. Check database access."})
            except Exception:
                return self.send(500, {"error": "CHECK_FAILED", "message": "The check failed; no completion is claimed."})
            finally:
                app.busy.release()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.app = app
    return server


def main():
    parser = argparse.ArgumentParser(description="TripMate local B02 workbench")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args()
    try:
        settings = Settings.load(args.env_file)
        server = make_server(settings, args.port)
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, "Startup failed: check mode, database permissions and port availability. " + type(exc).__name__ + "\n")
    print(f"TripMate B02 | {settings.mode} business data | http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
