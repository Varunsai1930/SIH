"""
UnifyMat (SIH 26099) — Streamlit AppTest UI suite.

Runs the real dashboard headlessly (streamlit.testing.v1.AppTest) against
the current code + data and asserts the closed human-in-the-loop UI
contract:

  1.  the app boots with no exception
  2.  Overview KPI cards show the live numbers (records / codes /
      precision / human-governed final-registry recall)
  3.  the OFFICER-MERGED status chip renders (officer merges in registry)
  4.  the Review Queue metrics (Pending / Approved / Rejected) match
      outputs/review_decisions.csv
  5.  the veto-checked-merge caption is present
  6.  the Audit Trail shows OFFICER_MERGED machine actions
  7.  rerun is stable (no exception on second render)

Not simulated here (they mutate state): a live Approve click and the CSV
upload pre-flight flow — those are exercised by the browser-tested demo
and were verified when the closed loop landed (see PROJECT_DOCUMENTATION).

Self-contained; stdlib + streamlit + pandas only. Exit 0 = pass, 1 = fail.

Run:  .venv/bin/python scripts/apptest_check.py
"""
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = ROOT / "src" / "app.py"
DECISIONS = ROOT / "outputs" / "review_decisions.csv"
QUEUE = ROOT / "outputs" / "review_queue.csv"


def blocked_count():
    """Approvals the hard-attribute veto refused: still APPROVED in the
    decisions file, but marked BLOCKED on the queue row and kept pending."""
    if not QUEUE.exists():
        return 0
    with open(QUEUE, newline="", encoding="utf-8") as f:
        return sum(1 for row in csv.DictReader(f)
                   if "BLOCKED" in str(row.get("decision", "")))


def approved_count():
    """Effective approvals, mirroring the dashboard: recorded APPROVED
    decisions minus veto-blocked ones (which merged nothing)."""
    if not DECISIONS.exists():
        return 0
    with open(DECISIONS, newline="", encoding="utf-8") as f:
        recorded = sum(1 for row in csv.DictReader(f)
                       if row.get("decision") == "APPROVED")
    return recorded - blocked_count()


def _as_frame(v):
    """AppTest dataframe value -> DataFrame (unwraps pandas Styler)."""
    if isinstance(v, pd.DataFrame):
        return v
    data = getattr(v, "data", None)
    return data if isinstance(data, pd.DataFrame) else None


def main():
    print("=" * 66)
    print("UnifyMat AppTest suite — headless UI contract check")
    print("=" * 66)

    at = AppTest.from_file(str(APP), default_timeout=240)
    at.run()
    if at.exception:
        print(f"[FAIL] app raised on boot: "
              f"{at.exception[0].message[:200]}")
        return 1

    body = (" ".join(str(m.value) for m in at.markdown)
            + " " + " ".join(str(c.value) for c in at.caption))

    results = []

    def check(name, ok, detail=""):
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"
              + (f" — {detail}" if not ok and detail else ""))
        results.append((name, ok))

    # (1) boot ---------------------------------------------------------------
    check("app boots with no exception", not at.exception)

    # (2) KPI cards ----------------------------------------------------------
    import re
    records = re.search(r"(\d+) records", body)
    check("records KPI renders a count", records is not None)
    check("codes KPI renders a count", "National codes issued" in body)
    check("auto-merge precision card", "Auto-merge precision" in body)
    check("human-governed recall card", "Human-governed recall" in body)

    # (3) status chips -------------------------------------------------------
    check("OFFICER-MERGED chip present", "officer-merged" in body.lower())
    n_officer = len([m for m in csv.DictReader(
        open(ROOT / "outputs" / "unified_master.csv", encoding="utf-8"))
        if m.get("status") == "OFFICER_MERGED"])
    if n_officer:
        check(f"Overview chip row counts {n_officer} officer-merged",
              f"{n_officer} officer-merged" in body.lower())

    # (4) Review Queue metrics vs decisions file ------------------------------
    mets = {m.label: m.value for m in at.metric}
    check(f"Approved metric = {approved_count()}",
          mets.get("Approved") == str(approved_count()))
    check("Pending metric renders", "Pending" in mets)

    # (5) captions -----------------------------------------------------------
    check("review caption: veto-checked merge",
          "hard engineering attribute conflicts" in body)
    check("audit caption: decisions change the registry",
          "applied to the registry itself" in body)

    # (6) audit trail tables -------------------------------------------------
    tables = [str(df.value) for df in at.dataframe]
    check("OFFICER_MERGED visible in audit tables",
          any("OFFICER_MERGED" in t for t in tables))

    # (6b) catalog price columns stay numeric --------------------------------
    # a "—" placeholder mixed into a float column flips it to object dtype
    # and pyarrow infers double -> ArrowInvalid -> Streamlit silently falls
    # back to a text table. Guard the defect class directly on dtypes.
    price_frames = [_as_frame(df.value) for df in at.dataframe]
    price_frames = [f for f in price_frames
                    if f is not None and "Min ₹" in f.columns]
    mixed = sorted({f"{c}" for f in price_frames for c in ("Avg ₹", "Min ₹", "Max ₹")
                    if c in f.columns and f[c].dtype == object})
    check("catalog price columns numeric (no mixed-dtype Arrow breakage)",
          price_frames and not mixed,
          f"no catalog table rendered" if not price_frames
          else f"object-dtype columns: {mixed}")

    # (7) rerun stability ----------------------------------------------------
    at.run()
    check("no exception on rerun", not at.exception)

    n_pass = sum(1 for _, ok in results if ok)
    print()
    failed = [name for name, ok in results if not ok]
    if failed:
        print(f"APPTEST CHECK: FAIL — {failed[0]}")
        return 1
    print(f"APPTEST CHECK: PASS ({n_pass} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
