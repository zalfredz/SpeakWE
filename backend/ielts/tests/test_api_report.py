from unittest import mock

from django.test import override_settings

from ielts.models import Assessment, AssessmentJob, PracticeSession, Turn
from ielts.tests.helpers import ApiTestCase


class ReportApiTests(ApiTestCase):
    def completed(self):
        sid = self.new_active_session()
        self.answer(sid, 1, data=b"answer-audio")
        s = PracticeSession.objects.get(pk=sid)
        s.status = "completed"
        s.save()
        return s, AssessmentJob.objects.create(session=s, version="ielts-eval-v2")

    def test_report_while_queued(self):
        s, _ = self.completed()
        body = self.client.get(f"/api/sessions/{s.id}/report").json()
        self.assertEqual(body["job"]["status"], "queued")
        self.assertIsNone(body["assessment"])

    @override_settings(GEMINI_API_KEY="top-secret-key")
    def test_report_ready_and_key_never_exposed(self):
        s, job = self.completed()
        Assessment.objects.create(job=job, status="ready", scope="part1_only", report={"criteria": {}}, overall=None,
                                  features={}, provenance={"model": "m", "prompt_version": "ielts-eval-v2"})
        job.status = "ready"
        job.save()
        res = self.client.get(f"/api/sessions/{s.id}/report")
        body = res.json()
        self.assertEqual((body["job"]["status"], body["assessment"]["status"]), ("ready", "ready"))
        self.assertEqual(body["assessment"]["provenance"]["prompt_version"], "ielts-eval-v2")
        self.assertNotIn(b"top-secret-key", res.content)

    def test_report_404_without_job(self):
        sid = self.new_active_session()
        self.assertEqual(self.client.get(f"/api/sessions/{sid}/report").status_code, 404)

    def test_reassess_requeues_only_failed_jobs(self):
        s, job = self.completed()
        self.assertEqual(self.post_json(f"/api/sessions/{s.id}/assess").status_code, 409)
        job.status, job.error_code = "failed", "gemini_http_500"
        job.save()
        res = self.post_json(f"/api/sessions/{s.id}/assess")
        self.assertEqual(res.status_code, 200)
        job.refresh_from_db()
        self.assertEqual((job.status, job.error_code), ("queued", ""))

    def test_turn_audio_is_served(self):
        s, _ = self.completed()
        res = self.client.get(f"/api/sessions/{s.id}/turns/1/audio")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(b"".join(res.streaming_content), b"answer-audio")
        self.assertEqual(res["Content-Type"], "audio/webm")
        self.assertEqual(self.client.get(f"/api/sessions/{s.id}/turns/2/audio").status_code, 404)

    def test_turn_audio_is_converted_to_seekable_mp3(self):
        s, _ = self.completed()
        with mock.patch("ielts.views.to_mp3", return_value=b"ID3mp3-bytes"):
            res = self.client.get(f"/api/sessions/{s.id}/turns/1/audio")
        self.assertEqual((res.status_code, res["Content-Type"], res.content), (200, "audio/mpeg", b"ID3mp3-bytes"))
