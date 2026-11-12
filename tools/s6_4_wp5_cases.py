"""Frozen WP-5 inputs. Seeds identify paired software worlds."""

from dataclasses import dataclass
from itertools import product

from s6_4_wp4_cases import SEEDS


@dataclass(frozen=True)
class Case:
    family: str
    arm: str
    workers: int
    seed: int

    @property
    def key(self):
        return "-".join(self.arguments())

    def arguments(self):
        return tuple(map(str, (self.family, self.arm, self.workers, self.seed)))


def matrix():
    yield from (Case("founding", arm, 0, seed) for arm, seed in product(("off", "on"), SEEDS))
    yield from (Case("worker-reserve", "half", workers, seed) for workers, seed in product((8, 32), SEEDS))
    yield from (Case("excavation", arm, workers, seed) for arm, workers, seed in product(
        ("compact", "wet", "roomy", "isolated", "shielded"), (4, 8, 32), SEEDS))
    yield from (Case("joint", arm, workers, seed) for arm, workers, seed in product(("depot", "empty"), (8, 32), SEEDS))
    yield Case("gate", "reopen", 2, 1)
