import ast
import random
from collections import Counter
from pathlib import Path

import pytest

from engine import (
    InvalidHistoryError,
    MissingResultError,
    NoValidDrawError,
    PastBye,
    PastDebate,
    assign_sides,
    generate_draw,
)
from engine.types import Draw


def pair_sets(draw: Draw) -> set[frozenset[int]]:
    return {frozenset((p.aff, p.neg)) for p in draw.pairings}


def test_engine_does_not_import_django() -> None:
    for path in Path(__file__).parent.parent.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            assert not [n for n in names if n.split('.')[0] in ('django', 'tabs', 'rest_framework')]


class TestRoundOne:
    def test_even_field_pairs_everyone_with_no_bye(self) -> None:
        draw = generate_draw(range(1, 9), [], [], rng=random.Random(1))
        assert draw.bye is None
        assert sorted(t for p in draw.pairings for t in (p.aff, p.neg)) == list(range(1, 9))

    def test_odd_field_gives_exactly_one_bye(self) -> None:
        draw = generate_draw(range(1, 8), [], [], rng=random.Random(1))
        assert draw.bye is not None
        covered = [t for p in draw.pairings for t in (p.aff, p.neg)] + [draw.bye]
        assert sorted(covered) == list(range(1, 8))

    def test_same_rng_gives_the_same_draw(self) -> None:
        assert generate_draw(range(1, 11), [], [], rng=random.Random(5)) == generate_draw(
            range(1, 11), [], [], rng=random.Random(5)
        )

    def test_pairings_and_sides_are_random(self) -> None:
        draws = {generate_draw(range(1, 11), [], [], rng=random.Random(s)) for s in range(10)}
        assert len(draws) > 1
        assert len({p.aff for d in draws for p in d.pairings}) > 5

    def test_needs_at_least_two_teams(self) -> None:
        with pytest.raises(InvalidHistoryError):
            generate_draw([1], [], [])


class TestLaterRounds:
    def test_pairs_within_win_groups_top_half_against_bottom_half(self) -> None:
        # Winners 1,3,5,7 rank by points 100>90>80>70; losers 2,4,6,8 by 60>55>50>45.
        debates = [
            PastDebate(1, 1, 2, winner=1, aff_points=100, neg_points=60),
            PastDebate(1, 3, 4, winner=3, aff_points=90, neg_points=55),
            PastDebate(1, 5, 6, winner=5, aff_points=80, neg_points=50),
            PastDebate(1, 7, 8, winner=7, aff_points=70, neg_points=45),
        ]
        draw = generate_draw(range(1, 9), debates, [], rng=random.Random(0))
        assert pair_sets(draw) == {
            frozenset((1, 5)),
            frozenset((3, 7)),
            frozenset((2, 6)),
            frozenset((4, 8)),
        }

    def test_odd_group_sends_its_lowest_ranked_team_down(self) -> None:
        debates = [
            PastDebate(1, 1, 2, winner=1, aff_points=100, neg_points=60),
            PastDebate(1, 3, 4, winner=3, aff_points=90, neg_points=55),
            PastDebate(1, 5, 6, winner=5, aff_points=80, neg_points=50),
        ]
        draw = generate_draw(range(1, 7), debates, [], rng=random.Random(0))
        # Winners 1,3 meet; 5 drops into the losers' group [5,2,4,6] -> 5 v 4, 2 v 6.
        assert pair_sets(draw) == {frozenset((1, 3)), frozenset((5, 4)), frozenset((2, 6))}

    def test_pairings_come_out_best_bracket_first(self) -> None:
        debates = [
            PastDebate(1, 1, 2, winner=1, aff_points=100, neg_points=60),
            PastDebate(1, 3, 4, winner=3, aff_points=90, neg_points=55),
        ]
        draw = generate_draw(range(1, 5), debates, [], rng=random.Random(0))
        assert {draw.pairings[0].aff, draw.pairings[0].neg} == {1, 3}

    def test_rematch_is_avoided_by_swapping_with_the_nearest_valid_team(self) -> None:
        debates = [
            PastDebate(1, 1, 2, winner=1),
            PastDebate(1, 3, 4, winner=3),
            PastDebate(2, 1, 3, winner=1),
            PastDebate(2, 2, 4, winner=2),
        ]
        # Ideal round 3 is 1 v 2 (a rematch), so it must become 1 v 4 and 2 v 3.
        draw = generate_draw([1, 2, 3, 4], debates, [], rng=random.Random(0))
        assert pair_sets(draw) == {frozenset((1, 4)), frozenset((2, 3))}

    def test_forfeit_still_blocks_a_rematch(self) -> None:
        debates = [
            PastDebate(1, 1, 2, winner=1, forfeit=True),
            PastDebate(1, 3, 4, winner=3),
        ]
        draw = generate_draw([1, 2, 3, 4], debates, [], rng=random.Random(0))
        assert frozenset((1, 2)) not in pair_sets(draw)

    def test_no_draw_when_every_pairing_would_be_a_rematch(self) -> None:
        debates = [
            PastDebate(1, 1, 2, winner=1),
            PastDebate(1, 3, 4, winner=3),
            PastDebate(2, 1, 3, winner=1),
            PastDebate(2, 2, 4, winner=2),
            PastDebate(3, 1, 4, winner=1),
            PastDebate(3, 2, 3, winner=2),
        ]
        with pytest.raises(NoValidDrawError):
            generate_draw([1, 2, 3, 4], debates, [])

    def test_missing_result_blocks_the_draw(self) -> None:
        with pytest.raises(MissingResultError):
            generate_draw([1, 2], [PastDebate(1, 1, 2, winner=None)], [])


class TestByes:
    def history_for_five(self) -> list[PastDebate]:
        # Round 1: 1>2, 3>4, team 5 had the bye. Points give the rank order 1,3,2,4 (5 has a win).
        return [
            PastDebate(1, 1, 2, winner=1, aff_points=100, neg_points=60),
            PastDebate(1, 3, 4, winner=3, aff_points=90, neg_points=50),
        ]

    def test_bye_goes_to_the_lowest_ranked_team_without_one(self) -> None:
        draw = generate_draw(
            range(1, 6), self.history_for_five(), [PastBye(1, 5)], rng=random.Random(0)
        )
        # Ranking: 1 (1w,100), 3 (1w,90), 5 (1w,0), 2 (0w,60), 4 (0w,50). Lowest is 4.
        assert draw.bye == 4

    def test_a_team_that_had_a_bye_is_skipped(self) -> None:
        debates = self.history_for_five()
        draw = generate_draw(range(1, 6), debates, [PastBye(1, 4)], rng=random.Random(0))
        # 4 already had a bye, so the lowest-ranked team without one gets it instead.
        assert draw.bye != 4

    def test_no_second_bye_while_another_team_has_none(self) -> None:
        # Four rounds of five teams: every team should have exactly one bye after five rounds,
        # and nobody gets a second before then. Played out with random results.
        rng = random.Random(3)
        teams = list(range(1, 6))
        debates: list[PastDebate] = []
        byes: list[PastBye] = []
        for rnd in range(1, 5):
            draw = generate_draw(teams, debates, byes, rng=rng)
            assert draw.bye is not None
            assert draw.bye not in {b.team for b in byes}
            byes.append(PastBye(rnd, draw.bye))
            for p in draw.pairings:
                debates.append(PastDebate(rnd, p.aff, p.neg, winner=rng.choice((p.aff, p.neg))))

    def test_bye_moves_on_when_the_natural_choice_would_force_a_rematch(self) -> None:
        # Round 4 of five teams. Teams 1 and 3 are the only ones without a bye, but sitting
        # either out leaves the other four with only rematches, so no rematch beats the bye
        # rule and team 2 (who already had one) must sit out instead.
        d = PastDebate
        debates = [
            d(1, aff=4, neg=3, winner=3),
            d(1, aff=2, neg=1, winner=1),
            d(2, aff=1, neg=5, winner=5),
            d(2, aff=3, neg=2, winner=3),
            d(3, aff=5, neg=3, winner=3),
            d(3, aff=1, neg=4, winner=4),
        ]
        byes = [PastBye(1, 5), PastBye(2, 4), PastBye(3, 2)]
        draw = generate_draw(range(1, 6), debates, byes, rng=random.Random(0))
        assert draw.bye == 2
        played = {frozenset((x.aff, x.neg)) for x in debates}
        assert not pair_sets(draw) & played
        assert len(draw.pairings) == 2


class TestSides:
    def test_team_with_fewer_aff_rounds_gets_aff(self) -> None:
        aff, neg = Counter({1: 2}), Counter({2: 2})
        for seed in range(10):
            p = assign_sides(1, 2, aff, neg, random.Random(seed))
            assert (p.aff, p.neg) == (2, 1)

    def test_equal_counts_are_settled_at_random(self) -> None:
        sides = {assign_sides(1, 2, Counter(), Counter(), random.Random(s)).aff for s in range(20)}
        assert sides == {1, 2}

    def test_generate_draw_balances_sides_for_each_pair(self) -> None:
        # Round 1: 1 (aff) beat 2, 3 (neg) beat 4 (aff). Round 2 pairs winners 1 v 3 and
        # losers 2 v 4. 1 has been aff and 3 neg, so 3 gets aff; 2 has been neg and 4 aff,
        # so 2 gets aff.
        debates = [
            PastDebate(1, aff=1, neg=2, winner=1),
            PastDebate(1, aff=4, neg=3, winner=3),
        ]
        for seed in range(10):
            draw = generate_draw([1, 2, 3, 4], debates, [], rng=random.Random(seed))
            assert {(p.aff, p.neg) for p in draw.pairings} == {(3, 1), (2, 4)}

    def test_side_balance_never_changes_who_plays_whom(self) -> None:
        debates = [
            PastDebate(1, 1, 2, winner=1, aff_points=100, neg_points=60),
            PastDebate(1, 3, 4, winner=3, aff_points=90, neg_points=55),
        ]
        sets = {
            frozenset(pair_sets(generate_draw(range(1, 5), debates, [], rng=random.Random(s))))
            for s in range(10)
        }
        assert len(sets) == 1
