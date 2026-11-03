from unittest import TestCase

from ielts.assessment import calibration


class CalibrationTests(TestCase):
    def test_confidence_features(self):
        words = [{"w": " a", "p": 0.9}, {"w": " b", "p": 0.3}, {"w": " c", "p": 0.6}, {"w": " d", "p": 0.2}]
        c = calibration.confidence(words)
        self.assertAlmostEqual(c["mean_p"], 0.5)
        self.assertEqual(c["low_p_ratio"], 0.5)
        self.assertEqual(calibration.confidence([]), {"mean_p": 0.0, "low_p_ratio": 0.0})

    def test_shipped_models_cover_every_input(self):
        sess = {"speech_s": 60, "pause_ratio": 0.2, "mean_length_of_run": 5, "speech_rate_wpm": 110,
                "fillers_per_min": 3, "repetitions": 2, "self_corrections": 1}
        values = calibration.inputs(sess, [{"w": " hello", "p": 0.9}], {"fc": 6, "lr": 6, "gra": 6, "p": 6})
        for key, model in calibration.load().items():
            self.assertTrue(set(model["features"]) <= set(values), key)
            self.assertTrue(1 <= calibration.predict(model, values) <= 9)
