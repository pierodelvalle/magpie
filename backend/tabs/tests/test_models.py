from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from tabs.models import (
    Adjudicator,
    Bye,
    Debate,
    DebateAdjudicator,
    Result,
    Room,
    Round,
    Team,
)

pytestmark = pytest.mark.django_db


def test_all_record_types_can_be_created(debate: Debate, teams: list[Team], round1: Round) -> None:
    adj = Adjudicator.objects.create(name='Judge Judy')
    DebateAdjudicator.objects.create(debate=debate, adjudicator=adj)
    Result.objects.create(
        debate=debate,
        winner=teams[0],
        aff_speaker_points=Decimal('75.5'),
        neg_speaker_points=Decimal(74),
    )
    Bye.objects.create(round=round1, team=teams[2])

    assert Debate.objects.get().aff_team == teams[0]
    assert debate.result.winner == teams[0]
    assert debate.adjudicators.get().adjudicator == adj
    assert round1.byes.get().team == teams[2]


def test_str_representations(debate: Debate, teams: list[Team], round1: Round) -> None:
    assert str(teams[0]) == 'Team 1'
    assert str(round1) == 'Round 1'
    assert str(debate) == 'Round 1: Team 1 (aff) v Team 2 (neg)'


def test_team_name_unique(teams: list[Team]) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Team.objects.create(name='Team 1')


def test_round_number_unique(round1: Round) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Round.objects.create(number=1)


def test_round_defaults_to_unreleased(round1: Round) -> None:
    assert round1.released is False


class TestDebate:
    def test_team_cannot_debate_itself(self, round1: Round, teams: list[Team]) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            Debate.objects.create(round=round1, aff_team=teams[0], neg_team=teams[0])

    def test_team_cannot_repeat_on_aff_in_a_round(
        self, debate: Debate, round1: Round, teams: list[Team]
    ) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            Debate.objects.create(round=round1, aff_team=teams[0], neg_team=teams[2])

    def test_team_cannot_repeat_on_neg_in_a_round(
        self, debate: Debate, round1: Round, teams: list[Team]
    ) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            Debate.objects.create(round=round1, aff_team=teams[2], neg_team=teams[1])

    def test_team_cannot_switch_sides_within_a_round(
        self, debate: Debate, round1: Round, teams: list[Team]
    ) -> None:
        clash = Debate(round=round1, aff_team=teams[1], neg_team=teams[2])
        with pytest.raises(ValidationError):
            clash.full_clean()

    def test_valid_second_debate_passes_clean(
        self, debate: Debate, round1: Round, teams: list[Team]
    ) -> None:
        Debate(round=round1, aff_team=teams[2], neg_team=teams[3]).full_clean()

    def test_editing_a_debate_does_not_clash_with_itself(self, debate: Debate) -> None:
        debate.full_clean()

    def test_room_cannot_be_reused_in_a_round(
        self, debate: Debate, round1: Round, teams: list[Team], room: Room
    ) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            Debate.objects.create(round=round1, room=room, aff_team=teams[2], neg_team=teams[3])

    def test_room_is_optional_and_unassigned_debates_can_coexist(
        self, round1: Round, teams: list[Team]
    ) -> None:
        Debate.objects.create(round=round1, aff_team=teams[0], neg_team=teams[1])
        Debate.objects.create(round=round1, aff_team=teams[2], neg_team=teams[3])
        assert Debate.objects.filter(room__isnull=True).count() == 2

    def test_same_teams_can_meet_in_different_rounds_at_model_level(
        self, debate: Debate, teams: list[Team]
    ) -> None:
        # Rematch avoidance is the draw engine's job, not a database rule.
        round2 = Round.objects.create(number=2)
        Debate.objects.create(round=round2, aff_team=teams[1], neg_team=teams[0])

    def test_team_with_debate_cannot_be_deleted(self, debate: Debate, teams: list[Team]) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            teams[0].delete()

    def test_deleting_a_round_removes_its_debates(self, debate: Debate, round1: Round) -> None:
        round1.delete()
        assert Debate.objects.count() == 0


class TestDebateAdjudicator:
    def test_adjudicator_once_per_debate(self, debate: Debate) -> None:
        adj = Adjudicator.objects.create(name='Judge')
        DebateAdjudicator.objects.create(debate=debate, adjudicator=adj)
        with pytest.raises(IntegrityError), transaction.atomic():
            DebateAdjudicator.objects.create(debate=debate, adjudicator=adj)

    def test_panel_of_any_size(self, debate: Debate) -> None:
        for i in range(3):
            adj = Adjudicator.objects.create(name=f'Judge {i}')
            DebateAdjudicator.objects.create(debate=debate, adjudicator=adj)
        assert debate.adjudicators.count() == 3

    def test_adjudicator_cannot_sit_on_two_debates_in_a_round(
        self, debate: Debate, round1: Round, teams: list[Team]
    ) -> None:
        other = Debate.objects.create(round=round1, aff_team=teams[2], neg_team=teams[3])
        adj = Adjudicator.objects.create(name='Judge')
        DebateAdjudicator.objects.create(debate=debate, adjudicator=adj)
        with pytest.raises(ValidationError):
            DebateAdjudicator(debate=other, adjudicator=adj).full_clean()

    def test_adjudicator_can_sit_in_different_rounds(
        self, debate: Debate, teams: list[Team]
    ) -> None:
        round2 = Round.objects.create(number=2)
        other = Debate.objects.create(round=round2, aff_team=teams[0], neg_team=teams[1])
        adj = Adjudicator.objects.create(name='Judge')
        DebateAdjudicator.objects.create(debate=debate, adjudicator=adj)
        DebateAdjudicator(debate=other, adjudicator=adj).full_clean()


class TestResult:
    def test_one_result_per_debate(self, debate: Debate, teams: list[Team]) -> None:
        Result.objects.create(debate=debate, winner=teams[0])
        with pytest.raises(IntegrityError), transaction.atomic():
            Result.objects.create(debate=debate, winner=teams[1])

    def test_winner_must_be_in_the_debate(self, debate: Debate, teams: list[Team]) -> None:
        with pytest.raises(ValidationError) as exc:
            Result(debate=debate, winner=teams[2]).full_clean()
        assert 'winner' in exc.value.message_dict

    def test_either_side_can_win(self, debate: Debate, teams: list[Team]) -> None:
        Result(debate=debate, winner=teams[1]).full_clean()

    def test_speaker_points_are_optional(self, debate: Debate, teams: list[Team]) -> None:
        result = Result.objects.create(debate=debate, winner=teams[0])
        assert result.aff_speaker_points is None
        assert result.neg_speaker_points is None

    def test_forfeit_defaults_to_false_and_needs_no_points(
        self, debate: Debate, teams: list[Team]
    ) -> None:
        assert Result.objects.create(debate=debate, winner=teams[0]).forfeit is False
        debate.result.delete()
        forfeit = Result.objects.create(debate=debate, winner=teams[0], forfeit=True)
        forfeit.full_clean()

    def test_negative_speaker_points_rejected(self, debate: Debate, teams: list[Team]) -> None:
        with pytest.raises(IntegrityError), transaction.atomic():
            Result.objects.create(debate=debate, winner=teams[0], aff_speaker_points=Decimal(-1))
        with pytest.raises(IntegrityError), transaction.atomic():
            Result.objects.create(debate=debate, winner=teams[0], neg_speaker_points=Decimal(-1))

    def test_deleting_a_debate_removes_its_result(self, debate: Debate, teams: list[Team]) -> None:
        Result.objects.create(debate=debate, winner=teams[0])
        debate.delete()
        assert Result.objects.count() == 0


class TestBye:
    def test_one_bye_per_round(self, round1: Round, teams: list[Team]) -> None:
        Bye.objects.create(round=round1, team=teams[0])
        with pytest.raises(IntegrityError), transaction.atomic():
            Bye.objects.create(round=round1, team=teams[1])

    def test_same_team_cannot_have_two_byes_in_a_round(
        self, round1: Round, teams: list[Team]
    ) -> None:
        Bye.objects.create(round=round1, team=teams[0])
        with pytest.raises(IntegrityError), transaction.atomic():
            Bye.objects.create(round=round1, team=teams[0])

    def test_team_can_have_byes_in_different_rounds_at_model_level(
        self, round1: Round, teams: list[Team]
    ) -> None:
        # "No second bye while another team has none" is the draw engine's rule.
        Bye.objects.create(round=round1, team=teams[0])
        Bye.objects.create(round=Round.objects.create(number=2), team=teams[0])

    def test_team_with_bye_cannot_be_in_a_debate(
        self, debate: Debate, round1: Round, teams: list[Team]
    ) -> None:
        with pytest.raises(ValidationError):
            Bye(round=round1, team=teams[0]).full_clean()

    def test_team_with_bye_cannot_be_added_to_a_debate(
        self, round1: Round, teams: list[Team]
    ) -> None:
        Bye.objects.create(round=round1, team=teams[2])
        with pytest.raises(ValidationError):
            Debate(round=round1, aff_team=teams[2], neg_team=teams[3]).full_clean()

    def test_bye_for_team_not_debating_is_valid(
        self, debate: Debate, round1: Round, teams: list[Team]
    ) -> None:
        Bye(round=round1, team=teams[2]).full_clean()
