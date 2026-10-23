import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from ielts.models import CueCard, Part1Topic, Status

REPO_BANK = Path(__file__).resolve().parents[3] / "data" / "question-bank" / "ielts-v1.json"


def small_bank(path):
    path.write_text(json.dumps({
        "version": 1,
        "part1_topics": [{"title": "Food", "questions": ["q1", "q2"]}],
        "cue_cards": [{"title": "Describe a gift.", "bullets": ["a", "b", "c"], "closing": "and explain why.",
                       "theme": "gifts", "rounding_off": ["r1"], "part3": ["p1", "p2"]}],
    }), encoding="utf-8")


class SeedBankTests(TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "bank.json"
        small_bank(self.path)

    def test_imports_as_draft_with_children(self):
        call_command("seed_bank", str(self.path), verbosity=0)
        topic = Part1Topic.objects.get()
        self.assertEqual(topic.status, Status.DRAFT)
        self.assertEqual([q.text for q in topic.questions.all()], ["q1", "q2"])
        card = CueCard.objects.get()
        self.assertEqual([q.text for q in card.part3.all()], ["p1", "p2"])
        self.assertEqual(card.rounding_off.count(), 1)

    def test_second_run_adds_nothing(self):
        call_command("seed_bank", str(self.path), verbosity=0)
        call_command("seed_bank", str(self.path), verbosity=0)
        self.assertEqual((Part1Topic.objects.count(), CueCard.objects.count()), (1, 1))

    def test_approve_flag(self):
        call_command("seed_bank", str(self.path), "--approve", verbosity=0)
        self.assertEqual(Part1Topic.objects.get().status, Status.APPROVED)
        self.assertEqual(CueCard.objects.get().status, Status.APPROVED)

    def test_repo_bank_is_valid_and_complete(self):
        call_command("seed_bank", str(REPO_BANK), verbosity=0)
        self.assertEqual(Part1Topic.objects.count(), 10)
        self.assertEqual(CueCard.objects.count(), 10)
        for card in CueCard.objects.all():
            card.full_clean()
            self.assertGreaterEqual(card.part3.count(), 4)
