"""Regression tests for code identities, CSV safety, and audit integrity."""
import csv
import pathlib

import pytest

from agents.base import AuditTrail, PHIGuard, SecurityException
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from loinc_mapper import lookup, process_csv


@pytest.mark.parametrize(
    ("query", "code"),
    [
        ("crp", "1988-5"),
        ("hs-crp", "30522-7"),
        ("esr", "4537-7"),
        ("tsh", "3016-3"),
        ("free t4", "3024-7"),
        ("free t3", "3051-0"),
        ("t3", "3053-6"),
        ("pco2", "11557-6"),
        ("bicarbonate", "1963-8"),
    ],
)
def test_verified_loinc_codes(query, code):
    assert lookup(query)["top_hit"].startswith(code + " ")


def test_short_alias_not_substring_matched():
    assert lookup("naive")["top_hit"] != "2951-2 Sodium"


@pytest.mark.parametrize("bad", [0, -2, 2.5])
def test_invalid_result_count(bad):
    with pytest.raises(ValueError):
        lookup("glucose", max_results=bad)


def test_lookup_maximum_query_length():
    with pytest.raises(ValueError):
        lookup("x" * 257)


def test_csv_header_with_existing_result_columns(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "output.csv"
    source.write_text("query,top_hit,lookup_score\ncreatinine,,\n", encoding="utf-8")
    process_csv(source, output)
    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["query", "top_hit", "lookup_score"]
        assert next(reader)["top_hit"] == "2160-0 Creatinine"


def test_csv_extra_fields_rejected(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("query\ncreatinine,unexpected\n", encoding="utf-8")
    with pytest.raises(ValueError, match="more fields"):
        process_csv(source, tmp_path / "output.csv")


def test_csv_formula_cells_escaped(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("query,note\ncreatinine,=1+1\n", encoding="utf-8")
    process_csv(source, tmp_path / "output.csv")
    with (tmp_path / "output.csv").open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["note"] == "'=1+1"


def test_audit_verifier_detects_signature_tampering():
    audit = AuditTrail(secret_key="unit-test-key")
    audit.log("test", "worker", "sample", {"status": "ok"})
    assert audit.verify_integrity()
    exposed = audit.get_trail()
    exposed[0]["actor"] = "tampered copy"
    assert audit.verify_integrity()
    audit.logs[0]["actor"] = "tampered inside"
    assert not audit.verify_integrity()


def test_audit_verifier_detects_invalid_payload_hash():
    audit = AuditTrail(secret_key="unit-test-key")
    audit.log("test", "worker", "sample", {"status": "ok"})
    audit.logs[0]["payload_hash"] = "0" * 64
    assert not audit.verify_integrity()


def test_attributes_guard_rejects_identifiers():
    task = SystemTaskPayload(
        task_id="T-01", target_identifier="LAB-01", primary_metric=1,
        attributes={"note": "MRN-12345678"},
    )
    with pytest.raises(SecurityException):
        SystemSupervisor().process_task(task)
