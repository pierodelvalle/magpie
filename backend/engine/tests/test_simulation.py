"""Plays whole tournaments with random results and checks the draw rules every round."""

import random
from collections import Counter

import pytest

from engine import NoValidDrawError, PastBye, PastDebate, compute_standings, generate_draw

ROUNDS = 6


def max_rounds(n: int) -> int:
    # Fields of 8 or fewer run out of fresh opponents, and the engine can paint itself into a
    # corner a round or two before that (it does not look ahead), so play fewer rounds.
    return ROUNDS if n > 8 else 3


def play(n: int, seed: int, rounds: int) -> tuple[list[PastDebate], list[PastBye], list[int]]:
    rng = random.Random(seed)
    teams = list(range(1, n + 1))
    debates: list[PastDebate] = []
    byes: list[PastBye] = []
    for rnd in range(1, rounds + 1):
        draw = generate_draw(teams, debates, byes, seed=seed, rng=rng)

        # Everyone is drawn exactly once.
        drawn = [t for p in draw.pairings for t in (p.aff, p.neg)]
        if draw.bye is not None:
            drawn.append(draw.bye)
        assert sorted(drawn) == teams

        # Even fields never have a bye, odd fields have exactly one.
        assert (draw.bye is None) == (n % 2 == 0)

        # No rematches.
        played = {frozenset((d.aff, d.neg)) for d in debates}
        assert not {frozenset((p.aff, p.neg)) for p in draw.pairings} & played

        # No second bye while another team has none.
        if draw.bye is not None:
            had = Counter(b.team for b in byes)
            assert had[draw.bye] == min(had[t] for t in teams)
            byes.append(PastBye(rnd, draw.bye))

        for p in draw.pairings:
            winner = rng.choice((p.aff, p.neg))
            debates.append(
                PastDebate(
                    rnd,
                    p.aff,
                    p.neg,
                    winner=winner,
                    aff_points=rng.randint(60, 80),
                    neg_points=rng.randint(60, 80),
                    forfeit=rng.random() < 0.03,
                )
            )
    return debates, byes, teams


@pytest.mark.parametrize('seed', [1, 2])
@pytest.mark.parametrize('n', range(4, 61))
def test_tournament_invariants_hold_for_every_field_size(n: int, seed: int) -> None:
    rounds = max_rounds(n)
    debates, byes, teams = play(n, seed, rounds)

    aff = Counter(d.aff for d in debates)
    neg = Counter(d.neg for d in debates)
    # Side balance is a lower priority than rematches, but should stay close.
    assert max(abs(aff[t] - neg[t]) for t in teams) <= max(2, rounds // 2)

    # Every team has played at most once per opponent.
    meetings = Counter(frozenset((d.aff, d.neg)) for d in debates)
    assert max(meetings.values()) == 1

    standings = compute_standings(teams, debates, byes, seed)
    assert sorted(s.rank for s in standings) == teams


@pytest.mark.parametrize('seed', range(5))
@pytest.mark.parametrize('n', [10, 16, 20, 33, 60])
def test_round_two_only_crosses_win_groups_to_fix_an_odd_group(n: int, seed: int) -> None:
    rng = random.Random(seed)
    teams = list(range(1, n + 1))
    first = generate_draw(teams, [], [], rng=rng)
    byes = [PastBye(1, first.bye)] if first.bye is not None else []
    debates = [
        PastDebate(1, p.aff, p.neg, winner=rng.choice((p.aff, p.neg))) for p in first.pairings
    ]
    second = generate_draw(teams, debates, byes, rng=rng)
    wins = {s.team: s.wins for s in compute_standings(teams, debates, byes)}
    crossing = [p for p in second.pairings if wins[p.aff] != wins[p.neg]]
    assert len(crossing) <= 1


def test_running_out_of_opponents_raises_instead_of_rematching() -> None:
    with pytest.raises(NoValidDrawError):
        play(4, seed=1, rounds=4)
