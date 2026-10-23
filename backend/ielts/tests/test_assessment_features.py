from unittest import TestCase

from ielts.assessment.features import session_features, turn_features


def w(word, s, e, p=0.9):
    return {"w": word, "s": s, "e": e, "p": p}


# 10 s answer: "I I like, um, cook- cooking" ... with one 1 s pause and one 0.25 s gap (below the 0.3 s pause threshold)
WORDS = [w(" I", 0.0, 0.2), w(" I", 0.45, 0.5), w(" like,", 0.5, 0.9), w(" um,", 1.0, 1.3),
         w(" cook-", 2.3, 2.6), w(" cooking", 2.6, 3.2), w(" at", 3.2, 3.4), w(" home.", 3.4, 4.0)]


class FeatureTests(TestCase):
    def test_turn_features(self):
        f = turn_features(WORDS, duration_s=10.0)
        self.assertAlmostEqual(f["speech_s"], 4.0)
        self.assertEqual(f["words"], 8)
        self.assertAlmostEqual(f["pause_ratio"], 0.1)            # only the 1.0 s gap counts (≥ 0.3 s)
        self.assertAlmostEqual(f["mean_length_of_run"], 4.0)     # runs of 4 and 4 words
        self.assertAlmostEqual(f["speech_rate_wpm"], 48.0)       # 8 words in 10 s
        self.assertAlmostEqual(f["fillers_per_min"], 6.0)        # one filler in 10 s
        self.assertEqual(f["repetitions"], 1)                    # "I I"
        self.assertEqual(f["self_corrections"], 1)               # "cook-"

    def test_empty_turn(self):
        f = turn_features([], duration_s=3.0)
        self.assertEqual((f["words"], f["speech_s"], f["mean_length_of_run"]), (0, 0.0, 0.0))

    def test_session_features_weight_by_duration(self):
        a = turn_features(WORDS, 10.0)
        s = session_features([(a, 10.0), (a, 10.0)])
        self.assertAlmostEqual(s["speech_s"], 8.0)
        self.assertAlmostEqual(s["pause_ratio"], 0.1)
        self.assertEqual(s["repetitions"], 2)
        self.assertAlmostEqual(s["speech_rate_wpm"], 48.0)
