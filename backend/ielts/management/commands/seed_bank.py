"""Import the question bank JSON. Idempotent by title; new items are drafts unless --approve."""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from ielts.models import CueCard, Part1Question, Part1Topic, Part3Question, RoundingOffQuestion, Source, Status

DEFAULT = Path(settings.BASE_DIR).parent / "data" / "question-bank" / "ielts-v1.json"


class Command(BaseCommand):
    help = "Import IELTS Part 1 topics and cue cards (with Part 3 questions) from a JSON bank."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(DEFAULT))
        parser.add_argument("--approve", action="store_true", help="Mark imported items approved (local testing only).")

    @transaction.atomic
    def handle(self, path, approve, **opts):
        bank = json.loads(Path(path).read_text(encoding="utf-8"))
        status = Status.APPROVED if approve else Status.DRAFT
        added = {"topics": 0, "cards": 0}
        for t in bank["part1_topics"]:
            if Part1Topic.objects.filter(title=t["title"]).exists():
                continue
            topic = Part1Topic.objects.create(title=t["title"], status=status, source=Source.ORIGINAL)
            Part1Question.objects.bulk_create(Part1Question(topic=topic, order=i, text=q) for i, q in enumerate(t["questions"]))
            added["topics"] += 1
        for c in bank["cue_cards"]:
            if CueCard.objects.filter(title=c["title"]).exists():
                continue
            card = CueCard(title=c["title"], bullets=c["bullets"], closing=c["closing"], theme=c["theme"],
                           status=status, source=Source.ORIGINAL)
            card.full_clean()
            card.save()
            RoundingOffQuestion.objects.bulk_create(RoundingOffQuestion(card=card, order=i, text=q) for i, q in enumerate(c["rounding_off"]))
            Part3Question.objects.bulk_create(Part3Question(card=card, order=i, text=q) for i, q in enumerate(c["part3"]))
            added["cards"] += 1
        self.stdout.write(f"Added {added['topics']} Part 1 topics and {added['cards']} cue cards as {status}.")
