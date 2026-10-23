import io
import json
from datetime import timedelta
from unittest import TestCase, mock

from django.core.management import call_command
from django.test import TestCase as DjangoTestCase, override_settings
from django.utils import timezone

from ielts.assessment.errors import GeminiError, GeminiOutputError
from ielts.assessment.gemini import GeminiClient
from ielts.models import AssessmentJob, PracticeSession


class FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class GeminiClientTests(TestCase):
    def test_posts_json_with_key_header_and_parses_the_json_answer(self):
        answer = {"candidates": [{"content": {"parts": [{"text": json.dumps({"status": "ready"})}]}}]}
        with mock.patch("ielts.assessment.gemini.urlopen", return_value=FakeResponse(json.dumps(answer).encode())) as op:
            out = GeminiClient("secret-key", "gemini-test").generate({"contents": []})
        req = op.call_args[0][0]
        self.assertEqual(out, {"status": "ready"})
        self.assertEqual(req.full_url, "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent")
        self.assertEqual(req.get_header("X-goog-api-key"), "secret-key")
        self.assertNotIn("secret-key", req.full_url)
        self.assertEqual(json.loads(req.data), {"contents": []})

    def test_http_error_becomes_gemini_error_with_status(self):
        from urllib.error import HTTPError
        err = HTTPError("u", 429, "Too Many Requests", {}, io.BytesIO(b'{"error":"quota"}'))
        with mock.patch("ielts.assessment.gemini.urlopen", side_effect=err):
            with self.assertRaises(GeminiError) as cm:
                GeminiClient("k", "m").generate({})
        self.assertEqual(cm.exception.status, 429)

    def test_unparseable_answer_is_an_output_error_so_it_can_be_retried(self):
        answer = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
        with mock.patch("ielts.assessment.gemini.urlopen", return_value=FakeResponse(json.dumps(answer).encode())):
            with self.assertRaises(GeminiOutputError):
                GeminiClient("k", "m").generate({})

    def test_connection_reset_and_non_json_body_become_gemini_errors(self):
        with mock.patch("ielts.assessment.gemini.urlopen", side_effect=ConnectionResetError("reset")):
            with self.assertRaises(GeminiError):
                GeminiClient("k", "m").generate({})
        with mock.patch("ielts.assessment.gemini.urlopen", return_value=FakeResponse(b"<html>oops</html>")):
            with self.assertRaises(GeminiError):
                GeminiClient("k", "m").generate({})


class WorkerCommandTests(DjangoTestCase):
    @override_settings(GEMINI_API_KEY="")
    def test_missing_key_exits_with_a_clear_error(self):
        err = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command("run_assessments", "--once", stderr=err)
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("GEMINI_API_KEY", err.getvalue())

    @override_settings(GEMINI_API_KEY="k")
    def test_stale_processing_jobs_are_requeued(self):
        s = PracticeSession.objects.create(mode="part1", seed=1, plan=[], status="completed")
        job = AssessmentJob.objects.create(session=s, version="v", status="processing")
        AssessmentJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=20))
        with mock.patch("ielts.management.commands.run_assessments.assess") as assess:
            call_command("run_assessments", "--once", stdout=io.StringIO())
        assess.assert_called_once()
        self.assertEqual(assess.call_args[0][0].pk, job.pk)

    @override_settings(GEMINI_API_KEY="k")
    def test_job_stuck_after_three_attempts_is_failed_not_requeued(self):
        s = PracticeSession.objects.create(mode="part1", seed=1, plan=[], status="completed")
        job = AssessmentJob.objects.create(session=s, version="v", status="processing", attempts=3)
        AssessmentJob.objects.filter(pk=job.pk).update(updated_at=timezone.now() - timedelta(minutes=20))
        with mock.patch("ielts.management.commands.run_assessments.assess") as assess:
            call_command("run_assessments", "--once", stdout=io.StringIO())
        assess.assert_not_called()
        job.refresh_from_db()
        self.assertEqual((job.status, job.error_code), ("failed", "stuck"))
