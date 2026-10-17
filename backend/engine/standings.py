"""Standings from history, in the tiebreak order fixed in docs/RULES.md.

1. wins  2. total speaker points  3. opponent wins  4. random draw fixed per tournament seed.
"""

import random
from collections.abc import Sequence

from .types import InvalidHistoryError, MissingResultError, PastBye, PastDebate, Standing


def tiebreak_key(seed: int, team: int) -> float:
    """Stable random number for a team, so the final tiebreak never changes between rounds."""
    return random.Random(f'{seed}:{team}').random()


def compute_standings(
    teams: Sequence[int],
    debates: Sequence[PastDebate],
    byes: Sequence[PastBye],
    seed: int = 0,
) -> list[Standing]:
    known = set(teams)
    if len(known) != len(teams):
        raise InvalidHistoryError('Duplicate team ids.')

    wins = dict.fromkeys(teams, 0)
    points = dict.fromkeys(teams, 0.0)

    for debate in debates:
        if debate.aff not in known or debate.neg not in known:
            raise InvalidHistoryError(f'Round {debate.round} has a team that is not entered.')
        if debate.aff == debate.neg:
            raise InvalidHistoryError(f'Round {debate.round} has a team debating itself.')
        if debate.winner is None:
            raise MissingResultError(
                f'Round {debate.round}: {debate.aff} v {debate.neg} has no result.'
            )
        if debate.winner not in (debate.aff, debate.neg):
            raise InvalidHistoryError(
                f'Round {debate.round}: winner {debate.winner} was not in the debate.'
            )
        wins[debate.winner] += 1
        # A forfeit counts 0 speaker points whatever was entered.
        if not debate.forfeit:
            points[debate.aff] += debate.aff_points
            points[debate.neg] += debate.neg_points

    for bye in byes:
        if bye.team not in known:
            raise InvalidHistoryError(f'Round {bye.round} bye is for a team that is not entered.')
        # A bye is a win with no speaker points and no opponent.
        wins[bye.team] += 1

    opponent_wins = dict.fromkeys(teams, 0)
    for debate in debates:
        opponent_wins[debate.aff] += wins[debate.neg]
        opponent_wins[debate.neg] += wins[debate.aff]

    tiebreaks = {team: tiebreak_key(seed, team) for team in teams}
    ordered = sorted(
        teams,
        key=lambda t: (-wins[t], -points[t], -opponent_wins[t], tiebreaks[t]),
    )
    return [
        Standing(
            team=team,
            rank=rank,
            wins=wins[team],
            speaker_points=points[team],
            opponent_wins=opponent_wins[team],
            tiebreak=tiebreaks[team],
        )
        for rank, team in enumerate(ordered, start=1)
    ]
