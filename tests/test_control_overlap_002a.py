"""Pure, deterministic checks for the separately registered Experiment 002A."""
import hashlib

import pytest

from scripts import control_overlap_002a as ex


def vector(g, color=1.0, lat=20.0, snr=12.0, ruwe=1.0):
    return [g, color, lat, snr, ruwe]


def test_frozen_selection_is_deterministic_disjoint_and_hash_ordered(monkeypatch):
    monkeypatch.setattr(ex, "is_reference", lambda row: row["screened"])
    rows = [{"source_id": str(9000-i), "screened": True} for i in range(531)]
    targets, controls = ex.selected_ids(rows)
    assert (targets, controls) == ex.selected_ids(list(reversed(rows)))
    assert len(targets) == 100 and len(controls) == 431
    assert not set(targets) & set(controls)
    order = sorted([row["source_id"] for row in rows], key=lambda sid: (
        hashlib.sha256((ex.SALT + sid).encode("ascii")).hexdigest(), int(sid)))
    assert targets + controls == order


def test_rejects_reference_screen_drift(monkeypatch):
    monkeypatch.setattr(ex, "is_reference", lambda row: True)
    with pytest.raises(ValueError, match="drift"):
        ex.selected_ids([{"source_id": str(i)} for i in range(530)])


def test_distinct_maximum_cardinality_assignment():
    # First target can use either control, second can only use the first.
    targets = {"a": vector(15.0), "b": vector(14.6)}
    controls = {"10": vector(15.0), "20": vector(15.4)}
    records, matched = ex.match_vectors(targets, controls, ["a", "b"])
    assert len(matched) == 2
    assert len(set(matched.values())) == 2
    assert all(r["status"] == "matched" for r in records.values())
    assert all(max(r["absolute_tolerance_scaled_differences"]) <= 1
               for r in records.values())


def test_no_eligible_control_is_preserved():
    records, assigned = ex.match_vectors(
        {"a": vector(20.0)}, {"10": vector(12.0)}, ["a"])
    assert not assigned
    assert records["a"]["status"] == "no_eligible_control"
    assert records["a"]["eligible_control_ids"] == []
    assert records["a"]["cumulative_eligible_counts"]["G magnitude"] == 0


def test_missing_covariates_do_not_create_false_matching():
    records, assigned = ex.match_vectors(
        {"a": None}, {"10": vector(15.0)}, ["a"])
    assert not assigned
    assert records["a"]["status"] == "unusable_covariates"


def test_summary_reports_missing_not_zero():
    assert ex.summarize(
        [{"phot_g_mean_mag": 13.0}, {"phot_g_mean_mag": None},
         {"phot_g_mean_mag": 15.0}], "phot_g_mean_mag") == {
             "available": 2, "missing": 1, "median": 14.0}
