# LogLens (terminal version)

Compares two log files and prints **new** and **spiking** error patterns in the terminal.

## Run (no installation needed, only Python 3.9+)
```bash
python cli.py sample_logs/before.log sample_logs/after.log
python cli.py sample_logs/before.log sample_logs/after.log --min-count 1
python cli.py sample_logs/before.log sample_logs/after.log --spike-factor 2
```
Use `python3` instead of `python` on Mac/Linux if needed.

Exit code: 0 = clean, 1 = new errors or spikes found, 2 = file problem.

## How it works
1. Keep only lines containing ERROR or FATAL.
2. Normalise them: replace timestamps, UUIDs, IPs and numbers with placeholders.
3. Count each pattern.
4. Compare before vs after:
   - NEW: appears in "after" but never in "before"
   - SPIKE: "after" count is MORE than spike-factor x "before" count (default 3)
   - Patterns seen fewer than min-count times (default 3) are ignored

## Files
- analyzer.py : the logic (normalize, count_patterns, compare)
- cli.py      : reads two files, calls the analyzer, prints the report
- sample_logs : fake before/after logs for the demo

## Tests (optional)
```bash
pip install pytest
pytest
```

## Limitations
- Regex normalisation does not cover every log format.
- A fixed spike factor is simple; a real system would use a rolling baseline.
- Whole files are read into memory.
