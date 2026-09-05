"""
Comprehensive tests for loinc_mapper core functionality.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import loinc_mapper


def test_lookup_exact_match():
    """Test exact keyword match returns highest score."""
    result = loinc_mapper.lookup("creatinine")
    assert result["top_hit"] == "2160-0 Creatinine"
    assert result["score"] >= 10.0


def test_lookup_partial_match():
    """Test partial/substring match returns a hit."""
    result = loinc_mapper.lookup("glu")
    assert result["top_hit"] == "2345-7 Glucose"
    assert result["score"] > 0


def test_lookup_loinc_code():
    """Test lookup by exact LOINC code."""
    result = loinc_mapper.lookup("2160-0")
    assert "2160-0" in result["top_hit"]
    assert result["score"] >= 10.0


def test_lookup_no_match():
    """Test that a nonsense query returns no match."""
    result = loinc_mapper.lookup("xyzzy_nonexistent_test")
    assert result["top_hit"] == "no match"
    assert result["score"] == 0


def test_lookup_empty_query():
    """Test that empty query returns no match without error."""
    result = loinc_mapper.lookup("")
    assert result["top_hit"] == "no match"
    assert result["score"] == 0


def test_lookup_none_query():
    """Test that None query returns no match without error."""
    result = loinc_mapper.lookup(None)
    assert result["top_hit"] == "no match"
    assert result["score"] == 0


def test_lookup_case_insensitive():
    """Test that lookup is case insensitive."""
    r1 = loinc_mapper.lookup("CREATININE")
    r2 = loinc_mapper.lookup("creatinine")
    assert r1["top_hit"] == r2["top_hit"]


def test_lookup_max_results():
    """Test max_results parameter limits output."""
    result = loinc_mapper.lookup("blood", max_results=2)
    assert len(result["all"]) <= 2


def test_levenshtein_identical():
    """Test Levenshtein ratio for identical strings."""
    assert loinc_mapper._levenshtein_ratio("creatinine", "creatinine") == 1.0


def test_levenshtein_completely_different():
    """Test Levenshtein ratio for completely different strings."""
    assert loinc_mapper._levenshtein_ratio("abc", "xyz") < 0.5


def test_levenshtein_empty():
    """Test Levenshtein ratio handles empty strings."""
    assert loinc_mapper._levenshtein_ratio("", "test") == 0.0
    assert loinc_mapper._levenshtein_ratio("test", "") == 0.0


def test_levenshtein_fuzzy_match():
    """Test Levenshtein ratio for similar strings (typo tolerance)."""
    ratio = loinc_mapper._levenshtein_ratio("creatinine", "creatinin")
    assert ratio >= 0.7


def test_process_csv_success():
    """Test CSV processing with valid input."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = pathlib.Path(tmpdir) / "input.csv"
        output_path = pathlib.Path(tmpdir) / "output.csv"

        input_path.write_text("query,lab_name\ncreatinine,serum\nsodium,plasma\n", encoding="utf-8")

        results = loinc_mapper.process_csv(str(input_path), str(output_path))

        assert len(results) == 2
        assert results[0]["top_hit"] == "2160-0 Creatinine"
        assert results[1]["top_hit"] == "2951-2 Sodium"
        assert output_path.exists()


def test_process_csv_file_not_found():
    """Test CSV processing raises FileNotFoundError for missing file."""
    try:
        loinc_mapper.process_csv("/nonexistent/path.csv", "/tmp/out.csv")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_process_csv_empty_file():
    """Test CSV processing raises ValueError for empty file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = pathlib.Path(tmpdir) / "empty.csv"
        input_path.write_text("", encoding="utf-8")

        try:
            loinc_mapper.process_csv(str(input_path), str(pathlib.Path(tmpdir) / "out.csv"))
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


def test_process_csv_no_data_rows():
    """Test CSV processing raises ValueError for file with only header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = pathlib.Path(tmpdir) / "header_only.csv"
        input_path.write_text("query,lab_name\n", encoding="utf-8")

        try:
            loinc_mapper.process_csv(str(input_path), str(pathlib.Path(tmpdir) / "out.csv"))
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


def test_build_parser():
    """Test CLI argument parser builds correctly."""
    parser = loinc_mapper.build_parser()
    assert parser is not None


def test_main_single_command():
    """Test main() with single lookup command."""
    exit_code = loinc_mapper.main(["single", "creatinine"])
    assert exit_code == 0


def test_main_batch_command():
    """Test main() with batch command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = pathlib.Path(tmpdir) / "input.csv"
        output_path = pathlib.Path(tmpdir) / "output.csv"
        input_path.write_text("query\nhemoglobin\n", encoding="utf-8")

        exit_code = loinc_mapper.main(["batch", "--input", str(input_path), "--output", str(output_path)])
        assert exit_code == 0


def test_main_batch_missing_file():
    """Test main() batch command handles missing file gracefully."""
    exit_code = loinc_mapper.main(["batch", "--input", "/nonexistent.csv", "--output", "/tmp/out.csv"])
    assert exit_code == 1


def test_detect_query_column():
    """Test query column detection logic."""
    assert loinc_mapper._detect_query_column(["query", "lab_name"]) == "query"
    assert loinc_mapper._detect_query_column(["test", "value"]) == "test"
    assert loinc_mapper._detect_query_column(["foo", "bar"]) == "foo"
    assert loinc_mapper._detect_query_column([]) == ""
