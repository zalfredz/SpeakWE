"""Worker: assess queued sessions. Run alongside the dev server: manage.py run_assessments"""
import sys
import time
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from ielts.assessment.audio import to_mp3
from ielts.assessment.gemini import GeminiClient
from ielts.assessment.pipeline import assess
from ielts.assessment.transcribe import WhisperTranscriber
from ielts.models import AssessmentJob

STALE_AFTER = timedelta(minutes=15)
MAX_ATTEMPTS = 3


class Command(BaseCommand):
    help = "Transcribe and assess completed IELTS sessions (polls the job queue)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process the current queue and exit.")
        parser.add_argument("--interval", type=float, default=3.0)

    def handle(self, once, interval, **opts):
        if not settings.GEMINI_API_KEY:
            self.stderr.write("GEMINI_API_KEY is not set. Put it in backend/.env (GEMINI_API_KEY=...) or the environment.")
            sys.exit(1)
        client = GeminiClient(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
        transcriber = WhisperTranscriber()
        self.stdout.write(f"Assessment worker using {settings.GEMINI_MODEL}. Gemini free tier: dev/test recordings only.")
        tried = set()   # never pick the same job twice in one pass, even if it stays queued
        while True:
            # a job left 'processing' by a crashed worker goes back to the queue, unless it keeps getting stuck
            stale = AssessmentJob.objects.filter(status="processing", updated_at__lt=timezone.now() - STALE_AFTER)
            stale.filter(attempts__gte=MAX_ATTEMPTS).update(status="failed", error_code="stuck")
            stale.filter(attempts__lt=MAX_ATTEMPTS).update(status="queued")
            job = AssessmentJob.objects.filter(status="queued").exclude(pk__in=tried).order_by("created_at").first()
            if job:
                tried.add(job.pk)
                self.stdout.write(f"Assessing session {job.session_id} (attempt {job.attempts + 1})…")
                assess(job, transcribe=transcriber, convert=to_mp3, client=client)
                job.refresh_from_db()
                self.stdout.write(f"  → {job.status} {job.error_code}".rstrip())
                continue
            if once:
                return
            tried.clear()
            time.sleep(interval)
