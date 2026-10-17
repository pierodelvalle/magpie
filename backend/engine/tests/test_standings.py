import pytest

from engine import (
    InvalidHistoryError,
    MissingResultError,
    PastBye,
    PastDebate,
    Standing,
    compute_standings,
)
from engine.standings import tiebreak_key


def by_team(standings: list[Standing]) -> dict[int, Standing]:
    return {s.team: s for s in standings}


def test_wins_and_speaker_points_are_summed() -> None:
    debates = [
        PastDebate(1, aff=1, neg=2, winner=1, aff_points=75, neg_points=70),
        PastDebate(2, aff=2, neg=1, winner=1, aff_points=72, neg_points=76),
    ]
    s = by_team(compute_standings([1, 2], debates, []))
    assert (s[1].wins, s[1].speaker_points) == (2, 151)
    assert (s[2].wins, s[2].speaker_points) == (0, 142)


def test_bye_counts_as_a_win_with_no_points_or_opponent() -> None:
    s = by_team(compute_standings([1, 2, 3], [PastDebate(1, 1, 2, 1, 70, 60)], [PastBye(1, 3)]))
    assert s[3].wins == 1
    assert s[3].speaker_points == 0
    assert s[3].opponent_wins == 0


def test_forfeit_is_a_loss_and_points_count_as_zero() -> None:
    forfeit = PastDebate(1, aff=1, neg=2, winner=1, aff_points=80, neg_points=10, forfeit=True)
    s = by_team(compute_standings([1, 2], [forfeit], []))
    assert (s[1].wins, s[2].wins) == (1, 0)
    assert s[1].speaker_points == 0
    assert s[2].speaker_points == 0


def test_opponent_wins_sums_the_wins_of_every_opponent() -> None:
    debates = [
        PastDebate(1, 1, 2, winner=1),
        PastDebate(1, 3, 4, winner=3),
        PastDebate(2, 1, 3, winner=1),
        PastDebate(2, 2, 4, winner=2),
    ]
    s = by_team(compute_standings([1, 2, 3, 4], debates, []))
    # wins: 1->2, 3->1, 2->1, 4->0
    assert s[1].opponent_wins == 1 + 1  # faced 2 and 3
    assert s[4].opponent_wins == 1 + 1  # faced 3 and 2
    assert s[2].opponent_wins == 2 + 0
    assert s[3].opponent_wins == 0 + 2


def test_order_is_wins_then_points_then_opponent_wins() -> None:
    debates = [
        PastDebate(1, 1, 2, winner=1, aff_points=70, neg_points=60),
        PastDebate(1, 3, 4, winner=3, aff_points=80, neg_points=60),
    ]
    order = [s.team for s in compute_standings([1, 2, 3, 4], debates, [])]
    assert order[:2] == [3, 1]  # equal wins, 3 has more speaker points


def test_opponent_wins_break_a_tie_on_wins_and_points() -> None:
    # 1 and 3 both 1-1 on 100 points. 1 lost to the strong team 2 and beat 4; 3 lost to the
    # weak team 4 and beat 5.
    debates = [
        PastDebate(1, 1, 2, winner=2, aff_points=50, neg_points=50),
        PastDebate(2, 1, 4, winner=1, aff_points=50, neg_points=50),
        PastDebate(1, 3, 4, winner=4, aff_points=50, neg_points=50),
        PastDebate(2, 3, 5, winner=3, aff_points=50, neg_points=50),
        PastDebate(3, 2, 5, winner=2, aff_points=0, neg_points=0),
    ]
    s = by_team(compute_standings([1, 2, 3, 4, 5], debates, []))
    assert s[1].wins == s[3].wins and s[1].speaker_points == s[3].speaker_points
    assert s[1].opponent_wins > s[3].opponent_wins
    assert s[1].rank < s[3].rank


def test_random_final_tiebreak_is_stable_for_a_seed() -> None:
    first = [s.team for s in compute_standings(list(range(1, 11)), [], [], seed=7)]
    again = [s.team for s in compute_standings(list(range(1, 11)), [], [], seed=7)]
    assert first == again


def test_random_final_tiebreak_changes_with_the_seed() -> None:
    orders = {
        tuple(s.team for s in compute_standings(list(range(1, 11)), [], [], seed=seed))
        for seed in range(5)
    }
    assert len(orders) > 1


def test_tiebreak_key_does_not_depend_on_other_teams() -> None:
    assert tiebreak_key(3, 5) == tiebreak_key(3, 5)
    assert tiebreak_key(3, 5) != tiebreak_key(4, 5)


def test_ranks_start_at_one_and_are_unique() -> None:
    ranks = [s.rank for s in compute_standings([1, 2, 3], [], [])]
    assert sorted(ranks) == [1, 2, 3]


def test_missing_result_is_rejected() -> None:
    with pytest.raises(MissingResultError):
        compute_standings([1, 2], [PastDebate(1, 1, 2, winner=None)], [])


@pytest.mark.parametrize(
    ('teams', 'debates', 'byes'),
    [
        ([1, 1], [], []),
        ([1, 2], [PastDebate(1, 1, 9, winner=1)], []),
        ([1, 2], [PastDebate(1, 1, 1, winner=1)], []),
        ([1, 2, 3], [PastDebate(1, 1, 2, winner=3)], []),
        ([1, 2], [], [PastBye(1, 9)]),
    ],
)
def test_inconsistent_history_is_rejected(
    teams: list[int], debates: list[PastDebate], byes: list[PastBye]
) -> None:
    with pytest.raises(InvalidHistoryError):
        compute_standings(teams, debates, byes)
