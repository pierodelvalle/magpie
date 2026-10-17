import pytest

from tabs.models import Debate, Room, Round, Team


@pytest.fixture
def round1(db: None) -> Round:
    return Round.objects.create(number=1, motion='This House would test everything')


@pytest.fixture
def teams(db: None) -> list[Team]:
    return [Team.objects.create(name=f'Team {i}', institution='Uni') for i in range(1, 5)]


@pytest.fixture
def room(db: None) -> Room:
    return Room.objects.create(name='Room A')


@pytest.fixture
def debate(round1: Round, teams: list[Team], room: Room) -> Debate:
    return Debate.objects.create(round=round1, room=room, aff_team=teams[0], neg_team=teams[1])
