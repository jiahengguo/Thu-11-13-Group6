"""Local-only B02 workbench; not a production HTTP server or authentication system."""
import argparse
import json
import re
import secrets
import sqlite3
import sys
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore
from urllib.parse import parse_qs, urlsplit
from datetime import datetime, timezone, timedelta

from importlib.util import find_spec
from tripmate.fixtures.b03 import FIXTURE_TIME
from tripmate.fixtures import FixtureRepository
from tripmate.persistence.platform import PlatformStore
from tripmate.operations import OperationsRepository, OperationsService
from tripmate.operations.common import OperationsError, instant
from tripmate.operations.analytics import analyse, experiment
from .settings import Settings, has_model_key
from tripmate.exception_handling import ExceptionRepository
from tripmate.exception_handling.fixtures import demo_runtime, SCENARIOS
from tripmate.agents.exception import CustomerExceptionAgent


class WorkbenchError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def planning_is_available():
    return find_spec("tripmate.planning") is not None


class Workbench:
    def __init__(self, settings, llm_factory=None, *, planning_fixture=False, planning_live_model=False, exception_fixture=False):
        if exception_fixture and (settings.mode != 'FIXTURE' or planning_fixture):
            raise ValueError('Exception demonstration requires FIXTURE mode and its own fixture clock')
        if planning_live_model and not planning_fixture:
            raise ValueError('Live Planning requires explicit planning_fixture integration')
        if planning_fixture and settings.mode != 'FIXTURE':
            raise ValueError('Integrated development Planning requires FIXTURE mode')
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
        self.supplier_db = settings.database.with_name(
            settings.database.stem + '.supplier-demo' + settings.database.suffix)
        self.token = secrets.token_urlsafe(32)
        self.busy = BoundedSemaphore(1)
        self.operations = OperationsService(OperationsRepository(settings.database), self.fixtures) if settings.mode == "FIXTURE" else None
        if self.operations is not None and has_model_key():
            try:
                from tripmate.adapters.campus import CampusLLMService
                self.operations.llm = CampusLLMService(timeout=20)
            except (ImportError, ValueError):
                pass  # An absent/incompatible adapter remains explicitly unconfigured.
        self.ops_sessions = {}
        self.exception_repository = ExceptionRepository(settings.database) if settings.mode == "FIXTURE" else None
        self.integrated_planning = None
        self.integrated_exception = None
        self.planning_live_model = planning_live_model
        if planning_fixture:
            from tripmate.planning.integration import connect_workbench_planning
            self.operations.clock = lambda: FIXTURE_TIME
            self.operations.entitlement.clock = self.operations.clock
            self.operations.dependency_timeout = 60
            if planning_live_model and not has_model_key():
                raise ValueError('Set the course model key locally before enabling live Planning')
            self.integrated_planning = connect_workbench_planning(
                self.operations, self.fixtures, settings.database, live_model=planning_live_model)
        if exception_fixture:
            from tripmate.exception_handling.integration_demo import connect_saved_demo
            self.integrated_exception = connect_saved_demo(self.operations, self.fixtures, settings.database)

    def ops_actor(self, session):
        evidence = self.ops_sessions.get(session)
        if not evidence or instant(evidence["expiresAt"]) <= datetime.now(timezone.utc):
            raise OperationsError("ACCESS_DENIED", "Choose a simulated identity to start a new local session.")
        return evidence["actor"]

    def ops_post(self, action, body, session):
        if self.operations is None:
            raise OperationsError("NOT_IMPLEMENTED", "Operations requires explicit FIXTURE mode.")
        if action == "session":
            if set(body) != {"identityId"} or not isinstance(body["identityId"], str) or not self.operations.profile(body["identityId"]):
                raise OperationsError("ACCESS_DENIED", "Select an available simulated identity.")
            token = secrets.token_urlsafe(32)
            # This is deliberately a fixture-role switcher, never a login claim.
            evidence = {"actor": body["identityId"], "expiresAt": (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()}
            if len(self.ops_sessions) >= 100:
                self.ops_sessions = {k: v for k, v in self.ops_sessions.items() if instant(v["expiresAt"]) > datetime.now(timezone.utc)}
                if len(self.ops_sessions) >= 100:
                    raise OperationsError("TOOL_UNAVAILABLE", "Local session limit reached; restart or wait for expiry.")
            self.ops_sessions[token] = evidence
            return {"session": token, "identity": self.operations.profile(evidence["actor"]), "expiresAt": evidence["expiresAt"], "simulationOnly": True}
        actor = self.ops_actor(session)
        expected = {
            "intake": ({"requestKey", "text"}, {"intents", "campaignId", "channel", "consent"}),
            "confirm": ({"requestKey", "intakeId", "revision", "intents", "confirmed"}, set()),
            "update-intake": ({"requestKey", "intakeId", "revision"}, {"intents", "human"}),
            "dispatch": ({"requestKey", "caseId", "revision"}, set()),
            "deliver": ({"requestKey", "caseId", "revision"}, set()),
            "case-action": ({"requestKey", "caseId", "revision", "action"}, {"reason"}),
            "clarify": ({"requestKey", "caseId", "revision", "intents", "confirmed"}, set()),
            "review": ({"requestKey", "caseId", "revision", "decision", "reason"}, {"editedText"}),
            "premium": ({"requestKey", "action"}, {"memberOfferRuleId"}),
            "adopt": ({"requestKey", "versionId", "expectedBaseline", "accepted"}, set()),
            "start-trip": ({"requestKey", "versionId", "confirmed"}, set()),
            "analysis": ({"requestKey", "data"}, set()),
            "exception-selection": ({"requestKey", "caseId", "revision", "runId", "optionId", "confirmed"}, set()),
        }
        if action not in expected:
            raise OperationsError("INVALID_CONTRACT", "Unsupported Operations action.")
        required, optional = expected[action]
        if not required.issubset(body) or set(body) - required - optional:
            raise OperationsError("INVALID_CONTRACT", "Required fields are missing or unexpected fields were supplied.")
        if "revision" in body and (type(body["revision"]) is not int or body["revision"] < 1):
            raise OperationsError("INVALID_CONTRACT", "A positive case/intake revision is required.")
        for field in {"caseId", "intakeId", "versionId", "action", "decision"} & body.keys():
            if not isinstance(body[field], str) or not 1 <= len(body[field]) <= 100:
                raise OperationsError("INVALID_CONTRACT", "Invalid identifier or action.")
        service, key = self.operations, body["requestKey"]
        if action == "intake":
            return service.intake(actor, key, body["text"], body.get("intents"), body.get("campaignId"), body.get("channel", "LOCAL"), body.get("consent", False))
        if action == "confirm":
            return service.confirm(actor, key, body["intakeId"], body["revision"], body["intents"], body["confirmed"])
        if action == "update-intake":
            if type(body.get("human", False)) is not bool:
                raise OperationsError("INVALID_CONTRACT", "Human request flag must be boolean.")
            return service.update_intake(actor, key, body["intakeId"], body["revision"], body.get("intents"), body.get("human", False))
        if action in {"dispatch", "deliver"}:
            return getattr(service, action)(actor, key, body["caseId"], body["revision"])
        if action == "case-action":
            return service.case_action(actor, key, body["caseId"], body["revision"], body["action"], body.get("reason", "Requester action"))
        if action == "clarify":
            return service.clarify(actor, key, body["caseId"], body["revision"], body["intents"], body["confirmed"])
        if action == "review":
            return service.review_case(actor, key, body["caseId"], body["revision"], body["decision"], body["reason"], body.get("editedText"))
        if action == 'exception-selection':
            return service.select_exception(actor, key, body['caseId'], body['revision'],
                                            body['runId'], body['optionId'], body['confirmed'])
        if action == "premium":
            result = service.premium(actor, key, body["action"], body.get("memberOfferRuleId"))
            if body["action"] == "ROUTE_MAP" and result["decision"]["outcome"] == "ALLOWED":
                result["routePoints"] = [{"label": "Sydney Central", "x": 90, "y": 60},
                                         {"label": "Melbourne Centre", "x": 300, "y": 160}]
                result["mapNotice"] = "B03 Sydney–Melbourne scenario: schematic simulated route points, not live geography."
            return result
        if action == "adopt":
            return service.adopt_plan(actor, key, body["versionId"], body["expectedBaseline"], body["accepted"])
        if action == "start-trip":
            return service.start_trip(actor, key, body['versionId'], body['confirmed'])
        if not service.access.authorise(actor, "ANALYSE", {}):
            raise OperationsError("ACCESS_DENIED", "Only the simulated operator may analyse campaign records.")
        report = analyse(body["data"])
        recommendation = experiment(report)
        return service._command(actor, "analysis", key, body["data"],
                                lambda records: self._save_analysis(records, key, body["data"], report, recommendation))

    @staticmethod
    def _save_analysis(records, key, data, report, recommendation):
        result = {"report": report, "experiment": recommendation, "inputType": "OPERATOR_SUPPLIED_SIMULATION"}
        records.put("analysis_source", key, data)
        records.put("analysis", key, result)
        return result

    def status(self):
        return {"stage": "B02 local workbench", "executionMode": self.settings.mode,
                "database": "CONNECTED" if self.store.healthy() else "UNAVAILABLE",
                "modelConfigured": has_model_key(), "csrfToken": self.token,
                "fixtureTime": FIXTURE_TIME,
                "supplierAssessment": "FIXTURE_AVAILABLE" if planning_is_available() else "B04_NOT_INSTALLED",
                "fixtureCatalog": "SEE_/api/fixtures" if self.settings.mode == "FIXTURE" else "DISABLED",
                "integration": {"operations": "LOCAL_FIXTURE" if self.operations else "STUB", "supplier": "STUB",
                                "exception": "ISOLATED_FIXTURE" if self.exception_repository else "STUB", "planning": "OPERATIONS_B03_FIXTURE" if self.integrated_planning else "ISOLATED_FIXTURE" if planning_is_available() else "NOT_INSTALLED",
                                "reviewer": "EXPLICIT_FIXTURE" if self.integrated_planning else "NOT_INTEGRATED",
                                "planningModel": "CAMPUS_LIVE" if self.planning_live_model else "DETERMINISTIC"}}

    def exception_demo(self, body):
        if self.exception_repository is None:
            raise WorkbenchError("NOT_IMPLEMENTED", "Exception demos require FIXTURE mode.")
        if set(body) - {"kind", "scenario"} or body.get("kind") not in {"DISRUPTION", "COMPLAINT"} or body.get("scenario", "normal") not in SCENARIOS:
            raise ValueError("Select a supported exception demonstration and scenario.")
        case, runtime = demo_runtime(self.exception_repository, body["kind"], body.get("scenario", "normal"))
        result = CustomerExceptionAgent(runtime).handle_case(case)
        saved = self.exception_repository.get(result["runId"])
        if saved is None:
            raise WorkbenchError("PERSISTENCE_FAILED", "Investigation was not saved. Keep the case open and retry or obtain human assistance.")
        return saved

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

    def supplier_demo(self, body):
        if self.settings.mode != 'FIXTURE':
            raise WorkbenchError('NOT_IMPLEMENTED', 'Supplier demonstration requires FIXTURE mode')
        from tripmate.supplier.fixtures import fixture_runtime
        scenario = body.get('scenario', 'coach')
        if not isinstance(scenario, str):
            raise ValueError('Choose a documented supplier scenario')
        case, runtime = fixture_runtime(self.supplier_db, scenario)
        result = runtime.handle_case(case)
        record = runtime.repository.current(runtime.load_input(case['caseId'])['offerId'])
        evidence = self.store.record('SUPPLIER_FIXTURE', result['status'],
                                    {'caseId': case['caseId'], 'runId': result['runId'], 'scenario': scenario,
                                     'executionMode': 'FIXTURE', 'modelExecution': 'FIXTURE_REPLAY'})
        return {'result': result, 'snapshot': record, 'evidence': evidence,
                'notice': 'B04 pricing executed; extraction, access, trace and review are synthetic adapters. No commitment or live AI call.'}

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
        if self.supplier_db.exists():
            with closing(sqlite3.connect(str(self.supplier_db), timeout=10)) as db, db:
                db.execute('BEGIN IMMEDIATE')
                existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                allowed = {'supplier_current', 'supplier_versions', 'supplier_fixture_events', 'supplier_fixture_approvals'}
                for table in sorted(existing & allowed):
                    db.execute('DELETE FROM ' + table)
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


def make_server(settings, port=8765, llm_factory=None, *, planning_fixture=False, planning_live_model=False, exception_fixture=False):
    app = Workbench(settings, llm_factory, planning_fixture=planning_fixture, planning_live_model=planning_live_model, exception_fixture=exception_fixture)
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
                      "/operations": ("operations.html", "text/html; charset=utf-8"),
                      "/operations.js": ("operations.js", "text/javascript; charset=utf-8"),
                      "/exceptions.js": ("exceptions.js", "text/javascript; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/style.css": ("style.css", "text/css; charset=utf-8")}
            try:
                if path in assets:
                    name, mime = assets[path]
                    return self.send(200, (static / name).read_bytes(), mime)
                if path == "/api/status":
                    return self.send(200, app.status())
                if path == "/api/exception-runs":
                    if app.exception_repository is None:
                        raise WorkbenchError("NOT_IMPLEMENTED", "Exception history requires FIXTURE mode.")
                    return self.send(200, {"runs": app.exception_repository.recent()})
                if path == "/api/checks":
                    return self.send(200, {"checks": app.store.recent()})
                if path == "/api/fixtures":
                    return self.send(200, app.fixture_catalog())
                if path.startswith("/api/operations/"):
                    if app.operations is None:
                        raise OperationsError("NOT_IMPLEMENTED", "Operations is disabled outside FIXTURE mode.")
                    if path == "/api/operations/status":
                        return self.send(200, {"identities": app.operations.identities(), "simulationOnly": True,
                                              "modelExtraction": "NOT_INSTALLED" if app.operations.llm is None else "CONFIGURED",
                                              "planning": "NOT_INTEGRATED" if app.operations.planning_repository is None else "INJECTED"})
                    actor = app.ops_actor(self.headers.get("X-Ops-Session", ""))
                    query = parse_qs(urlsplit(self.path).query)
                    if path == '/api/operations/exception' and set(query) == {'caseId'} and len(query['caseId']) == 1:
                        if app.integrated_exception is None:
                            raise OperationsError('NOT_IMPLEMENTED', 'Exception integration is not configured.')
                        return self.send(200, {'investigation': app.integrated_exception.investigation(actor, query['caseId'][0])})
                    if path == "/api/operations/cases" and not query:
                        return self.send(200, {"cases": app.operations.cases(actor)})
                    if path in {"/api/operations/case", "/api/operations/traces", "/api/operations/history"} and set(query) == {"caseId"} and len(query["caseId"]) == 1:
                        case_id = query["caseId"][0]
                        if path.endswith("/history"):
                            return self.send(200, {"history": app.operations.history(actor, case_id)})
                        return self.send(200, app.operations.case_view(actor, case_id) if path.endswith("/case") else {"events": app.operations.traces(actor, case_id)})
                    if path == "/api/operations/plan" and set(query) == {"versionId"} and len(query["versionId"]) == 1:
                        return self.send(200, app.operations.plan_view(actor, query["versionId"][0]))
                return self.send(404, {"error": "NOT_FOUND"})
            except OperationsError as exc:
                return self.send(403 if exc.code == "ACCESS_DENIED" else 422, {"error": exc.code, "message": str(exc)})
            except WorkbenchError as exc:
                return self.send(422, {"error": exc.code, "message": str(exc)})
            except (OSError, sqlite3.Error):
                return self.send(503, {"error": "STORAGE_UNAVAILABLE", "message": "Check database access and available disk space."})

        def do_POST(self):
            if not self.local_request() or not secrets.compare_digest(self.headers.get("X-TripMate-Token", ""), app.token):
                # Discard a bounded body before closing an HTTP/1.0 connection.
                # Unread inbound bytes can otherwise reset the socket on Windows
                # before the caller receives the intended 403 response.
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if 0 < size <= 8192:
                        self.connection.settimeout(1)
                        self.rfile.read(size)
                except (ValueError, OSError):
                    pass
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
                if self.path.startswith("/api/operations/"):
                    return self.send(200, app.ops_post(self.path.removeprefix("/api/operations/"), body, self.headers.get("X-Ops-Session", "")))
                if self.path == "/api/exception-demo":
                    return self.send(200, app.exception_demo(body))
                if self.path == "/api/planning-demo":
                    if set(body) - {"mode", "budget"}:
                        raise ValueError("Unexpected demo fields")
                    return self.send(200, app.planning(body))
                if self.path == '/api/supplier-demo':
                    if set(body) - {'scenario'}:
                        raise ValueError('Unexpected supplier demo fields')
                    return self.send(200, app.supplier_demo(body))
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
            except OperationsError as exc:
                return self.send(403 if exc.code == "ACCESS_DENIED" else 422, {"error": exc.code, "message": str(exc)})
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
    if "--workbench" not in sys.argv[1:]:
        from tripmate.portal.server import main as portal_main
        return portal_main()
    parser = argparse.ArgumentParser(description="TripMate local B02 workbench")
    parser.add_argument("--workbench", action="store_true", help="Explicitly enable the isolated, unauthenticated development workbench")
    parser.add_argument('--planning-fixture', action='store_true', help='Connect actual Operations + B03 database + Planning with an explicit fixture Reviewer')
    parser.add_argument('--planning-live-model', action='store_true', help='Use campus-qwen for integrated Planning; requires --planning-fixture')
    parser.add_argument('--exception-fixture', action='store_true', help='Reopen an explicitly seeded Exception integration demonstration database')
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args()
    try:
        settings = Settings.load(args.env_file)
        server = make_server(settings, args.port, planning_fixture=args.planning_fixture, planning_live_model=args.planning_live_model, exception_fixture=args.exception_fixture)
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, "Startup failed: check mode, database permissions and port availability. " + type(exc).__name__ + "\n")
    print(f"TripMate B02 | {settings.mode} business data | http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if server.app.integrated_planning:
            server.app.integrated_planning.close()


if __name__ == "__main__":
    main()
