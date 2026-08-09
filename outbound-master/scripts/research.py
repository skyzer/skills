#!/usr/bin/env python3
"""Web research for sourcing and enrichment, behind a pluggable provider.

Two providers are supported, plus the default of having none:

  brave        Brave Search API. Cheap keyword search with a news index and
               freshness filters. Good for finding companies and dated signals.
  perplexity   Perplexity API. A research model with citations. Good for the
               synthesis questions ("what does this company do, who founded
               it") where ten blue links would each need reading.
  agent        No API at all. The runtime agent uses its own web tools
               (Claude Code and Cowork both have web search built in), and
               this script refuses politely so nothing silently returns empty.

Pick one in config/settings.yaml under providers.research.type. Keys live in
.env (BRAVE_API_KEY, PERPLEXITY_API_KEY), never in config files.

Everything returns JSON on stdout, so the agent can weave results into the
run's checkpoint files. This script finds facts; judgment about what a fact
is worth stays in the skill.

Usage:
  python scripts/research.py search "stablecoin off-ramp Nigeria" [--count 8] [--freshness 90]
  python scripts/research.py news "CompanyName" [--freshness 90]
  python scripts/research.py enrich example.com
  python scripts/research.py ask "What does example.com sell and to whom?"
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

from common import _env, cfg


def _fail(msg):
    print(json.dumps({"error": msg}), file=sys.stdout)
    sys.exit(2)


def providers():
    """The configured research providers, as a list.

    settings.yaml accepts a single name or a list, so both of these work:

        research:
          type: brave

        research:
          type: [brave, perplexity]

    With both configured, each command routes to the provider that's actually
    good at it: brave for keyword search and news, perplexity for synthesis,
    and enrich uses both.
    """
    raw = cfg("providers.research.type") or "agent"
    if isinstance(raw, str):
        raw = [raw]
    return [p.lower() for p in raw]


# ---------------------------------------------------------------- Brave

BRAVE_WEB = "https://api.search.brave.com/res/v1/web/search"
BRAVE_NEWS = "https://api.search.brave.com/res/v1/news/search"


def _brave_get(endpoint, params):
    key = _env("BRAVE_API_KEY")
    if not key:
        _fail("providers.research.type is brave but BRAVE_API_KEY is not set in .env")
    url = endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "X-Subscription-Token": key,
        "Accept": "application/json",
        "User-Agent": "outbound-master/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _brave_freshness(days):
    if not days:
        return None
    if days <= 1:
        return "pd"
    if days <= 7:
        return "pw"
    if days <= 31:
        return "pm"
    return "py"


def brave_search(query, count=8, freshness_days=None, news=False):
    params = {"q": query, "count": count}
    fr = _brave_freshness(freshness_days)
    if fr:
        params["freshness"] = fr
    data = _brave_get(BRAVE_NEWS if news else BRAVE_WEB, params)
    items = data.get("results") if news else data.get("web", {}).get("results", [])
    out = []
    for r in items or []:
        out.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("description"),
            "age": r.get("age") or r.get("page_age"),
        })
    return out


# ---------------------------------------------------------------- Perplexity

PPLX_URL = "https://api.perplexity.ai/chat/completions"


def perplexity_ask(question, freshness_days=None):
    key = _env("PERPLEXITY_API_KEY")
    if not key:
        _fail("providers.research.type is perplexity but PERPLEXITY_API_KEY is not set in .env")
    body = {
        "model": _env("PERPLEXITY_MODEL", "sonar"),
        "messages": [
            {"role": "system",
             "content": "You are a B2B research assistant. Answer factually and concisely. "
                        "Only state things you can cite. If you can't find something, say so "
                        "plainly rather than guessing. Include dates for any event you mention."},
            {"role": "user", "content": question},
        ],
    }
    if freshness_days and freshness_days <= 31:
        body["search_recency_filter"] = "month"
    elif freshness_days:
        body["search_recency_filter"] = "year"
    req = urllib.request.Request(
        PPLX_URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "outbound-master/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.load(resp)
    choice = (data.get("choices") or [{}])[0]
    return {
        "answer": choice.get("message", {}).get("content"),
        "citations": data.get("citations") or data.get("search_results") or [],
    }


# ---------------------------------------------------------------- commands

ENRICH_QUESTIONS = (
    "What does {d} do, who are its customers, and who founded or runs it?",
    "What payment or infrastructure providers does {d} currently use or integrate with?",
    "What has {d} announced, launched, raised or changed in the last 90 days? Give dates.",
)


def cmd_search(args):
    return {"provider": "brave",
            "results": brave_search(args.query, args.count, args.freshness)}


def cmd_news(args):
    return {"provider": "brave",
            "results": brave_search(args.query, args.count, args.freshness or 90, news=True)}


def cmd_enrich(args, active):
    sections = []
    if "perplexity" in active:
        sections += [dict(provider="perplexity", question=q.format(d=args.domain),
                          **perplexity_ask(q.format(d=args.domain), freshness_days=365))
                     for q in ENRICH_QUESTIONS]
    if "brave" in active:
        sections += [
            {"provider": "brave", "query": f"{args.domain} company",
             "results": brave_search(f'"{args.domain}"', 6)},
            {"provider": "brave", "query": f"{args.domain} news",
             "results": brave_search(args.domain, 6, 90, news=True)},
        ]
    return {"providers": sorted(set(active) & {"brave", "perplexity"}),
            "domain": args.domain, "sections": sections}


def cmd_ask(args):
    return {"provider": "perplexity", **perplexity_ask(args.query, args.freshness)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, need_query in (("search", True), ("news", True), ("ask", True), ("enrich", False)):
        s = sub.add_parser(name)
        if need_query:
            s.add_argument("query")
        else:
            s.add_argument("domain")
        s.add_argument("--count", type=int, default=8)
        s.add_argument("--freshness", type=int, default=None,
                       help="only results newer than this many days")
    args = ap.parse_args()

    active = providers()
    if not (set(active) & {"brave", "perplexity"}):
        _fail("providers.research.type is 'agent': no research API is configured. "
              "Use the runtime's own web search instead of this script, or set "
              "providers.research.type to brave, perplexity, or a list of both, "
              "and add the key(s) to .env.")

    # Route each command to the provider that's good at it.
    if args.cmd == "ask":
        if "perplexity" not in active:
            _fail("'ask' needs the perplexity provider; brave does keyword search only. "
                  "Use 'search' or 'news', or add perplexity to providers.research.type.")
        result = cmd_ask(args)
    elif args.cmd == "enrich":
        result = cmd_enrich(args, active)
    elif "brave" in active:
        result = {"search": cmd_search, "news": cmd_news}[args.cmd](args)
    else:  # perplexity only: emulate search with a cited answer
        result = {"provider": "perplexity",
                  **perplexity_ask(f"Search: {args.query}. List sources with dates.",
                                   args.freshness)}
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
