from collections import Counter

import cli
from analyzer import compare, count_patterns, is_error, normalize


# ---------- analyzer.py (pure logic) ----------
def test_normalize_replaces_numbers_ip_uuid_and_timestamp():
    line = "2026-11-17 10:00:01 ERROR api user 4521 from 10.0.0.7 cart b2061ecc-65d4-64fd-29e7-8b06a72ed508"
    assert normalize(line) == "ERROR api user <NUM> from <IP> cart <UUID>"


def test_similar_errors_get_same_pattern():
    assert normalize("ERROR pay Timeout for order 111") == normalize("ERROR pay Timeout for order 999")


def test_is_error_only_matches_whole_word_levels():
    assert is_error("2026-11-17 10:00:00 ERROR something broke")
    assert is_error("FATAL out of memory")
    assert not is_error("INFO all good")
    assert not is_error("INFO user MYERRORS list")


def test_count_patterns_ignores_non_errors():
    lines = ["INFO ok 1", "ERROR boom 1", "ERROR boom 2", "WARN slow"]
    assert count_patterns(lines) == Counter({"ERROR boom <NUM>": 2})


def test_compare_finds_new_and_spike():
    result = compare(Counter({"A": 5, "B": 4}), Counter({"A": 20, "B": 4, "C": 10}), spike_factor=3, min_count=3)
    assert result["new_patterns"] == [{"pattern": "C", "count": 10}]
    assert result["spikes"] == [{"pattern": "A", "before": 5, "after": 20}]


def test_compare_ignores_rare_errors_below_min_count():
    assert compare(Counter(), Counter({"rare": 1}), min_count=3)["new_patterns"] == []


def test_compare_no_spike_when_exactly_at_factor():
    assert compare(Counter({"A": 5}), Counter({"A": 15}), spike_factor=3)["spikes"] == []


# ---------- cli.py ----------
def test_cli_reports_new_and_spike(capsys):
    code = cli.main(["sample_logs/before.log", "sample_logs/after.log"])
    out = capsys.readouterr().out
    assert code == 1
    assert "NullPointerException" in out
    assert "6 -> 25" in out
    assert "Cache miss" not in out


def test_cli_no_problem_returns_zero():
    assert cli.main(["sample_logs/before.log", "sample_logs/before.log"]) == 0


def test_cli_missing_file_returns_two():
    assert cli.main(["nope.log", "sample_logs/after.log"]) == 2
