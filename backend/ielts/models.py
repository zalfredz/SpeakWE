import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from . import states
from .flow import MODES


class Status(models.TextChoices):
    DRAFT = "draft"
    APPROVED = "approved"


class Source(models.TextChoices):
    ORIGINAL = "original"
    INSPIRED = "inspired_by"


class BankItem(models.Model):
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.ORIGINAL)
    source_ref = models.CharField(max_length=64, blank=True, help_text="Video id when inspired_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Part1Topic(BankItem):
    title = models.CharField(max_length=120)

    def __str__(self):
        return self.title


class Part1Question(models.Model):
    topic = models.ForeignKey(Part1Topic, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveSmallIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["order"]


class CueCard(BankItem):
    title = models.TextField(help_text='e.g. "Describe a time you helped someone."')
    bullets = models.JSONField(help_text="3–4 'You should say' points")
    closing = models.TextField(help_text='e.g. "and explain how you felt about it."')
    theme = models.CharField(max_length=80, help_text="Used in the Part 3 intro")

    def clean(self):
        if not isinstance(self.bullets, list) or not 3 <= len(self.bullets) <= 4:
            raise ValidationError({"bullets": "A cue card needs 3 or 4 bullet points."})

    def __str__(self):
        return self.title


class RoundingOffQuestion(models.Model):
    card = models.ForeignKey(CueCard, on_delete=models.CASCADE, related_name="rounding_off")
    order = models.PositiveSmallIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["order"]


class Part3Question(models.Model):
    card = models.ForeignKey(CueCard, on_delete=models.CASCADE, related_name="part3")
    order = models.PositiveSmallIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["order"]


class PracticeSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mode = models.CharField(max_length=8, choices=[(m, m) for m in MODES])
    status = models.CharField(max_length=16, default="created")
    seed = models.IntegerField()
    plan = models.JSONField()
    practice_tz = models.CharField(max_length=64, default="Asia/Jakarta")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def transition(self, dst: str) -> None:
        states.check(self.status, dst)
        self.status = dst
        if dst == "active" and self.started_at is None:
            self.started_at = timezone.now()
        if dst == "completed":
            self.completed_at = timezone.now()
        self.save()


class Turn(models.Model):
    """One answer recording; exists only for question/long_turn steps."""
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name="turns")
    index = models.PositiveSmallIntegerField()
    begun_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    audio = models.FileField(upload_to="answers/%Y/%m/", blank=True)
    mime = models.CharField(max_length=64, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    transcript = models.JSONField(null=True, blank=True, help_text="Whisper segments with word timestamps (seconds, relative to this answer)")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "index"], name="unique_turn_per_session")]


class CheckIn(models.Model):
    # shortcut: unique on local_date only because there is no login yet; becomes (user, local_date) when accounts arrive.
    local_date = models.DateField(unique=True)
    practice_tz = models.CharField(max_length=64)
    session = models.OneToOneField(PracticeSession, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class AssessmentJob(models.Model):
    STATUSES = ["queued", "processing", "ready", "partial", "failed"]
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name="assessment_jobs")
    version = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=[(s, s) for s in STATUSES], default="queued")
    attempts = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "version"], name="unique_job_per_version")]


class Assessment(models.Model):
    """One accepted evaluator result. The raw report is kept verbatim: it is also a silver label for the ML track."""
    job = models.OneToOneField(AssessmentJob, on_delete=models.CASCADE, related_name="assessment")
    status = models.CharField(max_length=24)          # ready | partial | insufficient_evidence
    scope = models.CharField(max_length=16)
    overall = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    report = models.JSONField(null=True, blank=True)
    features = models.JSONField(default=dict)
    provenance = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
