import copy
from unittest import TestCase

from ielts.assessment.scoring import overall
from ielts.assessment.validate import fix_priority_order, validate

SEGMENTS = {
    "t1-1": {"turn_id": "t1", "start_ms": 0, "end_ms": 7450, "text": "Um, I think the thing I like most is, uh, the food[?], because there is many street food near my house."},
    "t2-1": {"turn_id": "t2", "start_ms": 0, "end_ms": 8900, "text": "Yes, I- I go there every weekend with my friends and we, um, we usually try new place."},
    "t3-1": {"turn_id": "t3", "start_ms": 0, "end_ms": 26300, "text": "she was very worried that she will lose her money, so I explained it step by step"},
}


def ev(kind, seg, quote, **extra):
    s = SEGMENTS[seg]
    return {"type": kind, "turn_id": s["turn_id"], "segment_id": seg, "start_ms": s["start_ms"], "end_ms": s["end_ms"],
            "quote": quote, "observation_id": "catatan", **extra}


def crit(band, evidence):
    return {"band": band, "descriptor_fit_id": "x", "evidence": evidence, "why_not_higher_id": "x", "why_not_lower_id": "x"}


def valid_output():
    return {
        "status": "ready", "scope": "full_test",
        "criteria": {
            "fc": crit(6, [ev("strength", "t3-1", "so I explained it step by step"), ev("limitation", "t2-1", "I- I go there every weekend")]),
            "lr": crit(6, [ev("strength", "t3-1", "she was very worried"), ev("limitation", "t2-1", "try new place")]),
            "gra": crit(6, [ev("strength", "t3-1", "so I explained it"), ev("limitation", "t1-1", "there is many street food")]),
            "p": crit(7, [ev("strength", "t3-1", "step by step"), ev("limitation", "t1-1", "the food", heard_as="the fud")]),
        },
        "asr_suspected": [],
        "feedback": {"summary_id": "ringkas", "priorities": [{"criterion": "fc", "title_id": "a", "explanation_id": "b",
                                                              "evidence_segment_ids": ["t2-1"], "drill_id": "c"}],
                     "upgrade_opportunities": []},
    }


class OverallTests(TestCase):
    def test_ielts_rounding(self):
        cases = [((6, 6, 6, 7), 6.5), ((6, 6, 7, 7), 6.5), ((6, 7, 7, 7), 7.0), ((5, 5, 5, 6), 5.5), ((7, 7, 7, 7), 7.0)]
        for bands, expected in cases:
            self.assertEqual(overall(dict(zip(["fc", "lr", "gra", "p"], bands)), "full_test"), expected, bands)

    def test_only_for_full_test_with_all_bands(self):
        self.assertIsNone(overall({"fc": 6, "lr": 6, "gra": 6, "p": 6}, "part1_only"))
        self.assertIsNone(overall({"fc": 6, "lr": None, "gra": 6, "p": 6}, "full_test"))


class ValidateTests(TestCase):
    def check(self, mutate, needle):
        out = valid_output()
        mutate(out)
        errors = validate(out, SEGMENTS, "full_test")
        self.assertTrue(any(needle in e for e in errors), errors)

    def test_valid_sample_passes(self):
        self.assertEqual(validate(valid_output(), SEGMENTS, "full_test"), [])

    def test_quote_must_exist_in_segment(self):
        self.check(lambda o: o["criteria"]["lr"]["evidence"][1].update(quote="invented words"), "quote")

    def test_quote_matching_ignores_asr_markers_case_and_spacing(self):
        out = valid_output()
        out["criteria"]["p"]["evidence"][1]["quote"] = "THE   food"
        self.assertEqual(validate(out, SEGMENTS, "full_test"), [])

    def test_seg_prefix_is_accepted(self):
        out = valid_output()
        out["criteria"]["fc"]["evidence"][0]["segment_id"] = "seg t3-1"
        self.assertEqual(validate(out, SEGMENTS, "full_test"), [])

    def test_timestamps_must_match_segment(self):
        self.check(lambda o: o["criteria"]["fc"]["evidence"][0].update(start_ms=5), "timestamp")

    def test_unknown_segment(self):
        self.check(lambda o: o["criteria"]["fc"]["evidence"][0].update(segment_id="t9-9"), "unknown segment")

    def test_band_range_and_type(self):
        self.check(lambda o: o["criteria"]["fc"].update(band=10), "band")
        self.check(lambda o: o["criteria"]["fc"].update(band=6.5), "band")

    def test_needs_two_evidence_items_and_a_limitation_below_9(self):
        self.check(lambda o: o["criteria"]["fc"].update(evidence=o["criteria"]["fc"]["evidence"][:1]), "2 evidence")
        self.check(lambda o: o["criteria"]["fc"]["evidence"][1].update(type="strength"), "limitation")

    def test_pronunciation_limitation_needs_heard_as(self):
        self.check(lambda o: o["criteria"]["p"]["evidence"][1].pop("heard_as"), "heard_as")

    def test_overall_must_not_be_sent(self):
        self.check(lambda o: o.update(overall=6.5), "overall")

    def test_scope_must_match_session(self):
        out = valid_output()
        self.assertTrue(any("scope" in e for e in validate(out, SEGMENTS, "part1_only")))

    def test_fc_first_priority_when_fc_is_lowest(self):
        def m(o):
            o["feedback"]["priorities"][0]["criterion"] = "lr"
        self.check(m, "priority")

    def test_same_limitation_in_two_criteria(self):
        def m(o):
            o["criteria"]["lr"]["evidence"][1] = copy.deepcopy(o["criteria"]["gra"]["evidence"][1])
        self.check(m, "more than one criterion")

    def test_null_band_needs_no_evidence(self):
        out = valid_output()
        out["status"] = "insufficient_evidence"
        for k in out["criteria"]:
            out["criteria"][k].update(band=None, evidence=[])
        self.assertEqual(validate(out, SEGMENTS, "full_test"), [])

    def test_malformed_shapes_return_errors_instead_of_crashing(self):
        for mutate in (lambda o: o["criteria"].update(fc=None),
                       lambda o: o["criteria"]["fc"].update(evidence=["just a string"]),
                       lambda o: o["feedback"].update(priorities=["a string"]),
                       lambda o: o.update(feedback="nope")):
            out = valid_output()
            mutate(out)
            self.assertTrue(validate(out, SEGMENTS, "full_test"))

    def test_turn_id_must_match_the_segment(self):
        self.check(lambda o: o["criteria"]["fc"]["evidence"][0].update(turn_id="t7"), "turn_id")
        self.check(lambda o: o["criteria"]["fc"]["evidence"][0].pop("turn_id"), "turn_id")

    def test_quote_may_skip_a_filler_or_repetition_but_not_invent_words(self):
        segs = {"t5-1": {"turn_id": "t5", "start_ms": 0, "end_ms": 9000,
                         "text": "when-[?] because I-[?] I am a computer science student, right, so I very,[?] very close"}}
        def out(quote):
            o = valid_output()
            for k in o["criteria"]:
                o["criteria"][k].update(band=None, evidence=[])
            o["criteria"]["gra"].update(band=6, evidence=[
                {"type": "strength", "turn_id": "t5", "segment_id": "t5-1", "start_ms": 0, "end_ms": 9000, "quote": "a computer science student", "observation_id": "o"},
                {"type": "limitation", "turn_id": "t5", "segment_id": "t5-1", "start_ms": 0, "end_ms": 9000, "quote": quote, "observation_id": "o"}])
            o["feedback"]["priorities"][0]["criterion"] = "gra"
            o["feedback"]["priorities"][0]["evidence_segment_ids"] = ["t5-1"]
            return o
        self.assertEqual(validate(out("because I am a computer science student, right, so I very, very close"), segs, "full_test"), [])
        self.assertTrue(validate(out("because I am a software engineering student"), segs, "full_test"))

    def test_fc_priority_is_moved_first_by_the_server(self):
        out = valid_output()
        out["feedback"]["priorities"] = [{"criterion": "lr", "title_id": "a", "explanation_id": "b", "evidence_segment_ids": ["t2-1"], "drill_id": "c"},
                                         {"criterion": "fc", "title_id": "d", "explanation_id": "e", "evidence_segment_ids": ["t2-1"], "drill_id": "f"}]
        fix_priority_order(out)
        self.assertEqual([p["criterion"] for p in out["feedback"]["priorities"]], ["fc", "lr"])
        self.assertEqual(validate(out, SEGMENTS, "full_test"), [])
