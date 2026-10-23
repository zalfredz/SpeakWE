"""Overall band is computed here, never by the model (prompt doc §1)."""
import math

CRITERIA = ("fc", "lr", "gra", "p")


def overall(bands: dict, scope: str) -> float | None:
    """IELTS convention: mean of the four criteria; .25 rounds up to .5, .75 up to the next whole band."""
    values = [bands.get(k) for k in CRITERIA]
    if scope != "full_test" or any(v is None for v in values):
        return None
    mean = round(sum(values) / 4 * 4) / 4          # quarter steps are exact for four whole-number bands
    whole = math.floor(mean)
    frac = mean - whole
    return float(whole if frac < 0.25 else whole + 0.5 if frac < 0.75 else whole + 1)
