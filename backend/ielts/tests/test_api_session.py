import hashlib
import uuid
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core.files.storage import default_storage
from django.test import override_settings
from django.utils import timezone

from ielts.models import Part1Topic, Turn
from ielts.tests.helpers import ApiTestCase, audio


class CreateSessionTests(ApiTestCase):
    def test_create_session_returns_plan(self):
        r = self.post_json("/api/sessions", {"mode": "full"})
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["status"], "created")
        self.assertEqual(body["mode"], "full")
        self.assertEqual(body["plan"][0]["kind"], "instruction")
        self.assertEqual(body["turns"], [])

    def test_create_session_bad_mode_400(self):
        r = self.post_json("/api/sessions", {"mode": "daily"})
        self.assertEqual((r.status_code, r.json()["error"]), (400, "bad_mode"))

    def test_create_session_409_when_bank_too_small(self):
        Part1Topic.objects.first().delete()
        r = self.post_json("/api/sessions", {"mode": "part1"})
        self.assertEqual((r.status_code, r.json()["error"]), (409, "bank_too_small"))

    def test_get_session_404(self):
        r = self.client.get(f"/api/sessions/{uuid.uuid4()}")
        self.assertEqual((r.status_code, r.json()["error"]), (404, "not_found"))


class StateTests(ApiTestCase):
    def test_state_transition_ok_and_invalid(self):
        sid = self.post_json("/api/sessions", {"mode": "part1"}).json()["id"]
        r = self.post_json(f"/api/sessions/{sid}/state", {"to": "active"})
        self.assertEqual((r.status_code, r.json()["error"]), (409, "invalid_transition"))
        self.assertEqual(self.post_json(f"/api/sessions/{sid}/state", {"to": "mic_check"}).status_code, 200)
        r = self.post_json(f"/api/sessions/{sid}/state", {"to": "active"})
        self.assertEqual((r.status_code, r.json()["status"]), (200, "active"))

    def test_state_endpoint_refuses_completed(self):
        sid = self.new_active_session()
        r = self.post_json(f"/api/sessions/{sid}/state", {"to": "completed"})
        self.assertEqual((r.status_code, r.json()["error"]), (409, "invalid_transition"))


class TurnTests(ApiTestCase):
    def test_begin_is_idempotent(self):
        sid = self.new_active_session()
        first = self.post_json(f"/api/sessions/{sid}/turns/1/begin").json()["begun_at"]
        second = self.post_json(f"/api/sessions/{sid}/turns/1/begin").json()["begun_at"]
        self.assertEqual(first, second)

    def test_begin_rejects_instruction_step(self):
        sid = self.new_active_session()
        r = self.post_json(f"/api/sessions/{sid}/turns/0/begin")
        self.assertEqual((r.status_code, r.json()["error"]), (400, "not_an_answer_step"))

    def test_begin_requires_active_session(self):
        sid = self.post_json("/api/sessions", {"mode": "part1"}).json()["id"]
        r = self.post_json(f"/api/sessions/{sid}/turns/1/begin")
        self.assertEqual((r.status_code, r.json()["error"]), (409, "not_active"))

    def test_answer_upload_stores_metadata(self):
        sid = self.new_active_session()
        r = self.answer(sid, 1, data=b"abc")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["mime"], "audio/webm")
        turn = Turn.objects.get(session_id=sid, index=1)
        self.assertEqual(turn.sha256, hashlib.sha256(b"abc").hexdigest())
        self.assertEqual(turn.size_bytes, 3)
        self.assertEqual(turn.duration_ms, 1500)

    def test_answer_upload_is_idempotent(self):
        sid = self.new_active_session()
        self.answer(sid, 1, data=b"first")
        r = self.answer(sid, 1, data=b"second")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Turn.objects.get(session_id=sid, index=1).sha256, hashlib.sha256(b"first").hexdigest())
        self.assertEqual(len(self.media_files()), 1)

    def test_concurrent_upload_loser_keeps_first_and_deletes_own_file(self):
        sid = self.new_active_session()
        self.post_json(f"/api/sessions/{sid}/turns/1/begin")
        real_save = default_storage.save

        def save_then_lose_race(name, content, *args, **kwargs):
            stored = real_save(name, content, *args, **kwargs)
            # another request answers the same turn while this one is writing its file
            Turn.objects.filter(session_id=sid, index=1).update(answered_at=timezone.now(), sha256="winner")
            return stored

        with mock.patch("ielts.views.default_storage.save", side_effect=save_then_lose_race):
            r = self.client.post(f"/api/sessions/{sid}/turns/1/answer", {"audio": audio(), "duration_ms": 1000})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Turn.objects.get(session_id=sid, index=1).sha256, "winner")
        self.assertEqual(self.media_files(), [])

    def test_answer_rejected_out_of_order(self):
        sid = self.new_active_session()
        r = self.post_json(f"/api/sessions/{sid}/turns/2/begin")
        self.assertEqual((r.status_code, r.json()["error"]), (409, "out_of_order"))

    def test_answer_rejected_for_instruction_step(self):
        sid = self.new_active_session()
        r = self.client.post(f"/api/sessions/{sid}/turns/0/answer", {"audio": audio(), "duration_ms": 1000})
        self.assertEqual((r.status_code, r.json()["error"]), (400, "not_an_answer_step"))

    def test_answer_rejected_not_begun(self):
        sid = self.new_active_session()
        r = self.client.post(f"/api/sessions/{sid}/turns/1/answer", {"audio": audio(), "duration_ms": 1000})
        self.assertEqual((r.status_code, r.json()["error"]), (409, "not_begun"))

    def test_answer_rejected_over_limit(self):
        sid = self.new_active_session()
        self.post_json(f"/api/sessions/{sid}/turns/1/begin")
        Turn.objects.filter(session_id=sid, index=1).update(begun_at=timezone.now() - timedelta(seconds=70))
        r = self.client.post(f"/api/sessions/{sid}/turns/1/answer", {"audio": audio(), "duration_ms": 63000})
        self.assertEqual((r.status_code, r.json()["error"]), (400, "over_limit"))
        r = self.client.post(f"/api/sessions/{sid}/turns/1/answer", {"audio": audio(), "duration_ms": 61000})
        self.assertEqual(r.status_code, 201)

    def test_answer_rejected_longer_than_elapsed(self):
        sid = self.new_active_session()
        r = self.answer(sid, 1, duration_ms=30000)  # begun just now: 30 s of audio is impossible
        self.assertEqual((r.status_code, r.json()["error"]), (400, "over_limit"))

    def test_answer_rejected_bad_mime(self):
        sid = self.new_active_session()
        r = self.answer(sid, 1, mime="text/plain")
        self.assertEqual((r.status_code, r.json()["error"]), (400, "bad_mime"))
        self.assertEqual(self.media_files(), [])

    def test_answer_rejected_too_large(self):
        sid = self.new_active_session()
        with override_settings(SPEAKWE={**settings.SPEAKWE, "UPLOAD_MAX_BYTES": 10}):
            r = self.answer(sid, 1, data=b"x" * 11)
        self.assertEqual((r.status_code, r.json()["error"]), (413, "too_large"))
        self.assertEqual(self.media_files(), [])
        self.assertIsNone(Turn.objects.get(session_id=sid, index=1).answered_at)

    def test_session_json_lists_turns(self):
        sid = self.new_active_session()
        self.answer(sid, 1)
        turns = self.client.get(f"/api/sessions/{sid}").json()["turns"]
        self.assertEqual([t["index"] for t in turns], [1])
        self.assertEqual(turns[0]["duration_ms"], 1500)
