"""Pure session status machine (parent spec §3.3). active→abandoned is the "Akhiri sesi" button."""

TRANSITIONS: dict[str, set[str]] = {
    "created": {"mic_check"},
    "mic_check": {"active"},
    "active": {"interrupted", "finalizing", "abandoned"},
    "interrupted": {"active", "abandoned"},
    "finalizing": {"completed"},
    "completed": set(),
    "abandoned": set(),
}


class InvalidTransition(Exception):
    pass


def can_transition(src: str, dst: str) -> bool:
    return dst in TRANSITIONS.get(src, set())


def check(src: str, dst: str) -> None:
    if not can_transition(src, dst):
        raise InvalidTransition(f"{src} → {dst} is not allowed")
