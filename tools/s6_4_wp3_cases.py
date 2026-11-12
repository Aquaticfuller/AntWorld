"""Frozen WP-3 simulation inputs. Seeds represent software variation."""

from dataclasses import dataclass
from itertools import product


SEEDS = (1, 7, 19, 42, 43, 97)
SIGNALS = ("absent", "blind", "present")
AGES = ("fresh", "aged", "expired")


@dataclass(frozen=True)
class Case:
    family: str
    layout: str
    signal: str
    memory: int
    age: str
    seed: int

    @property
    def key(self):
        return "-".join(self.arguments())

    def arguments(self):
        return tuple(map(str, (self.family, self.layout, self.signal, self.memory, self.age, self.seed)))


def matrix():
    yield from (Case("factorial", layout, signal, memory, "fresh", seed)
                for layout, signal, memory, seed in product(("near", "far"), SIGNALS, (0, 1), SEEDS))
    yield from (Case("scout", "near", signal, 0, age, seed)
                for signal, age, seed in product(SIGNALS, AGES, SEEDS))
    yield from (Case("disruption", layout, "absent", 1, "fresh", seed)
                for layout, seed in product(("open", "wall", "gap", "deplete", "empty"), SEEDS))
    yield from (Case("density", layout, "present", 0, "fresh", seed)
                for layout, seed in product(("sparse8", "dense8", "dense32"), SEEDS))
    yield from (Case("prepared", "straight", signal, 0, age, seed)
                for signal, age, seed in product(SIGNALS, AGES, SEEDS))
