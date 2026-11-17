"""
LogLens command-line version. No web server needed.

Usage:
    python cli.py sample_logs/before.log sample_logs/after.log
    python cli.py before.log after.log --spike-factor 2 --min-count 1

Exit codes: 0 = nothing suspicious, 1 = new errors or spikes found, 2 = file problem.
(The exit code lets a CI/CD pipeline fail automatically after a bad deployment.)
"""
import argparse
import sys

from analyzer import compare, count_patterns


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare two log files and report new and spiking error patterns."
    )
    parser.add_argument("before", help="log file from before the change")
    parser.add_argument("after", help="log file from after the change")
    parser.add_argument("--spike-factor", type=float, default=3,
                        help="count must be MORE than this many times the baseline (default 3)")
    parser.add_argument("--min-count", type=int, default=3,
                        help="ignore patterns seen fewer than this many times (default 3)")
    args = parser.parse_args(argv)

    try:
        before_lines = read_lines(args.before)
        after_lines = read_lines(args.after)
    except FileNotFoundError as err:
        print(f"Error: file not found: {err.filename}", file=sys.stderr)
        return 2

    before = count_patterns(before_lines)
    after = count_patterns(after_lines)
    result = compare(before, after, spike_factor=args.spike_factor, min_count=args.min_count)

    print("LogLens report")
    print(f"Before: {sum(before.values())} errors in {len(before_lines)} lines")
    print(f"After:  {sum(after.values())} errors in {len(after_lines)} lines")

    print(f"\nNEW error patterns ({len(result['new_patterns'])}):")
    for item in result["new_patterns"]:
        print(f"  {item['count']:>4}x  {item['pattern']}")
    if not result["new_patterns"]:
        print("  none")

    print(f"\nSPIKES ({len(result['spikes'])}):")
    for item in result["spikes"]:
        print(f"  {item['before']:>3} -> {item['after']:<4} {item['pattern']}")
    if not result["spikes"]:
        print("  none")

    found_problem = bool(result["new_patterns"] or result["spikes"])
    return 1 if found_problem else 0


if __name__ == "__main__":
    sys.exit(main())
