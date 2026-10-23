"""Pure IELTS session flow: bank snapshot in, ordered list of steps out. No ORM imports."""
import random
from dataclasses import dataclass
from typing import Literal, TypedDict


@dataclass(frozen=True)
class Item:
    id: str
    text: str


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    questions: list[Item]


@dataclass(frozen=True)
class Card:
    id: str
    title: str
    bullets: list[str]
    closing: str
    theme: str
    rounding_off: list[Item]
    part3: list[Item]


@dataclass(frozen=True)
class Bank:
    part1_topics: list[Topic]
    cue_cards: list[Card]


MODES = ("part1", "part2", "part3", "full")

# Original wording spoken by Mimo (not copied from official IELTS scripts).
INSTRUCTIONS = {
    "part1_intro": "Let's begin with Part 1. I'm going to ask you some questions about yourself and familiar topics.",
    "part2_intro": "Now let's move on to Part 2. I'm going to give you a topic. You'll have one minute to prepare, "
                   "and then I'd like you to talk about it for one to two minutes.",
    "part2_start": "Your preparation time is over. Please start speaking now.",
    "part3_intro": "We've been talking about {theme}. Now I'd like to ask you some more general questions related to this.",
    "end": "Thank you. That is the end of the speaking test.",
}


class Step(TypedDict):
    index: int
    part: int
    kind: Literal["instruction", "question", "prep", "long_turn"]
    text: str
    item_id: str | None
    max_answer_s: int | None
    prep_s: int | None


class BankTooSmall(Exception):
    pass


def _step(part, kind, text, item_id=None, max_answer_s=None, prep_s=None):
    return {"part": part, "kind": kind, "text": text, "item_id": item_id, "max_answer_s": max_answer_s, "prep_s": prep_s}


def _card_text(card: Card) -> str:
    return card.title + "\nYou should say:\n" + "\n".join(card.bullets) + "\n" + card.closing


def _part1(bank, rng, cfg):
    n = cfg["PART1_TOPICS"]
    topics = [t for t in bank.part1_topics if t.questions]
    if len(topics) < n:
        raise BankTooSmall(f"Part 1 needs {n} approved topics with questions, found {len(topics)}.")
    steps = [_step(1, "instruction", INSTRUCTIONS["part1_intro"])]
    for topic in rng.sample(topics, n):
        steps += [_step(1, "question", q.text, q.id, cfg["MAX_ANSWER_S"][1])
                  for q in topic.questions[:cfg["PART1_QUESTIONS_PER_TOPIC"]]]
    return steps


def _pick_card(bank, rng, need_part3):
    cards = [c for c in bank.cue_cards if c.part3 or not need_part3]
    if not cards:
        raise BankTooSmall("No approved cue card" + (" with Part 3 questions." if need_part3 else "."))
    return rng.choice(cards)


def _part2(card, cfg):
    text = _card_text(card)
    return ([_step(2, "instruction", INSTRUCTIONS["part2_intro"]),
             _step(2, "prep", text, card.id, prep_s=cfg["PART2_PREP_S"]),
             _step(2, "instruction", INSTRUCTIONS["part2_start"]),
             _step(2, "long_turn", text, card.id, cfg["PART2_TALK_S"])]
            + [_step(2, "question", q.text, q.id, cfg["MAX_ANSWER_S"][1]) for q in card.rounding_off[:cfg["ROUNDING_OFF_MAX"]]])


def _part3(card, cfg):
    return ([_step(3, "instruction", INSTRUCTIONS["part3_intro"].format(theme=card.theme))]
            + [_step(3, "question", q.text, q.id, cfg["MAX_ANSWER_S"][3]) for q in card.part3])


def build_plan(mode: str, bank: Bank, seed: int, cfg: dict) -> list[Step]:
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")
    rng = random.Random(seed)
    steps = []
    if mode in ("part1", "full"):
        steps += _part1(bank, rng, cfg)
    if mode != "part1":
        card = _pick_card(bank, rng, need_part3=mode in ("part3", "full"))
        if mode in ("part2", "full"):
            steps += _part2(card, cfg)
        if mode in ("part3", "full"):
            steps += _part3(card, cfg)
    steps.append(_step(steps[-1]["part"], "instruction", INSTRUCTIONS["end"]))
    return [{"index": i, **s} for i, s in enumerate(steps)]
