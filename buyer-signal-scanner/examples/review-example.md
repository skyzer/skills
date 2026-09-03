# Buyer signals · 2026-09-03

2 ready with drafts · 1 need a human decision · 0 acted on · 0 expired or rejected

Nothing in this file has been posted. Every draft is yours to send, edit or bin.

## Needs a human first

Below the draft threshold, fit unclear, low confidence, a warm relationship, or already in the outbound pipeline. Decide, then mark or reject.

### 8/10 · x · 1d · @ops_at_examplepay · ExamplePay
`d2f379453461` · https://x.com/ops_at_examplepay/status/000

> our current provider just dropped the corridor we do most volume on. anyone doing business payouts into china that isn't a nightmare to onboard?

**Problem:** Provider dropped their main corridor; needs a replacement business-payout rail to China  
**Why:** Fit yes: payment app (REM). Score 8: trigger event plus an explicit ask. Confidence 8: handle is the company's ops account.  
**Confidence:** 8 · **Fit:** yes · **Group:** REM
**Note:** already in outbound pipeline; hand context to that sequence

Mark: `python scripts/save_signal.py --status d2f379453461 replied` · `--status d2f379453461 dm_sent` · `--status d2f379453461 handed_to_outbound` · `--reject d2f379453461 --reason "..."`

## Ready: drafts to post

### 9/10 · reddit · 2d · lagos_importer
`ebbb3ad419d0` · https://www.reddit.com/r/Nigeria/comments/abc123/paying_a_supplier_in_guangzhou/

> Anyone know a provider that can pay my supplier in Guangzhou from naira? Bank keeps rejecting the transfer, need to pay a $4k invoice this week.

**Problem:** Needs to pay a USD 4k Chinese supplier invoice from NGN this week; bank transfer rejected  
**Why:** Fit yes: importer paying a Chinese supplier (CHN). Score 9: active purchase with a deadline this week. Confidence 7: handle only, no company, but post is explicit.  
**Confidence:** 7 · **Fit:** yes · **Group:** CHN

**Public reply (copy, then post it yourself):**

```
Banks reject most of these because the purpose code and the supplier's registered name don't match the invoice; fix that first and a second attempt often clears. If it still fails, USDT-funded CNY payout rails settle to ICBC or CCB in a day. I work on one, so biased, but happy to point you at what to check.
```

**DM:**

```
Saw your r/Nigeria post about the Guangzhou invoice. We pay Chinese supplier bank accounts from naira or USDT, all major banks, settled same day, with the supplier seeing your company name as sender. For a 4k invoice you'd be looking at roughly 0.5% plus a small fixed fee. Want the required fields list so you can check it against the invoice? Artur, co-founder
```

Mark: `python scripts/save_signal.py --status ebbb3ad419d0 replied` · `--status ebbb3ad419d0 dm_sent` · `--status ebbb3ad419d0 handed_to_outbound` · `--reject ebbb3ad419d0 --reason "..."`

### 6/10 · hn · 3d · devhandle
`5b8cb9c854aa` · https://news.ycombinator.com/item?id=000

> How do people handle paying overseas contractors from a Nigerian entity? Wise won't onboard us.

**Problem:** Paying overseas contractors from a Nigerian company; mainstream provider refused onboarding  
**Why:** Fit unclear-to-yes: Nigerian company with cross-border payouts (REM adjacent). Score 6: problem named, not yet searching. Confidence 6.  
**Confidence:** 6 · **Fit:** yes

**Public reply (copy, then post it yourself):**

```
Most of the mainstream providers geo-block Nigerian entities at KYB rather than at payment, so it is the entity, not the flow, that is failing. Local licensed PSPs that settle in USDT or USD tend to onboard, and a few expose an API. I work on one of those, so take the bias into account.
```

Mark: `python scripts/save_signal.py --status 5b8cb9c854aa replied` · `--reject 5b8cb9c854aa --reason "..."`
