# Relationships and scarce resources

Most outbound systems treat a prospect as an address. Two prospects with identical company fit are not identical prospects if one shares sixteen connections with you and the other shares none, and an agent will treat them the same unless the difference is a number in a file.

## Mutual connections as a warmth score

`state/people.csv` carries `mutual_connections` (an integer) and `mutual_names` (optional, free text).

Warmth bands, configurable in the brief (`config/brief.md`):

| Mutuals | Warmth | What changes |
|---|---|---|
| 10+ | High | Worth a personal, human-written approach. Consider asking for an intro before any cold touch. |
| 4-9 | Medium | Reference the shared network if a specific name is known and it's genuinely relevant. |
| 1-3 | Low | Note it, don't lead with it. |
| 0 | Cold | Standard path. |

Warmth contributes to the reachability component of the score (`references/scoring.md`), and it decides who gets a scarce personal touch when there aren't enough to go round.

**A caution worth stating:** naming a mutual connection you don't actually know is transparent and it damages the relationship with the mutual, not just the prospect. Only name someone if you'd be comfortable with the prospect messaging them to ask about you. If in doubt, use the warmth to decide priority and don't mention it in the copy.

## Asking for an intro

At high warmth with a mutual you actually know, the intro beats the cold email by a wide enough margin that the cold email is usually the wrong move. The intro request goes to the mutual, not the prospect, and it should make saying yes easy: one line on why the prospect specifically, one line they can forward without editing.

That's an operator action, not an agent one. The agent's job is to surface it: flag the prospect, name the mutual, draft the forwardable line, and stop.

## Scarce resources need a number in a file

`state/budgets.yaml` holds anything limited, with a remaining count.

The clearest example is LinkedIn's cap on personalized connection notes per month. A run that knows two are left can spend them on the two highest-warmth tier 1 prospects. A run that doesn't know the limit exists burns them on whoever came up first, and finds out at the wrong moment.

This generalises past LinkedIn. Anything rationed goes in the file: daily sends, verification API credits, warm intro asks you're willing to make of one person per quarter, seats on a demo call. Agents allocate a budget well once told it exists, and are completely blind to one that lives only in the operator's head.

Decrement on use, in the same step as the action, not at the end of the run. A crashed run that already spent an invite must not spend it again.

## Reset handling

Each budget declares a reset period. At the start of a run, compare the last reset date to now and top up if the period has rolled over. Do it at the start, so a run never spends against a stale count.

## What the agent tracks vs what the operator does

The agent maintains the numbers, surfaces high-warmth prospects, drafts the messages, and records outcomes.

Sending a LinkedIn connection request, and asking a real person for an intro, stay manual. Not because they couldn't be automated, but because both spend social capital that belongs to the operator rather than to the system.
