from unittest import TestCase

from django.conf import settings

from ielts.flow import INSTRUCTIONS, Bank, BankTooSmall, Card, Item, Topic, build_plan

CFG = settings.SPEAKWE


def make_bank(n_topics=4, n_cards=2, part3=5):
    topics = [Topic(f"p1t:{t}", f"topic {t}", [Item(f"p1q:{t}-{q}", f"t{t} q{q}") for q in range(5)])
              for t in range(n_topics)]
    cards = [Card(f"card:{c}", f"Describe thing {c}.", ["a", "b", "c", "d"], "and explain why.", f"theme {c}",
                  [Item(f"ro:{c}-{i}", f"ro {c}-{i}") for i in range(2)],
                  [Item(f"p3q:{c}-{i}", f"p3 {c}-{i}") for i in range(part3)])
             for c in range(n_cards)]
    return Bank(topics, cards)


def kinds(plan):
    return [s["kind"] for s in plan]


class FlowTests(TestCase):
    def test_full_plan_shape(self):
        plan = build_plan("full", make_bank(), seed=1, cfg=CFG)
        expected = (["instruction"] + ["question"] * 12 + ["instruction", "prep", "instruction", "long_turn"]
                    + ["question"] * 2 + ["instruction"] + ["question"] * 5 + ["instruction"])
        self.assertEqual(kinds(plan), expected)
        self.assertEqual([s["index"] for s in plan], list(range(len(plan))))

    def test_full_plan_part3_uses_part2_card(self):
        plan = build_plan("full", make_bank(), seed=3, cfg=CFG)
        card_id = next(s["item_id"] for s in plan if s["kind"] == "long_turn")
        suffix = card_id.split(":")[1]
        part3 = [s for s in plan if s["part"] == 3 and s["kind"] == "question"]
        self.assertTrue(part3)
        self.assertTrue(all(s["item_id"].startswith(f"p3q:{suffix}-") for s in part3))

    def test_part3_intro_mentions_theme(self):
        bank = make_bank()
        plan = build_plan("full", bank, seed=2, cfg=CFG)
        card_id = next(s["item_id"] for s in plan if s["kind"] == "long_turn")
        card = next(c for c in bank.cue_cards if c.id == card_id)
        intro = next(s for s in plan if s["part"] == 3 and s["kind"] == "instruction")
        self.assertEqual(intro["text"], INSTRUCTIONS["part3_intro"].format(theme=card.theme))

    def test_limits_from_cfg(self):
        plan = build_plan("full", make_bank(), seed=1, cfg=CFG)
        p1 = [s for s in plan if s["part"] == 1 and s["kind"] == "question"]
        self.assertTrue(all(s["max_answer_s"] == 60 for s in p1))
        self.assertEqual(next(s for s in plan if s["kind"] == "long_turn")["max_answer_s"], 120)
        self.assertEqual(next(s for s in plan if s["kind"] == "prep")["prep_s"], 60)

    def test_same_seed_same_plan(self):
        bank = make_bank()
        self.assertEqual(build_plan("full", bank, 1, CFG), build_plan("full", bank, 1, CFG))

    def test_different_seed_can_differ(self):
        bank = make_bank()
        picks = {tuple(s["item_id"] for s in build_plan("part1", bank, seed, CFG)) for seed in range(1, 21)}
        self.assertGreater(len(picks), 1)

    def test_part_only_modes(self):
        bank = make_bank()
        self.assertNotIn("long_turn", kinds(build_plan("part1", bank, 1, CFG)))
        self.assertFalse([s for s in build_plan("part2", bank, 1, CFG) if s["part"] == 1])
        p3 = build_plan("part3", bank, 1, CFG)
        self.assertTrue(all(s["kind"] == "instruction" or (s["part"] == 3 and s["kind"] == "question") for s in p3))

    def test_bank_too_small_raises(self):
        for mode in ("part1", "full"):
            with self.assertRaises(BankTooSmall):
                build_plan(mode, make_bank(n_topics=2), 1, CFG)
        for mode in ("part2", "part3", "full"):
            with self.assertRaises(BankTooSmall):
                build_plan(mode, make_bank(n_cards=0), 1, CFG)
        with self.assertRaises(BankTooSmall):
            build_plan("part3", make_bank(part3=0), 1, CFG)

    def test_topics_without_questions_do_not_count(self):
        bank = make_bank(n_topics=3)
        empty = [Topic(t.id, t.title, []) for t in bank.part1_topics]
        with self.assertRaises(BankTooSmall):
            build_plan("part1", Bank(empty, bank.cue_cards), 1, CFG)

    def test_unknown_mode_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_plan("daily", make_bank(), 1, CFG)
