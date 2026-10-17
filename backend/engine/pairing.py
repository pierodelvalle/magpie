"""Swiss draw generation, implementing docs/RULES.md.

Priority order, where a higher rule is never broken for a lower one:
no rematches > same win count > top half v bottom half > odd groups pull down > side balance.
Sides are assigned after the pairs are fixed, so side balance can never cause a rematch.
"""

import random
from collections import Counter
from collections.abc import Sequence

from .standings import compute_standings
from .types import (
    Draw,
    InvalidHistoryError,
    NoValidDrawError,
    Pairing,
    PastBye,
    PastDebate,
    Standing,
)

# Backtracking guard. Real tournaments need a handful of nodes; this only trips when the
# history leaves no valid draw and the search would otherwise run for ages.
MAX_SEARCH_NODES = 50_000


def generate_draw(
    teams: Sequence[int],
    debates: Sequence[PastDebate],
    byes: Sequence[PastBye],
    *,
    seed: int = 0,
    rng: random.Random | None = None,
) -> Draw:
    """Pair the next round.

    `seed` fixes the random final tiebreak for the whole tournament; `rng` drives the
    randomness inside a single draw (round 1 pairings, random sides). Pass a seeded `rng`
    for a reproducible draw.
    """
    if len(teams) < 2:
        raise InvalidHistoryError('Need at least two teams to draw a round.')
    rng = rng or random.Random()

    standings = compute_standings(teams, debates, byes, seed)
    if not debates and not byes:
        return _first_round(teams, rng)

    ranked = [s.team for s in standings]
    played = {frozenset((d.aff, d.neg)) for d in debates}

    pairs: list[tuple[int, int]] | None = None
    bye: int | None = None
    for bye in _bye_candidates(standings, byes, odd=len(teams) % 2 == 1):
        pool = [t for t in ranked if t != bye]
        pairs = _pair_pool(pool, standings, played)
        if pairs is not None:
            break
    if pairs is None:
        raise NoValidDrawError('Every pairing would repeat an earlier debate.')

    aff_counts = Counter(d.aff for d in debates)
    neg_counts = Counter(d.neg for d in debates)
    return Draw(
        pairings=tuple(assign_sides(a, b, aff_counts, neg_counts, rng) for a, b in pairs),
        bye=bye,
    )


def _first_round(teams: Sequence[int], rng: random.Random) -> Draw:
    order = list(teams)
    rng.shuffle(order)
    bye = order.pop() if len(order) % 2 else None
    pairings = []
    for a, b in zip(order[::2], order[1::2], strict=True):
        pairings.append(Pairing(aff=a, neg=b) if rng.random() < 0.5 else Pairing(aff=b, neg=a))
    return Draw(pairings=tuple(pairings), bye=bye)


def _bye_candidates(
    standings: Sequence[Standing], byes: Sequence[PastBye], *, odd: bool
) -> list[int | None]:
    """Teams in the order they should be tried for the bye.

    Lowest-ranked first among the teams with the fewest byes, so nobody gets a second bye
    while another team has none. Later candidates are only used if an earlier one leaves
    the rest of the field with no rematch-free draw.
    """
    if not odd:
        return [None]
    counts = Counter(b.team for b in byes)
    ordered = sorted(standings, key=lambda s: (counts[s.team], -s.rank))
    return [s.team for s in ordered]


def _build_groups(pool: Sequence[int], wins: dict[int, int]) -> list[list[int]]:
    """Group by win count, highest first; an odd group sends its lowest-ranked team down."""
    groups: list[list[int]] = []
    carry: int | None = None
    for w in sorted({wins[t] for t in pool}, reverse=True):
        group = [t for t in pool if wins[t] == w]  # pool is already in rank order
        if carry is not None:
            group.insert(0, carry)
            carry = None
        if len(group) % 2:
            carry = group.pop()
        if group:
            groups.append(group)
    # The pool has an even size, so the last group can never be left with a carry.
    assert carry is None
    return groups


def _pair_pool(
    pool: Sequence[int], standings: Sequence[Standing], played: set[frozenset[int]]
) -> list[tuple[int, int]] | None:
    """Pair an even pool with no rematches, staying as close to the ideal draw as possible.

    Takes the highest-ranked unpaired team and tries opponents from most to least preferred:
    its top-half/bottom-half partner, then the nearest valid team in its group, then teams in
    the following groups. Backtracks if that leaves someone with no valid opponent.
    """
    rank = {s.team: s.rank for s in standings}
    wins = {s.team: s.wins for s in standings}
    groups = _build_groups(pool, wins)
    group_of = {t: gi for gi, g in enumerate(groups) for t in g}
    pos_in_group = {t: i for g in groups for i, t in enumerate(g)}

    def preference(t: int, u: int) -> tuple[int, int, int, int]:
        gi = group_of[t]
        if group_of[u] != gi:
            return (1, group_of[u] - gi, 0, rank[u])
        half = len(groups[gi]) // 2
        ideal = pos_in_group[t] + half if pos_in_group[t] < half else pos_in_group[t] - half
        same_half = (pos_in_group[t] < half) == (pos_in_group[u] < half)
        return (0, int(same_half), abs(pos_in_group[u] - ideal), rank[u])

    nodes = 0

    def solve(remaining: list[int]) -> list[tuple[int, int]] | None:
        nonlocal nodes
        if not remaining:
            return []
        nodes += 1
        if nodes > MAX_SEARCH_NODES:
            return None
        t, rest = remaining[0], remaining[1:]
        options = [u for u in rest if frozenset((t, u)) not in played]
        options.sort(key=lambda u: preference(t, u))
        for u in options:
            tail = solve([x for x in rest if x != u])
            if tail is not None:
                return [(t, u), *tail]
        return None

    return solve(list(pool))


def assign_sides(
    a: int,
    b: int,
    aff_counts: Counter[int],
    neg_counts: Counter[int],
    rng: random.Random,
) -> Pairing:
    """Give aff to the team that has had it less; a tie is settled at random."""
    need_a = neg_counts[a] - aff_counts[a]
    need_b = neg_counts[b] - aff_counts[b]
    if need_a == need_b:
        return Pairing(aff=a, neg=b) if rng.random() < 0.5 else Pairing(aff=b, neg=a)
    return Pairing(aff=a, neg=b) if need_a > need_b else Pairing(aff=b, neg=a)
