from unittest import TestCase as PlainTestCase

from django.test import TestCase

from ielts.models import PracticeSession
from ielts.states import TRANSITIONS, InvalidTransition, can_transition, check

ALLOWED = [("created", "mic_check"), ("mic_check", "active"), ("active", "interrupted"), ("active", "finalizing"),
           ("active", "abandoned"), ("interrupted", "active"), ("interrupted", "abandoned"), ("finalizing", "completed")]


class StateTableTests(PlainTestCase):
    def test_allowed_transitions(self):
        for src, dst in ALLOWED:
            self.assertTrue(can_transition(src, dst), (src, dst))
        self.assertEqual(sum(len(v) for v in TRANSITIONS.values()), len(ALLOWED))

    def test_forbidden_examples(self):
        for src, dst in [("created", "active"), ("completed", "active"), ("abandoned", "active"),
                         ("finalizing", "interrupted")]:
            self.assertFalse(can_transition(src, dst), (src, dst))

    def test_check_raises(self):
        with self.assertRaises(InvalidTransition):
            check("created", "completed")


class SessionTransitionTests(TestCase):
    def test_transition_sets_timestamps(self):
        s = PracticeSession.objects.create(mode="full", seed=1, plan=[])
        s.transition("mic_check")
        self.assertIsNone(s.started_at)
        s.transition("active")
        self.assertIsNotNone(s.started_at)
        s.transition("finalizing")
        s.transition("completed")
        s.refresh_from_db()
        self.assertEqual(s.status, "completed")
        self.assertIsNotNone(s.completed_at)

    def test_transition_rejects_invalid(self):
        s = PracticeSession.objects.create(mode="full", seed=1, plan=[])
        with self.assertRaises(InvalidTransition):
            s.transition("active")
        s.refresh_from_db()
        self.assertEqual(s.status, "created")
