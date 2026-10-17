from django.contrib import admin

from .models import Adjudicator, Bye, Debate, DebateAdjudicator, Result, Room, Round, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin[Team]):
    list_display = ['name', 'institution']
    search_fields = ['name', 'institution']


@admin.register(Adjudicator)
class AdjudicatorAdmin(admin.ModelAdmin[Adjudicator]):
    list_display = ['name', 'institution']
    search_fields = ['name', 'institution']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin[Room]):
    search_fields = ['name']


class DebateAdjudicatorInline(admin.TabularInline[DebateAdjudicator, Debate]):
    model = DebateAdjudicator
    extra = 1


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin[Round]):
    list_display = ['number', 'motion', 'released']
    list_filter = ['released']


@admin.register(Debate)
class DebateAdmin(admin.ModelAdmin[Debate]):
    list_display = ['round', 'room', 'aff_team', 'neg_team']
    list_filter = ['round']
    inlines = [DebateAdjudicatorInline]


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin[Result]):
    list_display = ['debate', 'winner', 'aff_speaker_points', 'neg_speaker_points', 'forfeit']
    list_filter = ['forfeit', 'debate__round']


@admin.register(Bye)
class ByeAdmin(admin.ModelAdmin[Bye]):
    list_display = ['round', 'team']
    list_filter = ['round']
