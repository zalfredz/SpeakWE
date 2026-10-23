import json
import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from ielts.models import CueCard, Part1Question, Part1Topic, Part3Question, RoundingOffQuestion, Status


def seed_bank(n_topics=3):
    for t in range(n_topics):
        topic = Part1Topic.objects.create(title=f"topic {t}", status=Status.APPROVED)
        for q in range(4):
            Part1Question.objects.create(topic=topic, order=q, text=f"t{t} q{q}")
    card = CueCard.objects.create(title="Describe a time you helped someone.", bullets=["who", "why", "how"],
                                  closing="and explain how you felt.", theme="helping others", status=Status.APPROVED)
    for i in range(2):
        RoundingOffQuestion.objects.create(card=card, order=i, text=f"ro {i}")
    for i in range(4):
        Part3Question.objects.create(card=card, order=i, text=f"p3 {i}")


def audio(data=b"webm-bytes", mime="audio/webm;codecs=opus"):
    return SimpleUploadedFile("answer.webm", data, content_type=mime)


class ApiTestCase(TestCase):
    """Temp MEDIA_ROOT + JSON helpers + a seeded approved bank."""

    def setUp(self):
        self._media = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=self._media)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self._media, True)
        seed_bank()

    def post_json(self, url, body=None):
        return self.client.post(url, json.dumps(body or {}), content_type="application/json")

    def new_active_session(self, mode="part1"):
        sid = self.post_json("/api/sessions", {"mode": mode}).json()["id"]
        self.post_json(f"/api/sessions/{sid}/state", {"to": "mic_check"})
        self.post_json(f"/api/sessions/{sid}/state", {"to": "active"})
        return sid

    def answer(self, sid, index, duration_ms=1500, data=b"webm-bytes", mime="audio/webm;codecs=opus"):
        self.post_json(f"/api/sessions/{sid}/turns/{index}/begin")
        return self.client.post(f"/api/sessions/{sid}/turns/{index}/answer",
                                {"audio": audio(data, mime), "duration_ms": duration_ms})

    def media_files(self):
        return [p for p in Path(self._media).rglob("*") if p.is_file()]
