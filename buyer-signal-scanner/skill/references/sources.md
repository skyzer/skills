# Sources

Each source in `config/sources.yaml` has `enabled`, `queries`, `max_age_days`, `allow_links`, `reply_max_words`, and `access` (`script` or `browser`). This file is what each one is good for and how to search it without getting blocked.

## X (`access: browser`)

Best source for real-time intent from founders and operators; worst source for scripts. x.com blocks fetchers via robots.txt and the API costs money. Search with the runtime's browser (Claude in Chrome or equivalent) using the advanced-search form: `"which provider" OR "anyone recommend" <topic> lang:en -filter:replies since:<date>`. Read the author's profile before scoring. Do not use mirrors, scrapers or cached copies to get around the block; if no browser is available, X is simply off for that run and the summary says so.

## Reddit (`access: script`, falls back to browser)

`scripts/search.py reddit "<query>"` uses the public JSON search endpoint (`/search.json`) with a descriptive user agent; it works unauthenticated at low volume and returns 403 or 429 when it doesn't. When that happens, search in the browser. Subreddits to include are in the query list. Read the subreddit's rules: some ban vendor replies outright, and a public reply there is a ban, not a lead. `sources.yaml` has a `no_reply_subreddits` list for those; signals from them get a DM draft only.

## Hacker News (`access: script`)

`scripts/search.py hn "<query>"` uses the Algolia API (no key, generous limits). Good for "Ask HN: what do you use for" and comments under launch threads of competitors. HN readers punish pitches harder than anywhere; public replies are pure help or nothing.

## GitHub (`access: script`)

`scripts/search.py github "<query>"` searches issues and discussions (unauthenticated: 10 requests/minute; set `GITHUB_TOKEN` in `.env` for 30). Signals look like: an issue on a competitor's SDK about a market they don't support, a discussion asking for an integration, a repo README that says "TODO: payments". Authors are developers, so the reply is technical and the DM is often an email found on their profile.

## Product Hunt (`access: browser`)

Comments under competitor launches and "looking for" posts. Low volume, high fit.

## Forums and communities (`access: browser`)

Indie Hackers, dev.to, niche Discord/Slack communities the operator belongs to (only ones they've listed; never join to scan), industry forums. Queries are the same list; the browser does the search.

## Review sites (`access: browser`)

G2, Capterra, Trustpilot reviews of competitors, 1-3 stars, last 14 days. The reviewer is rarely reachable directly, so these become `needs_review` with the company as the author, and usually export to outbound rather than get a reply.

## Job ads (`access: browser`, or `script` for boards with JSON)

A company hiring for the job your product does is a 6-7 signal. Search job boards for the role titles in `sources.yaml`. The author is the company; the reply is a DM to a named person, found the way the outbound skill finds them, or the signal is exported.

## What blocks scripts, and what to do

If `search.py` gets a 403, 429 or a captcha page, it says so and stops for that source. Do not retry in a loop, rotate user agents, or fetch through a proxy. The rule from the repo README applies: skipping is free, being blocked from a platform the operator's account lives on is not.

## Query design

Queries live in `config/sources.yaml`, per source, in the operator's words for the problem. Good queries name the problem, not the product category: "pay supplier in China from Nigeria" beats "cross-border payments API". Keep each list under 15 queries; more than that and the scan spends its time on noise. When a query returns nothing useful three runs in a row, drop it and say so in the summary.
