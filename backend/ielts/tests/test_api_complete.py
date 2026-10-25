from datetime import datetime, timedelta, timezone

from ielts.checkins import local_date
from ielts.models import AssessmentJob, CheckIn, PracticeSession
from ielts.tests.helpers import ApiTestCase, audio


class CompleteTests(ApiTestCase):
    def answer_all(self, sid, duration_ms=10000):
        plan = self.client.get(f"/api/sessions/{sid}").json()["plan"]
        for step in plan:
            if step["kind"] in ("question", "long_turn"):
                self.post_json(f"/api/sessions/{sid}/turns/{step['index']}/begin")
                # backdate begin so the answer's duration is plausible
                PracticeSession.objects.get(pk=sid).turns.filter(index=step["index"]).update(
                    begun_at=datetime.now(timezone.utc) - timedelta(milliseconds=duration_ms))
                r = self.client.post(f"/api/sessions/{sid}/turns/{step['index']}/answer",
                                     {"audio": audio(), "duration_ms": duration_ms})
                self.assertEqual(r.status_code, 201, r.content)

    def complete(self, sid):
        return self.post_json(f"/api/sessions/{sid}/complete")

    def test_complete_requires_all_turns(self):
        sid = self.new_active_session()
        self.answer(sid, 1)
        r = self.complete(sid)
        self.assertEqual((r.status_code, r.json()["error"]), (409, "unanswered_turns"))
        self.assertIn("2", r.json()["detail"])
        self.assertEqual(PracticeSession.objects.get(pk=sid).status, "active")

    def test_complete_creates_checkin_and_job(self):
        sid = self.new_active_session()
        self.answer_all(sid)
        r = self.complete(sid)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["session"]["status"], "completed")
        today = local_date(datetime.now(timezone.utc), "Asia/Jakarta").isoformat()
        self.assertEqual(body["checkin"], {"local_date": today, "created": True})
        self.assertEqual(body["assessment"], {"version": "ielts-eval-v2", "status": "queued"})

    def test_complete_twice_returns_same_result(self):
        sid = self.new_active_session()
        self.answer_all(sid)
        first = self.complete(sid).json()
        second = self.complete(sid)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["session"], first["session"])
        self.assertEqual(second.json()["checkin"]["local_date"], first["checkin"]["local_date"])
        self.assertEqual(CheckIn.objects.count(), 1)
        self.assertEqual(AssessmentJob.objects.count(), 1)

    def test_short_session_no_checkin(self):
        sid = self.new_active_session()
        self.answer_all(sid, duration_ms=2500)  # 12 answers × 2.5 s = 30 s < 60 s
        body = self.complete(sid).json()
        self.assertIsNone(body["checkin"])
        self.assertEqual(body["assessment"]["status"], "queued")
        self.assertEqual(CheckIn.objects.count(), 0)

    def test_second_session_same_day_no_new_checkin(self):
        first = self.new_active_session()
        self.answer_all(first)
        self.complete(first)
        second = self.new_active_session()
        self.answer_all(second)
        body = self.complete(second).json()
        self.assertFalse(body["checkin"]["created"])
        self.assertEqual(CheckIn.objects.count(), 1)
        self.assertEqual(str(CheckIn.objects.get().session_id), first)

    def test_complete_from_abandoned_409(self):
        sid = self.new_active_session()
        self.post_json(f"/api/sessions/{sid}/state", {"to": "abandoned"})
        r = self.complete(sid)
        self.assertEqual((r.status_code, r.json()["error"]), (409, "invalid_transition"))

    def test_checkins_endpoint_streak(self):
        today = local_date(datetime.now(timezone.utc), "Asia/Jakarta")
        for days_ago in (0, 1):
            s = PracticeSession.objects.create(mode="part1", seed=1, plan=[], status="completed")
            CheckIn.objects.create(local_date=today - timedelta(days=days_ago), practice_tz="Asia/Jakarta", session=s)
        body = self.client.get("/api/checkins").json()
        self.assertEqual(body["streak"], 2)
        self.assertEqual(body["today"], today.isoformat())
        self.assertEqual(body["dates"], [today.isoformat(), (today - timedelta(days=1)).isoformat()])

    def test_part1_time_limit_lets_the_session_complete_early(self):
        sid = self.new_active_session()
        for i in range(1, 9):
            self.answer(sid, i)
        turns = PracticeSession.objects.get(pk=sid).turns
        self.assertEqual(self.complete(sid).status_code, 409)   # 8 answers, but the 5 minutes are not used up
        turns.filter(index=1).update(begun_at=datetime.now(timezone.utc) - timedelta(seconds=290))
        r = self.complete(sid)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(PracticeSession.objects.get(pk=sid).status, "completed")
