#!/usr/bin/env python3
"""
LOINC Lab Mapper
Fuzzy maps local lab test names to LOINC codes via token overlap and Levenshtein ratio (no external deps).
Stdlib parser / mapper with batch CSV and single lookup.
"""
import argparse
import csv
import json
import pathlib
import sys


# LOINC code database for common lab tests
# Format: (LOINC code, display name, [keywords/aliases])
LOINC_DATABASE = [
    ("2160-0", "Creatinine", ["creatinine", "crea", "cr"]),
    ("6690-2", "WBC", ["wbc", "white blood cell", "white blood count", "leukocyte"]),
    ("718-7", "Hemoglobin", ["hemoglobin", "hgb", "hb"]),
    ("4548-4", "HbA1c", ["hba1c", "a1c", "hemoglobin a1c", "glycated hemoglobin"]),
    ("2951-2", "Sodium", ["sodium", "na"]),
    ("2823-3", "Potassium", ["potassium", "k"]),
    ("2075-0", "Chloride", ["chloride", "cl"]),
    ("17861-6", "Calcium", ["calcium", "ca"]),
    ("2345-7", "Glucose", ["glucose", "glu", "blood sugar"]),
    ("2571-8", "Triglyceride", ["triglyceride", "tg", "trig"]),
    ("2093-3", "Cholesterol", ["cholesterol", "chol", "tc"]),
    ("2085-9", "HDL Cholesterol", ["hdl", "hdl cholesterol", "high density lipoprotein"]),
    ("2089-1", "LDL Cholesterol", ["ldl", "ldl cholesterol", "low density lipoprotein"]),
    ("1988-5", "CRP", ["crp", "c-reactive protein", "c reactive protein"]),
    ("30522-7", "hs-CRP", ["hs-crp", "hscrp", "high sensitivity crp", "high sensitivity c-reactive protein"]),
    ("4537-7", "ESR (Westergren)", ["esr", "sed rate", "erythrocyte sedimentation rate", "westergren"]),
    ("1751-7", "Albumin", ["albumin", "alb"]),
    ("1975-2", "Bilirubin", ["bilirubin", "bili", "total bilirubin"]),
    ("1742-6", "ALT", ["alt", "alanine aminotransferase", "sgpt"]),
    ("1920-8", "AST", ["ast", "aspartate aminotransferase", "sgot"]),
    ("2885-2", "Total Protein", ["total protein", "tp", "protein total"]),
    ("3094-0", "Urea Nitrogen", ["bun", "blood urea nitrogen", "urea nitrogen"]),
    ("3016-3", "TSH", ["tsh", "thyroid stimulating hormone", "thyrotropin"]),
    ("3024-7", "Free T4", ["free t4", "ft4", "free thyroxine"]),
    ("3053-6", "Total T3", ["t3", "total t3", "triiodothyronine"]),
    ("3051-0", "Free T3", ["free t3", "ft3", "free triiodothyronine"]),
    ("11558-4", "pH", ["ph", "blood ph"]),
    ("11557-6", "pCO2", ["pco2", "carbon dioxide partial pressure"]),
    ("11556-8", "pO2", ["po2", "oxygen", "o2"]),
    ("1963-8", "Bicarbonate", ["hco3", "bicarbonate", "serum bicarbonate"]),
]


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """Compute similarity ratio between two strings using Levenshtein distance.

    Returns a float between 0.0 and 1.0 where 1.0 means identical strings.
    Pure Python implementation with no external dependencies.
    """
    s1 = s1.lower().strip()
    s2 = s2.lower().strip()

    if not s1 or not s2:
        return 0.0

    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)

    # Use iterative approach with single row for memory efficiency
    previous_row = list(range(len2 + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    distance = previous_row[-1]
    max_len = max(len1, len2)
    if max_len == 0:
        return 1.0
    return 1.0 - (distance / max_len)


def lookup(query: str, max_results: int = 5) -> dict:
    """Single lookup: token overlap + Levenshtein similarity scoring (no external deps).

    Returns top matching LOINC codes ranked by relevance score.

    Args:
        query: The lab test name or code to search for.
        max_results: Maximum number of results to return.

    Returns:
        Dictionary with query, top_hit, score, and all matches.
    """
    if query is None:
        query = ""
    query = str(query).lower().strip()

    if not isinstance(max_results, int) or max_results < 1:
        raise ValueError("max_results must be a positive integer")
    if len(query) > 256:
        raise ValueError("query must be 256 characters or fewer")
    if not query:
        return {"query": query, "top_hit": "no match", "score": 0, "all": []}

    query_tokens = set(query.split())
    scored = []
    for loinc_code, display_name, keywords in LOINC_DATABASE:
        max_keyword_score = 0

        # Check keyword matches
        for keyword in keywords:
            kw = keyword.lower().strip()

            # Exact keyword match
            if kw == query:
                max_keyword_score = max(max_keyword_score, 10.0)
                break

            # Keyword substring match (keyword contained in query)
            if len(kw) >= 3 and kw in query:
                max_keyword_score = max(max_keyword_score, 6.0)

            # Query substring of keyword (query contained in keyword)
            if len(query) >= 3 and query in kw:
                max_keyword_score = max(max_keyword_score, 4.0)

            # Token overlap scoring
            keyword_tokens = set(kw.split())
            overlap = len(query_tokens & keyword_tokens)
            if overlap > 0 and (len(query) >= 3 or query == kw):
                max_keyword_score = max(max_keyword_score, overlap * 2.0)

            # Levenshtein similarity for fuzzy matching (threshold 0.7)
            ratio = _levenshtein_ratio(query, kw)
            if len(query) >= 3 and len(kw) >= 3 and ratio >= 0.7:
                max_keyword_score = max(max_keyword_score, ratio * 5.0)

        # Also check display name for matches
        name_lower = display_name.lower()
        if len(query) >= 3 and query in name_lower:
            max_keyword_score = max(max_keyword_score, 5.0)
        elif len(name_lower) >= 3 and name_lower in query:
            max_keyword_score = max(max_keyword_score, 3.0)

        # LOINC code exact match bonus
        if query == loinc_code.lower():
            max_keyword_score = max(max_keyword_score, 10.0)

        if max_keyword_score > 0:
            scored.append((max_keyword_score, f"{loinc_code} {display_name}"))

    scored.sort(reverse=True, key=lambda x: x[0])

    # Round scores for cleaner output
    scored = [(round(score, 2), label) for score, label in scored]

    top = scored[0] if scored else (0, "no match")
    return {
        "query": query,
        "top_hit": top[1],
        "score": top[0],
        "all": scored[:max_results],
    }


def _detect_query_column(fieldnames: list) -> str:
    """Detect the most likely column name containing lab test queries."""
    if not fieldnames:
        return ""

    priority_cols = ["query", "test", "lab", "name", "code"]

    for candidate in priority_cols:
        for col in fieldnames:
            if col.lower() == candidate:
                return col

    # Fallback to first column
    return fieldnames[0]


def process_csv(input_path: str, output_path: str) -> list:
    """Process a CSV file containing lab test queries, mapping each to LOINC codes.

    Args:
        input_path: Path to input CSV file with a query column.
        output_path: Path to output CSV file for results.

    Returns:
        List of result dictionaries with LOINC mapping information.

    Raises:
        FileNotFoundError: If input file does not exist.
        ValueError: If input file is empty, has no header, or contains no data rows.
    """
    input_file = pathlib.Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not input_file.is_file():
        raise ValueError(f"Input path is not a file: {input_path}")

    output_file = pathlib.Path(output_path)

    try:
        with open(input_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
    except (csv.Error, UnicodeError) as e:
        raise ValueError(f"CSV parsing error in {input_path}: {e}")

    if not fieldnames:
        raise ValueError(f"CSV file {input_path} has no header row")
    if not rows:
        raise ValueError(f"CSV file {input_path} contains no data rows")

    qcol = _detect_query_column(fieldnames)

    results = []
    for row in rows:
        if None in row:
            raise ValueError("CSV contains a row with more fields than its header")
        res = lookup(row.get(qcol, ""))
        merged = {**row, "top_hit": res["top_hit"], "lookup_score": res["score"]}
        results.append(merged)

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_fieldnames = list(dict.fromkeys([*fieldnames, "top_hit", "lookup_score"]))
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        # Prevent spreadsheet formula execution when the exported CSV is opened in Excel.
        safe_rows = [
            {k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else v)
             for k, v in row.items()}
            for row in results
        ]
        writer.writerows(safe_rows)

    return results


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(prog="loinc_mapper", description="LOINC Lab Mapper")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # Single lookup command
    single = subparsers.add_parser("single", help="Look up a single lab test name")
    single.add_argument("query", nargs="?", default="", help="Lab test name to look up")
    single.add_argument("--query", dest="q2", help="Alternative query argument")
    single.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results (default: 5)",
    )

    # Batch CSV command
    batch = subparsers.add_parser("batch", help="Batch process a CSV file")
    batch.add_argument("--input", required=True, help="Input CSV file path")
    batch.add_argument("--output", required=True, help="Output CSV file path")
    return parser


def main(argv=None) -> int:
    """Main entry point for the LOINC Lab Mapper CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "single":
        q = getattr(args, "q2", None) or getattr(args, "query", "")
        try:
            result = lookup(q, max_results=args.max_results)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2))
        return 0

    if args.cmd == "batch":
        try:
            res = process_csv(args.input, args.output)
            print(json.dumps({"processed": len(res), "output": args.output}, indent=2))
            return 0
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
