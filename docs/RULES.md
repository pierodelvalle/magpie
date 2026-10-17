# Magpie: Tournament Rules (Phase 0)

Status: **proposed defaults, awaiting confirmation.** The draw engine will implement exactly what is written here, so change anything you disagree with before Phase 3.

## Stack
Django 5.2 + Django REST Framework, Postgres 17, Vue 3 + TypeScript + Vite (Pinia, Vue Router, Vitest), all run through Docker Compose. Django admin handles data entry in v1.

## Format
- Two teams per debate: **aff** and **neg**.
- Swiss-style preliminary rounds, then manually created elimination rounds.
- A debate is won by exactly one team. No draws.

## Standings (and tiebreak order)
1. Wins
2. Total speaker points
3. Opponent wins (sum of the wins of every opponent faced)
4. Random draw, fixed once per tournament so results stay stable

A bye counts as a win. It adds no speaker points and no opponent.

## Forfeits
- The forfeiting team gets a loss. The other team gets a win.
- Speaker points are not required for a forfeit and count as 0 in the totals.
- A forfeit still counts as a debate that was played, so the two teams cannot be paired again.

## Byes
- With an odd number of teams, one team gets a bye each round.
- The bye goes to the lowest-ranked team that has not yet had one.
- No team gets a second bye while another team has had none.

## Round 1
- Random pairing, with sides assigned randomly.

## Rounds 2 and later
Pairing proceeds in this priority order, and a higher rule is never broken to satisfy a lower one:

1. **No rematches.** Two teams never meet twice in the preliminary rounds.
2. **Same win count.** Teams are grouped by wins, highest first.
3. **Pairing within a group.** Rank the group by the standings tiebreaks, then pair top half against bottom half (1 v n/2+1, 2 v n/2+2, and so on).
4. **Odd groups.** The lowest-ranked team in an odd group is pulled down into the next group. If that is the last group, the bye rule applies.
5. **Side balance.** Each pair is assigned sides so that the team with fewer rounds on a given side gets it. If both teams are equal, assign randomly. Side balance can be broken to avoid a rematch, never the other way round.
6. **Rematch conflicts.** If a pairing would be a rematch, swap with the nearest valid team in the same group first, then across the adjacent group.

## Rooms
Rooms are assigned by hand or auto-assigned in order. There is no room-quality logic in v1.

## Adjudicators
Assigned by hand in v1. There are no conflicts, ratings or roles. A debate can have a panel of any size.

## How the draw engine reads these rules
Implemented in `backend/engine/` (no Django, usable from a notebook). Where the rules were open to interpretation:
- **Opponent wins** uses each opponent's total wins, byes included.
- **Bye vs. rematch:** no rematch outranks the bye rule. If the natural bye team would leave the rest with only rematches, the next candidate sits out, which can mean a second bye before every team has had one.
- **Side balance** only chooses sides within a pair. It never changes who plays whom.
- **No look-ahead:** the engine pairs one round at a time. Fields of 8 or fewer teams can run out of fresh opponents before the last rounds and get a `NoValidDrawError` instead of a rematch. Fields of 9 or more completed 6 rounds in every simulated tournament.
- A past debate with no result stops the draw (`MissingResultError`).

## Open questions
- Do you want speaker points per team only, or per individual speaker later?
- Should the number of preliminary rounds be fixed per tournament or changeable?
- Is "opponent wins" the right third tiebreak for your tournaments, or do you prefer head-to-head?
