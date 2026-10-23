from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError
from django.test import TestCase

from ielts.admin import approve_selected
from ielts.bank import load_bank
from ielts.models import CueCard, Part1Question, Part1Topic, Status


def make_topic(title, status=Status.APPROVED):
    return Part1Topic.objects.create(title=title, status=status)


def make_card(title, status=Status.APPROVED):
    return CueCard.objects.create(title=title, bullets=["who", "when", "why"],
                                  closing="and explain how you felt.", theme="helping others", status=status)


class LoadBankTests(TestCase):
    def test_load_bank_returns_only_approved(self):
        make_topic("Hometown")
        make_topic("Draft topic", Status.DRAFT)
        make_card("Describe a time you helped someone.")
        make_card("Draft card", Status.DRAFT)
        bank = load_bank()
        self.assertEqual([t.title for t in bank.part1_topics], ["Hometown"])
        self.assertEqual([c.title for c in bank.cue_cards], ["Describe a time you helped someone."])

    def test_load_bank_keeps_child_order(self):
        topic = make_topic("Food")
        Part1Question.objects.create(topic=topic, order=2, text="second")
        Part1Question.objects.create(topic=topic, order=1, text="first")
        bank = load_bank()
        self.assertEqual([q.text for q in bank.part1_topics[0].questions], ["first", "second"])


class AdminTests(TestCase):
    def test_approve_action_sets_status(self):
        make_topic("Work", Status.DRAFT)
        approve_selected(site._registry[Part1Topic], None, Part1Topic.objects.all())
        self.assertEqual(Part1Topic.objects.get().status, Status.APPROVED)

    def test_cue_card_requires_3_to_4_bullets(self):
        card = CueCard(title="t", bullets=["a", "b"], closing="c", theme="x")
        with self.assertRaises(ValidationError):
            card.full_clean()
        for bullets in (["a", "b", "c"], ["a", "b", "c", "d"]):
            CueCard(title="t", bullets=bullets, closing="c", theme="x").full_clean()
