"""Plain data types for the draw engine. No Django imports: the engine must run in a notebook."""

from dataclasses import dataclass


class DrawError(Exception):
    """Base class for everything the engine raises on purpose."""


class InvalidHistoryError(DrawError, ValueError):
    """The teams, debates or byes passed in are inconsistent."""


class MissingResultError(InvalidHistoryError):
    """A past debate has no winner recorded yet."""


class NoValidDrawError(DrawError):
    """No pairing exists that avoids every rematch (e.g. too many rounds for the team count)."""


@dataclass(frozen=True)
class PastDebate:
    round: int
    aff: int
    neg: int
    # None means the result has not been entered, which the engine rejects.
    winner: int | None
    aff_points: float = 0.0
    neg_points: float = 0.0
    forfeit: bool = False


@dataclass(frozen=True)
class PastBye:
    round: int
    team: int


@dataclass(frozen=True)
class Pairing:
    aff: int
    neg: int


@dataclass(frozen=True)
class Draw:
    # Ordered best bracket first.
    pairings: tuple[Pairing, ...]
    bye: int | None


@dataclass(frozen=True)
class Standing:
    team: int
    rank: int  # 1 is best
    wins: int
    speaker_points: float
    opponent_wins: int
    tiebreak: float  # fixed per tournament seed, only used as the last tiebreak
