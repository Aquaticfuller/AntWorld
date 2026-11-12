"""Frozen WP-4 cases. Seeds measure software variation."""

from dataclasses import dataclass
from itertools import product


SEEDS = (1, 7, 19, 42, 43, 97)
SUPPLY = ("depot", "ordinary", "scarce", "empty")
CLOCKS = ("legacy", "borisovka", "st-petersburg")


@dataclass(frozen=True)
class Case:
    family: str
    arm: str
    workers: int
    profile: str
    seed: int

    @property
    def key(self):
        return "-".join(self.arguments())

    def arguments(self):
        return tuple(map(str, (self.family, self.arm, self.workers, self.profile, self.seed)))


def matrix():
    yield from (Case("ecology", supply, workers, "legacy", seed)
                for supply, workers, seed in product(SUPPLY, (0, 8, 32), SEEDS))
    yield from (Case("reserve", "ordinary", workers, "legacy", seed)
                for workers, seed in product((0, 8), SEEDS))
    yield from (Case("clock", arm, 0, profile, 1)
                for profile, arm in product(CLOCKS, ("seed", "funded", "sentinel")))
    yield Case("clock", "energy-tie", 0, "borisovka", 1)
    yield Case("clock", "energy-tie", 0, "st-petersburg", 1)
    yield Case("clock", "water-tie", 0, "legacy", 1)
    yield Case("clock", "interrupted", 0, "legacy", 1)
    yield from (Case("pulse", arm, 1, "legacy", 1) for arm in ("none", "sham", "before", "on"))
    yield from (Case("brood", arm, 3, "legacy", 1) for arm in ("full", "low-protein", "none"))
