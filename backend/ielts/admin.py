from django.contrib import admin

from .models import CueCard, Part1Question, Part1Topic, Part3Question, RoundingOffQuestion, Status


@admin.action(description="Approve selected items")
def approve_selected(modeladmin, request, queryset):
    queryset.update(status=Status.APPROVED)


class Part1QuestionInline(admin.TabularInline):
    model = Part1Question
    extra = 1


class RoundingOffInline(admin.TabularInline):
    model = RoundingOffQuestion
    extra = 1


class Part3Inline(admin.TabularInline):
    model = Part3Question
    extra = 1


@admin.register(Part1Topic)
class Part1TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "source", "source_ref")
    list_filter = ("status", "source")
    inlines = [Part1QuestionInline]
    actions = [approve_selected]


@admin.register(CueCard)
class CueCardAdmin(admin.ModelAdmin):
    list_display = ("title", "theme", "status", "source", "source_ref")
    list_filter = ("status", "source")
    inlines = [RoundingOffInline, Part3Inline]
    actions = [approve_selected]
