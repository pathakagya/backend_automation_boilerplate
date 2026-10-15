#!/usr/bin/env python3
"""Parse allure-results and render an HTML email body for CI notification.

Reads raw allure-results/*-result.json files (no allure CLI needed).
Falls back to junit XML if allure results are absent.
Writes email_body.html and sets EMAIL_STATUS in $GITHUB_ENV.
"""

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

RESULTS_DIR = Path(os.getenv("ALLURE_RESULTS_DIR", "allure-results"))
JUNIT_PATH = Path(os.getenv("JUNIT_PATH", "junit-smoke.xml"))
OUTPUT_HTML = Path("email_body.html")
SCRIPT_DIR = Path(__file__).parent

GITHUB_RUN_NUMBER = os.getenv("GITHUB_RUN_NUMBER", "?")
GITHUB_REF_NAME = os.getenv("GITHUB_REF_NAME", "unknown")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")
GITHUB_SERVER_URL = os.getenv("GITHUB_SERVER_URL", "https://github.com")
GITHUB_RUN_ID = os.getenv("GITHUB_RUN_ID", "")
# Empty when GitHub Pages isn't enabled or the deploy failed; the email then omits the link.
ALLURE_REPORT_URL = os.getenv("ALLURE_REPORT_URL", "").strip()


def _repo_name() -> str:
    parts = GITHUB_REPOSITORY.split("/", 1)
    return parts[1] if len(parts) == 2 else GITHUB_REPOSITORY


def _run_url() -> str:
    return f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}"


def _format_duration(ms: float) -> str:
    s = ms / 1000
    if s < 60:
        return f"{s:.1f}s"
    m, sec = divmod(s, 60)
    return f"{int(m)}m {int(sec)}s"


def _parse_allure(results_dir: Path) -> dict | None:
    result_files = list(results_dir.glob("*-result.json"))
    if not result_files:
        return None

    stats = {"tests": 0, "passes": 0, "failures": 0, "broken": 0, "skipped": 0, "duration": 0}
    suites_map: dict[str, dict] = {}

    for f in result_files:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        raw = data.get("status", "unknown").lower()
        status = "skipped" if raw == "unknown" else raw
        duration = data.get("time", {}).get("duration", 0) or 0

        stats["tests"] += 1
        stats["duration"] += duration
        if status == "passed":
            stats["passes"] += 1
        elif status == "failed":
            stats["failures"] += 1
        elif status == "broken":
            stats["broken"] += 1
        else:
            stats["skipped"] += 1

        labels = {
            lbl["name"]: lbl["value"]
            for lbl in data.get("labels", [])
            if "name" in lbl and "value" in lbl
        }
        suite_name = labels.get("suite") or labels.get("testClass") or "Tests"
        parent_suite = labels.get("parentSuite", "")

        if suite_name not in suites_map:
            suites_map[suite_name] = {
                "title": suite_name,
                "parent_suite": parent_suite,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "broken": 0,
                "skipped": 0,
                "duration": 0,
                "tests": [],
            }

        err = None
        if status in ("failed", "broken", "skipped"):
            sd = data.get("statusDetails", {})
            msg = (sd.get("message") or "").strip()
            err = {"message": msg[:300], "trace": (sd.get("trace") or "")[:500]}

        s = suites_map[suite_name]
        s["total"] += 1
        s["duration"] += duration
        s[status if status in ("passed", "failed", "broken", "skipped") else "skipped"] += 1
        s["tests"].append(
            {"title": data.get("name", f.stem), "state": status, "duration": duration, "err": err}
        )

    return {"stats": stats, "suites": list(suites_map.values())}


def _parse_junit(junit_path: Path) -> dict | None:
    if not junit_path.exists():
        return None
    try:
        root = ET.parse(junit_path).getroot()
        ts = root if root.tag == "testsuite" else root.find("testsuite")
        if ts is None:
            return None
        a = ts.attrib
        total = int(a.get("tests", 0))
        failures = int(a.get("failures", 0)) + int(a.get("errors", 0))
        skipped = int(a.get("skipped", 0))
        duration_ms = float(a.get("time", 0)) * 1000
        return {
            "stats": {
                "tests": total,
                "passes": max(0, total - failures - skipped),
                "failures": failures,
                "broken": 0,
                "skipped": skipped,
                "duration": duration_ms,
            },
            "suites": [],
        }
    except Exception as e:
        print(f"JUnit parse error: {e}", flush=True)
        return None


def main() -> None:
    results = _parse_allure(RESULTS_DIR) or _parse_junit(JUNIT_PATH)

    if results is None:
        print("No test results found — writing minimal fallback email.", flush=True)
        results = {
            "stats": {"tests": 0, "passes": 0, "failures": 0, "broken": 0, "skipped": 0, "duration": 0},
            "suites": [],
        }

    stats = results["stats"]
    suites = results["suites"]

    if stats["tests"] == 0:
        overall = "NO RESULTS"
    elif stats["failures"] == 0 and stats["broken"] == 0:
        overall = "PASSED"
    else:
        overall = "FAILED"
    stats["duration_fmt"] = _format_duration(stats["duration"])

    failed_tests = [
        t for suite in suites for t in suite.get("tests", []) if t["state"] in ("failed", "broken")
    ]

    env = Environment(loader=FileSystemLoader(str(SCRIPT_DIR)), autoescape=True)
    template = env.get_template("email_template.html")
    html = template.render(
        status=overall,
        repo=_repo_name(),
        branch=GITHUB_REF_NAME,
        run_number=GITHUB_RUN_NUMBER,
        stats=stats,
        suites=suites,
        failed_tests=failed_tests,
        allure_url=ALLURE_REPORT_URL,
        run_url=_run_url(),
    )

    OUTPUT_HTML.write_text(html)
    print(f"Wrote {OUTPUT_HTML} ({len(html)} bytes)  status={overall}", flush=True)

    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a") as fh:
            fh.write(f"EMAIL_STATUS={overall}\n")
    else:
        print(f"EMAIL_STATUS={overall}", flush=True)


if __name__ == "__main__":
    main()
