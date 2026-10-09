# Evidence ledger

Classifications:

- `VERIFIED_REAL`: tested with running original/recompiled licensed game runtime(s).
- `VERIFIED_SYNTHETIC`: tested using fixtures/mocks or standalone harness without both real runtimes.
- `NOT_TESTED`: no actual command/run.
- `BLOCKED`: specific missing condition; include how to unblock.

For each result: date, revision(s), command, environment, expected, actual, classification, log link/path, investigator. Avoid reporting `VERIFIED_REAL` based on a compile, static scan, mock, visual overlay or invented transcript.
