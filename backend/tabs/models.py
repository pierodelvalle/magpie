from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Team(models.Model):
    name = models.CharField(max_length=200, unique=True)
    institution = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Adjudicator(models.Model):
    name = models.CharField(max_length=200)
    institution = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Round(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
    motion = models.TextField(blank=True)
    released = models.BooleanField(default=False)

    class Meta:
        ordering = ['number']

    def __str__(self) -> str:
        return f'Round {self.number}'


class Debate(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='debates')
    # Draft draws may exist before rooms are assigned.
    room = models.ForeignKey(
        Room, null=True, blank=True, on_delete=models.SET_NULL, related_name='debates'
    )
    aff_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='aff_debates')
    neg_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='neg_debates')

    class Meta:
        ordering = ['round', 'id']
        constraints = [
            models.CheckConstraint(
                condition=~Q(aff_team=F('neg_team')), name='debate_teams_differ'
            ),
            models.UniqueConstraint(
                fields=['round', 'aff_team'], name='debate_aff_team_once_per_round'
            ),
            models.UniqueConstraint(
                fields=['round', 'neg_team'], name='debate_neg_team_once_per_round'
            ),
            models.UniqueConstraint(fields=['round', 'room'], name='debate_room_once_per_round'),
        ]

    def __str__(self) -> str:
        return f'{self.round}: {self.aff_team} (aff) v {self.neg_team} (neg)'

    def clean(self) -> None:
        # The unique constraints only catch a team repeating on the same side, so check that
        # a team is not aff in one debate and neg in another, or on a bye, in the same round.
        if self.round_id is None or self.aff_team_id is None or self.neg_team_id is None:
            return
        teams = [self.aff_team_id, self.neg_team_id]
        others = Debate.objects.filter(round_id=self.round_id).exclude(pk=self.pk)
        if others.filter(Q(aff_team_id__in=teams) | Q(neg_team_id__in=teams)).exists():
            raise ValidationError('A team can only appear in one debate per round.')
        if Bye.objects.filter(round_id=self.round_id, team_id__in=teams).exists():
            raise ValidationError('A team with a bye cannot also be in a debate.')


class DebateAdjudicator(models.Model):
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE, related_name='adjudicators')
    adjudicator = models.ForeignKey(
        Adjudicator, on_delete=models.PROTECT, related_name='debate_assignments'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['debate', 'adjudicator'], name='adjudicator_once_per_debate'
            ),
        ]

    def __str__(self) -> str:
        return f'{self.adjudicator} on {self.debate}'

    def clean(self) -> None:
        if self.debate_id is None or self.adjudicator_id is None:
            return
        clash = DebateAdjudicator.objects.filter(
            debate__round_id=self.debate.round_id, adjudicator_id=self.adjudicator_id
        ).exclude(pk=self.pk)
        if clash.exists():
            raise ValidationError('An adjudicator can only sit on one debate per round.')


class Result(models.Model):
    debate = models.OneToOneField(Debate, on_delete=models.CASCADE, related_name='result')
    winner = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='wins')
    # Optional; a forfeit needs no speaker points and counts as 0 in totals.
    aff_speaker_points = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    neg_speaker_points = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    forfeit = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(aff_speaker_points__isnull=True) | Q(aff_speaker_points__gte=0)),
                name='result_aff_points_non_negative',
            ),
            models.CheckConstraint(
                condition=(Q(neg_speaker_points__isnull=True) | Q(neg_speaker_points__gte=0)),
                name='result_neg_points_non_negative',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.debate}: {self.winner} won'

    def clean(self) -> None:
        if self.debate_id is None or self.winner_id is None:
            return
        if self.winner_id not in (self.debate.aff_team_id, self.debate.neg_team_id):
            raise ValidationError({'winner': 'The winner must be one of the two teams debating.'})


class Bye(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='byes')
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name='byes')

    class Meta:
        verbose_name_plural = 'byes'
        constraints = [
            models.UniqueConstraint(fields=['round', 'team'], name='bye_team_once_per_round'),
            # RULES.md: a bye is one per round, and no team gets a second one while another
            # has none. The "no second bye" rule depends on the other teams, so it lives in the
            # draw engine; here we only stop a single round having two byes.
            models.UniqueConstraint(fields=['round'], name='one_bye_per_round'),
        ]

    def __str__(self) -> str:
        return f'{self.round}: {self.team} (bye)'

    def clean(self) -> None:
        if self.round_id is None or self.team_id is None:
            return
        in_debate = Debate.objects.filter(round_id=self.round_id).filter(
            Q(aff_team_id=self.team_id) | Q(neg_team_id=self.team_id)
        )
        if in_debate.exists():
            raise ValidationError('A team with a bye cannot also be in a debate.')
