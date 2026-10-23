from django.conf import settings
from django.test import SimpleTestCase


class SettingsTests(SimpleTestCase):
    def test_speakwe_config(self):
        self.assertEqual(settings.SPEAKWE["PART2_TALK_S"], 120)
        self.assertEqual(settings.SPEAKWE["MAX_ANSWER_S"][3], 60)
        self.assertEqual(settings.TIME_ZONE, "UTC")
        self.assertIs(settings.USE_TZ, True)
