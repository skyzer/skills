# Examples

`dry-run-example.md` is real output from `scripts/dry_run.py`, lightly
anonymised. Five prospects staged, one would send, four skipped.

It is here because a repo with no evidence anything ever ran is asking you to
take its word for it. The four skips are the interesting part: a catch-all
domain with a role address, a hook that scored below the confidence threshold,
an unsendable verdict, and a domain on the exclusion list. Each one is a send
the system declined to make, with the reason recorded.
