# Frozen Reference Fixtures

These files are small, synthetic, hand-computed fixtures pinned by SHA-256 in
`manifest.json` (checked by `build/validate_fixtures.py`). They exist for
*future* numeric-parity features — F1.6 (resampling), F2.1 (indicator
registry), and similar — to validate their implementations against, without
depending on any indicator library to generate the reference values.

## Files

- `ohlc_synthetic_10bar.csv` — a 10-bar daily OHLCV series for a fictitious
  instrument, hand-authored so downstream arithmetic is easy to re-derive.
- `sma_ema_reference.json` — SMA(3) and EMA(3) of the CSV's `close` column,
  computed by hand (not by an indicator library), with an explicit warm-up
  policy: the first `window - 1` bars are `null`, never a partial average.

## Changing a fixture

A fixture's bytes are load-bearing — they are exactly what a future feature's
test asserts against. To change one:

1. Update the fixture file.
2. Recompute its SHA-256 and update `manifest.json` (do not hand-type the
   digest; regenerate it, e.g. `python -c "import hashlib; print(hashlib.sha256(open('FILE','rb').read()).hexdigest())"`).
3. Re-run `python build/validate_fixtures.py` and `pytest build/tests -q`.
4. Treat this as its own reviewed change, not an incidental edit alongside
   unrelated work — a silently-changed fixture would invalidate every test
   that already pins against the old value.

`.gitattributes` forces LF line endings for every file in this directory so
the recorded hashes stay stable across Windows and Linux clones regardless of
local `core.autocrlf` settings.
