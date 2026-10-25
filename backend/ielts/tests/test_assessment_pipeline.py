import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from ielts.assessment import calibration
from ielts.assessment.errors import GeminiError, GeminiOutputError
from ielts.assessment.pipeline import assess
from ielts.models import Assessment, AssessmentJob, PracticeSession, Turn

SENTENCE = "I really like my hometown because it is calm and green"


def step(i, part, kind):
    return {"index": i, "part": part, "kind": kind, "text": f"question {i}", "item_id": None,
            "max_answer_s": 120 if kind == "long_turn" else 60, "prep_s": None}


def fake_transcribe(path):
    # ~22 s of recognised speech per answer, so three answers clear the 60 s per-Part minimum
    words = [{"w": " " + x, "s": n * 2.2, "e": n * 2.2 + 0.3, "p": 0.9} for n, x in enumerate(SENTENCE.split())]
    return [{"start": 0.0, "end": words[-1]["e"], "words": words}]


class FakeClient:
    model = "fake-model"

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def generate(self, body):
        self.calls += 1
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out(body) if callable(out) else out


def valid_output(scope, seg_ids, bands=(6, 6, 6, 7)):
    end = round(((len(SENTENCE.split()) - 1) * 2.2 + 0.3) * 1000)
    def ev(kind, sid, quote, **x):
        return {"type": kind, "turn_id": sid.split("-")[0], "segment_id": sid, "start_ms": 0, "end_ms": end,
                "quote": quote, "observation_id": "o", **x}
    a, b = seg_ids[0], seg_ids[1]
    crit = lambda band, quotes: {"band": band, "descriptor_fit_id": "d", "why_not_higher_id": "h", "why_not_lower_id": "l",
                                 "evidence": quotes}
    return {
        "status": "ready", "scope": scope,
        "criteria": {
            "fc": crit(bands[0], [ev("strength", a, "I really like"), ev("limitation", a, "because it is")]),
            "lr": crit(bands[1], [ev("strength", a, "calm and green"), ev("limitation", b, "my hometown")]),
            "gra": crit(bands[2], [ev("strength", b, "it is calm"), ev("limitation", b, "I really")]),
            "p": crit(bands[3], [ev("strength", b, "green"), ev("limitation", a, "like my", heard_as="laik mai")]),
        },
        "asr_suspected": [],
        "feedback": {"summary_id": "s", "upgrade_opportunities": [],
                     "priorities": [{"criterion": "fc", "title_id": "t", "explanation_id": "e", "evidence_segment_ids": [a], "drill_id": "d"}]},
    }


class PipelineTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        o = override_settings(MEDIA_ROOT=self.media)
        o.enable()
        self.addCleanup(o.disable)
        self.addCleanup(shutil.rmtree, self.media, True)

    def make_session(self, mode, layout):
        """layout: list of (part, kind, duration_ms)"""
        plan = [step(i, part, kind) for i, (part, kind, _) in enumerate(layout)]
        s = PracticeSession.objects.create(mode=mode, seed=1, plan=plan, status="completed")
        for i, (_, _, ms) in enumerate(layout):
            t = Turn(session=s, index=i, duration_ms=ms, mime="audio/webm")
            t.audio.save(f"{i}.webm", ContentFile(b"audio"), save=False)
            from django.utils import timezone
            t.begun_at = t.answered_at = timezone.now()
            t.save()
        return AssessmentJob.objects.create(session=s, version="ielts-eval-v2")

    FULL = [(1, "question", 25000)] * 3 + [(2, "long_turn", 80000)] + [(2, "question", 25000)] * 2 + [(3, "question", 25000)] * 3

    def run_job(self, job, client):
        assess(job, transcribe=fake_transcribe, convert=lambda p: b"mp3", client=client)
        job.refresh_from_db()
        return job

    def test_full_test_ready_with_server_overall(self):
        job = self.make_session("full", self.FULL)
        client = FakeClient(lambda body: valid_output("full_test", ["t0-1", "t4-1"]))
        job = self.run_job(job, client)
        self.assertEqual(job.status, "ready")
        a = Assessment.objects.get(job=job)
        self.assertEqual(a.features["ml"]["gemini_overall"], 6.5)   # the shown overall depends on calibration.json
        self.assertEqual(float(a.overall), a.features["ml"].get("a", 6.5))
        self.assertEqual(a.provenance["prompt_version"], "ielts-eval-v2")
        self.assertEqual(a.provenance["model"], "fake-model")
        self.assertIn("pause_ratio", a.features["session"])
        self.assertIsNotNone(Turn.objects.get(session=job.session, index=0).transcript)

    def test_full_test_overall_comes_from_calibration_model_a(self):
        # a fake model whose only input is Gemini's gra band: overall = 2 * gra - 4.75 -> 7.25, shown as 7.5
        fake = {"a": {"features": ["gra"], "mean": [0], "scale": [1], "coef": [2], "intercept": -4.75, "trained": "t"},
                "b": {"features": ["speech_rate_wpm"], "mean": [0], "scale": [1], "coef": [0], "intercept": 5.0, "trained": "t"}}
        path = Path(self.media) / "calibration.json"
        path.write_text(json.dumps(fake))
        with mock.patch.object(calibration, "MODELS_PATH", path):
            job = self.run_job(self.make_session("full", self.FULL), FakeClient(lambda body: valid_output("full_test", ["t0-1", "t4-1"])))
        a = Assessment.objects.get(job=job)
        self.assertEqual(float(a.overall), 7.5)
        self.assertEqual(a.features["ml"], {"a": 7.5, "b": 5.0, "gemini_overall": 6.5})
        self.assertEqual(a.provenance["calibration"], "ridge-a-t")

    def test_without_calibration_models_the_gemini_overall_is_shown(self):
        with mock.patch.object(calibration, "MODELS_PATH", Path(self.media) / "missing.json"):
            job = self.run_job(self.make_session("full", self.FULL), FakeClient(lambda body: valid_output("full_test", ["t0-1", "t4-1"])))
        a = Assessment.objects.get(job=job)
        self.assertEqual((float(a.overall), a.provenance["calibration"]), (6.5, "none"))

    def test_part_only_has_no_overall(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        job = self.run_job(job, FakeClient(valid_output("part1_only", ["t0-1", "t1-1"])))
        self.assertEqual(job.status, "ready")
        self.assertIsNone(Assessment.objects.get(job=job).overall)

    def test_too_little_speech_is_insufficient_without_calling_gemini(self):
        job = self.make_session("part1", [(1, "question", 8000)] * 2)
        client = FakeClient()
        job = self.run_job(job, client)
        self.assertEqual(client.calls, 0)
        a = Assessment.objects.get(job=job)
        self.assertEqual((a.status, a.overall, a.report), ("insufficient_evidence", None, None))

    def test_invalid_output_is_retried_then_fails(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        bad = valid_output("part1_only", ["t0-1", "t1-1"])
        bad["criteria"]["fc"]["evidence"][0]["quote"] = "made up"
        client = FakeClient(bad, bad, bad)
        job = self.run_job(job, client)
        self.assertEqual((job.status, job.error_code, client.calls), ("failed", "invalid_output", 3))
        self.assertFalse(Assessment.objects.filter(job=job).exists())

    def test_retry_recovers_from_one_invalid_output(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        bad = valid_output("part1_only", ["t0-1", "t1-1"])
        bad["overall"] = 6.0
        job = self.run_job(job, FakeClient(bad, valid_output("part1_only", ["t0-1", "t1-1"])))
        self.assertEqual(job.status, "ready")

    def test_gemini_error_marks_job_failed(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        job = self.run_job(job, FakeClient(GeminiError(429, "quota")))
        self.assertEqual((job.status, job.error_code), ("failed", "gemini_http_429"))

    def test_part_below_minimum_is_excluded_and_job_is_partial(self):
        layout = [(1, "question", 25000)] * 3 + [(2, "long_turn", 20000)] + [(3, "question", 25000)] * 3
        job = self.make_session("full", layout)
        seen = {}
        def capture(body):
            seen["text"] = body["contents"][0]["parts"][0]["text"]
            return valid_output("full_test", ["t0-1", "t4-1"])
        job = self.run_job(job, FakeClient(capture))
        self.assertEqual(job.status, "partial")
        self.assertNotIn("t3 part2", seen["text"])
        self.assertIsNone(Assessment.objects.get(job=job).overall)

    def test_finished_job_is_not_assessed_again(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        self.run_job(job, FakeClient(valid_output("part1_only", ["t0-1", "t1-1"])))
        client = FakeClient()
        self.run_job(job, client)
        self.assertEqual(client.calls, 0)

    def test_unexpected_error_marks_job_failed_instead_of_killing_the_worker(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        job = self.run_job(job, FakeClient(ValueError("boom")))
        self.assertEqual((job.status, job.error_code), ("failed", "internal_error"))

    def test_silent_answers_do_not_reach_gemini(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        client = FakeClient()
        assess(job, transcribe=lambda p: [], convert=lambda p: b"mp3", client=client)
        job.refresh_from_db()
        self.assertEqual(client.calls, 0)
        self.assertEqual(Assessment.objects.get(job=job).status, "insufficient_evidence")

    def test_unparseable_output_is_retried_once(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        job = self.run_job(job, FakeClient(GeminiOutputError(200, "not json"), valid_output("part1_only", ["t0-1", "t1-1"])))
        self.assertEqual(job.status, "ready")

    def test_schema_rejected_by_api_falls_back_to_plain_json_mode(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        seen = []
        def second(body):
            seen.append("responseJsonSchema" in body["generationConfig"])
            return valid_output("part1_only", ["t0-1", "t1-1"])
        job = self.run_job(job, FakeClient(GeminiError(400, "Invalid JSON schema"), second))
        self.assertEqual(job.status, "ready")
        self.assertEqual(seen, [False])

    def test_request_tells_gemini_the_exact_scope(self):
        layout = [(1, "question", 25000)] * 3 + [(2, "long_turn", 20000)] + [(3, "question", 25000)] * 3
        job = self.make_session("full", layout)
        seen = {}
        def capture(body):
            seen["text"] = body["contents"][0]["parts"][0]["text"]
            return valid_output("full_test", ["t0-1", "t4-1"])
        self.run_job(job, FakeClient(capture))
        self.assertIn('use exactly "full_test"', seen["text"])

    def test_retry_tells_gemini_what_was_wrong_and_allows_three_attempts(self):
        job = self.make_session("part1", [(1, "question", 25000)] * 3)
        bad = valid_output("part1_only", ["t0-1", "t1-1"])
        bad["criteria"]["p"]["evidence"][1].pop("heard_as")
        seen = []
        def third(body):
            seen.append(body["contents"][-1]["parts"][0]["text"])
            return valid_output("part1_only", ["t0-1", "t1-1"])
        client = FakeClient(bad, bad, third)
        job = self.run_job(job, client)
        self.assertEqual((job.status, client.calls), ("ready", 3))
        self.assertIn("heard_as", seen[0])
