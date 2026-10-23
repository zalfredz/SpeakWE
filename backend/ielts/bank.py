"""ORM -> flow dataclasses. Only approved items leave this module."""
from .flow import Bank, Card, Item, Topic
from .models import CueCard, Part1Topic, Status


def load_bank() -> Bank:
    topics = [
        Topic(f"p1t:{t.pk}", t.title, [Item(f"p1q:{q.pk}", q.text) for q in t.questions.all()])
        for t in Part1Topic.objects.filter(status=Status.APPROVED).prefetch_related("questions").order_by("pk")
    ]
    cards = [
        Card(f"card:{c.pk}", c.title, list(c.bullets), c.closing, c.theme,
             [Item(f"ro:{q.pk}", q.text) for q in c.rounding_off.all()],
             [Item(f"p3q:{q.pk}", q.text) for q in c.part3.all()])
        for c in CueCard.objects.filter(status=Status.APPROVED).prefetch_related("rounding_off", "part3").order_by("pk")
    ]
    return Bank(topics, cards)
