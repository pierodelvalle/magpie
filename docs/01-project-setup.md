# Magpie: MVP Build Plan

A minimal, Tabbycat-style debate tabulation app: a Swiss-style, 2-team format with public draws and standings.

## Data model (7 tables)

| Table | Fields |
|---|---|
| **Team** | name, institution (text) |
| **Adjudicator** | name, institution (text) |
| **Room** | name |
| **Round** | number, motion (text), released (bool) |
| **Debate** | round, room, aff team, neg team |
| **DebateAdjudicator** | debate, adjudicator (add `role` later) |
| **Result** | debate, winner (team), speaker points per team, forfeit (bool) |

Plus a **Bye** record (round, team) for odd team counts.

Derived from history, not stored: records, rematch history, side counts, opponent strength.

### Deliberately left out of v1
- Tournament table (one tournament per install)
- Institution table (plain text instead)
- Individual speakers (team-level scoring only)
- Conflicts and adjudicator ratings
- Break categories and automated elimination rounds
- Multiple formats (e.g. BP)
- Roles and permissions beyond a single admin

## Phase 0: Decisions (before any code)
1. **Pick the stack.** Recommended: Django + Postgres (+ HTMX), or Next.js + Postgres if the team prefers TypeScript.
2. **Fix the rules** in a short `RULES.md`:
   - sides (aff/neg)
   - pairing method (top half v bottom half, or adjacent)
   - bye rules
   - tiebreak order (wins, then speaker points, then opponent wins)
   - how a forfeit counts

## Phase 1: Foundation
3. Scaffold the project, set up the database, and add linting, a type checker and a test runner.
4. Create the 7 tables with migrations. Include aff/neg on `Debate`, the bye record, and the forfeit flag on `Result`.
5. Add one admin login. Everything outside the admin is read-only for the public.

**Check:** all 7 record types can be created by hand.

## Phase 2: Data entry
6. CRUD screens for teams, adjudicators and rooms (use the framework's admin if it has one).
7. CSV import for teams and adjudicators, with error reporting for bad rows.

**Check:** a realistic 20-team sample loads.

## Phase 3: Draw engine
The core of the project. Build it as a pure module with no database access.

8. Pure functions: input is teams plus past results, output is a list of pairings.
9. Round 1: random pairing, with a bye if the count is odd.
10. Later rounds: group by wins, pair within groups, and handle odd groups by moving a team to an adjacent group.
11. Rematch avoidance first, then side balancing as a lower-priority rule.
12. Unit tests for each rule: odd counts, no repeated byes, no rematches, balanced sides. Add a simulation test that runs 6 rounds of random results across many team counts and asserts the invariants.

**Check:** tests pass for team counts from 4 to 60.

## Phase 4: Running a round
13. A "Generate draw" action that calls the engine and saves a draft `Round` with its `Debate` rows.
14. A screen to edit the draft: swap teams, change rooms, auto-assign rooms.
15. Manual adjudicator assignment per debate through `DebateAdjudicator`.
16. A "Release" button that sets `released = true`.

**Check:** a full round can be run from draw to release.

## Phase 5: Results and standings
17. Ballot entry: pick the winner and optionally speaker points, with validation.
18. A list of debates still missing results.
19. Standings computed from results: wins, speaker points, opponent wins, using the tiebreak order from step 2.

**Check:** standings match a hand-calculated example.

## Phase 6: Public pages
20. Public pages for the released draw, motion and standings, mobile-friendly.
21. A results view per round.

## Phase 7: Finish
22. Elimination rounds: take the top N from the standings and create the rounds manually with the existing draw screens.
23. Run a mock tournament with test data. Fix what breaks.
24. Deploy, set up backups, and write a short tab director guide.

## Risk ordering
Build **Phase 3 first** if possible, even before the UI. If the pairing logic is wrong nothing else matters, and it is the part most likely to need rework.
