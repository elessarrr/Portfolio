import json
import subprocess
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_S = 60


def _browse_bin() -> str:
    candidate = ROOT / ".claude" / "gstack" / "browse" / "dist" / "browse"
    if candidate.exists():
        return str(candidate)
    home_candidate = Path.home() / ".claude" / "skills" / "gstack" / "browse" / "dist" / "browse"
    return str(home_candidate)


WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _fix_mojibake(s: str) -> str:
    # Heuristic: if output looks like UTF-8 decoded as latin-1, fix it.
    if "Ã" in s or "Â" in s or "ï»¿" in s:
        try:
            return s.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            return s
    return s


def _norm(s: str | None) -> str | None:
    if s is None:
        return None
    s = _fix_mojibake(s)
    s = unicodedata.normalize("NFC", s)
    s = " ".join(s.replace("\u00a0", " ").split())
    return s.strip()


def _parse_asn_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = _norm(raw) or ""
    lower = raw.lower()
    for wd in WEEKDAYS:
        if lower.startswith(wd + " "):
            raw = raw[len(wd) + 1 :].strip()
            break
    try:
        dt = datetime.strptime(raw, "%d %B %Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def _extract_fields(page_text: str) -> tuple[str | None, str | None, str | None]:
    """
    Returns (asn_date_iso, asn_operator, detail_if_failed)
    """
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    asn_date_raw = None
    asn_op_raw = None

    # ASN pages can contain other "Date:" strings (e.g., revision history).
    # We want the first metadata block, so capture the first Date/Owner we see in order.
    saw_date = False
    for ln in lines:
        if asn_date_raw is None and ln.startswith("Date:"):
            asn_date_raw = ln[len("Date:") :].strip()
            saw_date = True
            continue

        if saw_date and asn_op_raw is None and (ln.startswith("Owner/operator:") or ln.startswith("Operator:")):
            if ln.startswith("Owner/operator:"):
                asn_op_raw = ln[len("Owner/operator:") :].strip()
            else:
                asn_op_raw = ln[len("Operator:") :].strip()
            break

    asn_date = _parse_asn_date(asn_date_raw)
    # Defensive truncation in case fields get concatenated on one line.
    if asn_op_raw:
        for stopper in ("Registration:", "MSN:", "Fatalities:", "Aircraft damage:", "Location:"):
            if stopper in asn_op_raw:
                asn_op_raw = asn_op_raw.split(stopper, 1)[0].strip()
    asn_op = _norm(asn_op_raw)

    if asn_date is None or asn_op is None:
        return asn_date, asn_op, f"parse_failed dateRaw={asn_date_raw!r} ownerRaw={asn_op_raw!r}"
    return asn_date, asn_op, None


def _browse_text(url: str, *, retry: bool) -> str:
    b = _browse_bin()
    commands = [
        ["goto", url],
        ["wait", "--load"],
        ["wait", "--networkidle"],
        ["text"],
    ]
    proc = subprocess.run(
        [b, "chain"],
        input=json.dumps(commands),
        text=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT_S,
    )
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    if proc.returncode == 0:
        return out

    # One retry with a lighter command set (sometimes networkidle can be flaky)
    if retry:
        commands2 = [
            ["goto", url],
            ["wait", "--load"],
            ["text"],
        ]
        proc2 = subprocess.run(
            [b, "chain"],
            input=json.dumps(commands2),
            text=True,
            capture_output=True,
            timeout=DEFAULT_TIMEOUT_S,
        )
        out2 = (proc2.stdout or "") + ("\n" + proc2.stderr if proc2.stderr else "")
        if proc2.returncode == 0:
            return out2
        raise RuntimeError(f"browse_failed rc={proc2.returncode}\n{out2[:2000]}")

    raise RuntimeError(f"browse_failed rc={proc.returncode}\n{out[:2000]}")


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/verify_asn_checkset.py <checkset.json> [out.json] [resume_results.json]",
            file=sys.stderr,
        )
        return 2

    checkset_path = Path(sys.argv[1]).expanduser().resolve()
    out_path = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) >= 3 else checkset_path.with_suffix(".results.json")
    resume_path = Path(sys.argv[3]).expanduser().resolve() if len(sys.argv) >= 4 else None

    checkset = json.loads(checkset_path.read_text(encoding="utf-8"))
    items = checkset["items"]

    # Warm-start the persistent server once, with a timeout, so the first URL isn't a silent multi-second stall.
    b = _browse_bin()
    try:
        subprocess.run([b, "status"], text=True, capture_output=True, timeout=DEFAULT_TIMEOUT_S)
    except Exception:
        # Non-fatal: we’ll surface errors per-URL.
        pass

    prior_by_incident: dict[int, dict] = {}
    if resume_path and resume_path.exists():
        try:
            prior = json.loads(resume_path.read_text(encoding="utf-8"))
            for r in prior.get("results", []):
                if isinstance(r.get("incident_id"), int):
                    prior_by_incident[r["incident_id"]] = r
        except Exception:
            prior_by_incident = {}

    by_model: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        by_model[it["model"]].append(it)

    ordered_models = sorted(by_model.keys())
    results: list[dict] = []

    total = len(items)
    processed = 0

    for mi, model in enumerate(ordered_models):
        group = by_model[model]
        for it in group:
            url = it["asn_url"]
            print(f"checking {processed+1}/{total} {model} incident_id={it['incident_id']} url={url}", file=sys.stderr)

            prior = prior_by_incident.get(it["incident_id"])
            if prior and prior.get("status") == "PASS":
                results.append(prior)
                processed += 1
                if processed % 25 == 0 or processed == total:
                    print(f"progress {processed}/{total}", file=sys.stderr)
                continue

            try:
                raw = _browse_text(url, retry=True)
                # The `text` output includes a [text] header; keep only the text payload if present.
                payload = raw.split("[text]", 1)[-1]
                asn_date, asn_op, detail = _extract_fields(payload)

                internal_date = it["internal_date"]
                internal_op = _norm(it["internal_operator"])

                status = "PASS"
                if detail is not None:
                    status = "ERROR"
                elif asn_date != internal_date:
                    status = "FAIL"
                    detail = f"date_mismatch internal={internal_date} asn={asn_date}"
                elif (asn_op or "").casefold() != (internal_op or "").casefold():
                    status = "FAIL"
                    detail = f"operator_mismatch internal={internal_op!r} asn={asn_op!r}"

                results.append(
                    {
                        **it,
                        "asn_date": asn_date,
                        "asn_operator": asn_op,
                        "status": status,
                        "detail": detail,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        **it,
                        "asn_date": None,
                        "asn_operator": None,
                        "status": "ERROR",
                        "detail": str(e)[:500],
                    }
                )

            processed += 1
            if processed % 25 == 0 or processed == total:
                print(f"progress {processed}/{total}", file=sys.stderr)

            time.sleep(1.5)  # per-URL pacing

        if mi < len(ordered_models) - 1:
            time.sleep(10)  # per-model cooldown

    out = {"generated_at": datetime.utcnow().strftime("%Y-%m-%d"), "count": total, "results": results}
    out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(str(out_path))

    # Exit non-zero if any fails/errors.
    bad = [r for r in results if r["status"] != "PASS"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

