# LogLens

**LogLens compares two log files, one from before a change and one from after it, and reports which errors are new and which errors have suddenly become more frequent.**

It is useful after a deployment, a configuration change, or a library upgrade, when you want to know *"did this make things worse?"* without reading hundreds of log lines by hand.

- Pure Python, **no dependencies** (only the standard library)
- Works from the terminal and in CI/CD pipelines (it returns a meaningful exit code)
- Small, readable code base with unit tests

---

## Table of contents

1. [Quick start](#quick-start)
2. [Example output](#example-output)
3. [Command-line options](#command-line-options)
4. [Exit codes](#exit-codes)
5. [How it works](#how-it-works)
6. [Project structure](#project-structure)
7. [Using it in a CI/CD pipeline](#using-it-in-a-cicd-pipeline)
8. [Running the tests](#running-the-tests)
9. [Log format requirements](#log-format-requirements)
10. [Limitations and ideas for improvement](#limitations-and-ideas-for-improvement)

---

## Quick start

**Requirements:** Python 3.9 or newer. Nothing else needs to be installed.

```bash
git clone https://github.com/Zarrar201/loglens-cli.git
cd loglens-cli
python cli.py sample_logs/before.log sample_logs/after.log
```

On macOS/Linux you may need to use `python3` instead of `python`.

---

## Example output

Running LogLens on the included sample logs:

```text
$ python cli.py sample_logs/before.log sample_logs/after.log
LogLens report
Before: 10 errors in 200 lines
After:  42 errors in 232 lines

NEW error patterns (1):
    12x  ERROR order-service NullPointerException in calculateTotal for cart <UUID>

SPIKES (1):
    6 -> 25   ERROR payment-service Timeout calling gateway after <NUM> ms for order <NUM>
```

How to read this report:

| Section | Meaning |
|---|---|
| **Before / After** | Total number of error lines and total number of lines in each file. |
| **NEW error patterns** | Errors that appear in the *after* log but **never** appeared in the *before* log. `12x` means it happened 12 times. |
| **SPIKES** | Errors that existed before but are now much more frequent. `6 -> 25` means 6 occurrences before and 25 after. |

In this example, the change introduced a brand-new `NullPointerException` in the order service, and payment gateway timeouts went up more than 4 times.

Because problems were found, the program exits with code `1`.

---

## Command-line options

```text
python cli.py BEFORE AFTER [--spike-factor N] [--min-count N]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `BEFORE` | yes | — | Path to the log file from **before** the change (the baseline). |
| `AFTER` | yes | — | Path to the log file from **after** the change. |
| `--spike-factor` | no | `3` | An error counts as a spike only if its *after* count is **more than** this many times its *before* count. |
| `--min-count` | no | `3` | Ignore error patterns that appear fewer than this many times in the *after* log. Filters out rare one-off errors. |
| `-h`, `--help` | no | — | Show the help message. |

### Examples

```bash
# Default settings
python cli.py sample_logs/before.log sample_logs/after.log

# Also report errors that happen only once
python cli.py sample_logs/before.log sample_logs/after.log --min-count 1

# Be more sensitive: treat a doubling as a spike
python cli.py sample_logs/before.log sample_logs/after.log --spike-factor 2
```

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Nothing suspicious: no new error patterns and no spikes. |
| `1` | At least one new error pattern or spike was found. |
| `2` | A log file could not be found. |

---

## How it works

LogLens runs in four steps.

### 1. Keep only error lines

A line counts as an error if it contains the word `ERROR` or `FATAL` as a **whole word**. `INFO`, `WARN` and `DEBUG` lines are ignored. A word like `MYERRORS` does **not** count.

### 2. Normalise each error line

The same error usually appears with different details every time: a different timestamp, user ID, IP address and so on. To group them together, LogLens replaces the parts that change with placeholders:

| What | Example | Replaced with |
|---|---|---|
| Timestamp at the start of the line | `2026-11-17 10:00:01 ` | *(removed)* |
| UUID | `b2061ecc-65d4-64fd-29e7-8b06a72ed508` | `<UUID>` |
| IPv4 address | `10.0.0.7` | `<IP>` |
| Any other number | `4521` | `<NUM>` |

For example, these two lines:

```text
2026-11-17 10:05:12 ERROR payment-service Timeout calling gateway after 3000 ms for order 1182
2026-11-17 10:07:44 ERROR payment-service Timeout calling gateway after 5000 ms for order 9921
```

both become the same **pattern**:

```text
ERROR payment-service Timeout calling gateway after <NUM> ms for order <NUM>
```

The replacements run in the order shown above. UUIDs and IP addresses are replaced before plain numbers, so their digits don't get turned into `<NUM>` first.

### 3. Count each pattern

LogLens counts how many times each pattern appears in the *before* file and in the *after* file.

### 4. Compare before and after

For every pattern in the *after* file:

1. If it appears fewer than `--min-count` times, it is **ignored**.
2. If it never appeared in the *before* file, it is reported as **NEW**.
3. If its *after* count is **greater than** `--spike-factor` × its *before* count, it is reported as a **SPIKE**.

With the defaults (`spike-factor 3`), going from 5 to 15 is **not** a spike (15 is exactly 3 × 5), but going from 5 to 16 is.

Results are sorted so the most frequent problems are shown first.

---

## Project structure

```text
loglens-cli/
├── analyzer.py        # Core logic: normalize(), is_error(), count_patterns(), compare()
├── cli.py             # Command-line interface: reads files, runs the analyzer, prints the report
├── test_loglens.py    # Unit tests for the analyzer and the CLI (pytest)
├── sample_logs/
│   ├── before.log     # Example log before a deployment (200 lines)
│   └── after.log      # Example log after a deployment (232 lines)
└── README.md
```

### `analyzer.py`

Contains only **pure functions**: no file access and no printing. This makes the logic easy to test and reuse (for example, in a web API later).

| Function | Purpose |
|---|---|
| `normalize(line)` | Turns a raw log line into a pattern by removing the timestamp and replacing UUIDs, IPs and numbers with placeholders. |
| `is_error(line)` | Returns `True` if the line contains `ERROR` or `FATAL` as a whole word. |
| `count_patterns(lines)` | Returns a `Counter` of normalised patterns for all error lines. |
| `compare(baseline, current, spike_factor, min_count)` | Returns `{"new_patterns": [...], "spikes": [...]}`. |

### `cli.py`

Parses the command-line arguments with `argparse`, reads both files (skipping blank lines), calls the analyzer, prints the report and returns the exit code.

---

## Using it in a CI/CD pipeline

Because LogLens exits with code `1` when it finds problems, a pipeline can stop a bad release automatically:

```bash
python cli.py logs/before_deploy.log logs/after_deploy.log || echo "Error regression detected!"
```

Example GitHub Actions step:

```yaml
- name: Check for new errors after deploy
  run: python cli.py logs/before.log logs/after.log
```

If new errors or spikes are found, the step fails.

---

## Running the tests

The tests use [pytest](https://pytest.org). Run them from the project folder, because some tests use the files in `sample_logs/`:

```bash
pip install pytest
pytest
```

Expected output:

```text
10 passed
```

What the tests cover:

- Normalising timestamps, numbers, IPs and UUIDs
- Grouping similar errors into the same pattern
- Matching only whole-word `ERROR` and `FATAL`
- Detecting new patterns and spikes
- Ignoring rare errors below `--min-count`
- Not reporting a spike when the count is exactly at the factor
- CLI exit codes `0`, `1` and `2`

---

## Log format requirements

LogLens works best with plain-text logs that look like this:

```text
2026-11-17 10:00:01 ERROR service-name Message text with ids 123 and ip 10.0.0.7
```

- One log entry per line, UTF-8 encoded
- An optional timestamp at the start, in `YYYY-MM-DD HH:MM:SS` format (a `T` separator, fractional seconds and a trailing `Z` are also accepted)
- The level written as an uppercase word (`ERROR`, `FATAL`)

Other formats still work, but patterns may group less well. For example, a timestamp in a different format will be turned into several `<NUM>` placeholders instead of being removed.

---

## Limitations and ideas for improvement

**Current limitations**

- Normalisation uses simple regular expressions and does not cover every log format (for example, hex IDs, email addresses or quoted values are not replaced).
- Multi-line errors such as stack traces are treated as separate lines.
- A fixed spike factor is simple. A production system would use a rolling baseline or statistical thresholds.
- Both files are read fully into memory, so very large logs may use a lot of RAM.
- Patterns that **disappeared** or **decreased** are not reported.

**Possible improvements**

- JSON output (`--json`) for use by other tools
- Support for `.gz` compressed logs and streaming large files
- Configurable error levels (for example, also include `WARN`)
- Report resolved errors (present before, gone after)
- Colour output in the terminal
