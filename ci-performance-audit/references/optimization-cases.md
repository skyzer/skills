# CI optimization cases

| Observation | Candidate change | Verification |
| --- | --- | --- |
| Every job installs dependencies for every component | Provision each dependency in the jobs that need it. Pin toolchain versions and key reuse to lockfiles and relevant platform inputs. | Run from a fresh worker and after a dependency change. Compare installation time, download bytes and total wall time. |
| A shared fixture serializes otherwise independent workers | Give workers private fixtures and preserve per-test isolation. | Prove every original case still runs and check fixture cleanup, data isolation and contention. Skysay moved Postgres shards to private database templates to remove contention on the shared template. |
| One test shard finishes long after the others | Use recorded test durations to balance shards. Refresh timings as the suite changes. | Compare the slowest shard, verify exact coverage across shards, and record failures and retries. |
| Two isolated proof families are serial | Run them concurrently if there is capacity. Join both, retain their logs, and fail if either fails. | Alternate serial and parallel trials on the same artifact and runner shape. Verify they use independent state, such as ports and databases. Check that either failure or missing proof fails the gate. In shell, capture and check each child PID’s exit status. |
| Every change runs every suite | Declare affected components and required checks in a shared registry or equivalent configuration. | Replay changes with known test failures and check whether selection would have run the failing cases. Probe shared code, lockfiles, CI and test infrastructure changes. Use the full suite when selection is uncertain. Spot-check selection against full runs to measure misses. |
| Branches routinely pay for repeat heavy runs before review | Give authors a focused iteration path and run the required merge pipeline on the candidate being reviewed. | Measure time to actionable failure and to merge, plus runner-minutes including canceled and retried attempts. Keep a way to request full CI earlier. |
| Compatible changes are already waiting for capacity | Consider one integration candidate from pinned branch heads. Recompute the required plan for the combined diff and verify the exact candidate against main. | Count natural overlaps, estimated duplicated compute, delay to the first branch, and the cost of failed batches. Start a lone ready change when capacity is available. |
| Different worker pools charge different rates | Compare equivalent jobs on eligible runner shapes and count lifecycle costs. | Measure cost per completed gate, including queueing, preemption, boot, disk and network where available. Price by actual worker shape instead of runner labels. |

## Benchmark design

Keep a record of baseline and candidate source revisions, runner shape, cache state, workload, and exact test inventory. For an isolated parallelism change, run the same built artifact in both modes. For network or startup changes, distinguish warm and cold runs. Report individual runs and label the summary statistic for a small sample. Use a representative cohort for a p90 claim and describe its size and mix.

Quantify experiment findings at the level measured. For example, Skysay measured two proof families at about 243 seconds serial and 156 seconds parallel on the same built image, with two trials per mode and 571 tests with zero skips in every trial. The figures are means. A separate broad-pipeline comparison took 13m45s and 12m01s, with differing worker allocation. The substage result establishes a measured improvement in that substage. The broad comparison is an observation across two runs.

Skysay also observed median downloads per worker fall from 311.9 MB to 7.3 MB after refreshing the worker image. The after sample covered 189 workers. Report the download metric as observed and verify billing separately. Include cache and image-refresh costs when estimating recurring savings.

Example report finding: “Parallelize the two image test suites. Each runs against the same pinned artifact in its own container. The combined step dropped by 86.5 seconds across two trials per mode, with all 571 cases retained and neither suite allowed to fail silently. Measure the full pipeline separately.”
