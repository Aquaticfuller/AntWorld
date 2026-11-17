"""Bounded live projection of the canonical journal. The archive holds the full record."""

from collections import OrderedDict, deque


LANDMARKS = ("egg", "hatch", "worker", "exit", "delivery", "excavation", "nursing", "trophallaxis", "queen-death")
LIFE = {"AntSeeded", "AntBorn", "StageChanged", "AntDied"}
ACTIVITY = {"FoodCollected", "FoodDelivered", "NutritionTransferred", "FoundingRation", "BroodMoved",
            "SoilExcavated", "SoilDropped", "RecruitmentActivated", "FoundressWaterIngested", "FoundressNestMeal"}


class Chronicle:
    def __init__(self):
        self.cursor = 0
        self.first = {}
        self.underground = set()
        self.life = {}
        self.recent = OrderedDict()

    def accept(self, event, frame):
        self.cursor = int(event["id"])
        actor = event["actor"]
        kind, stage = event["kind"], event["stage"]
        ant = frame["ants"].get(int(actor)) if actor else None
        worker = ant is not None and ant["caste"] == 0 and stage == "Adult"
        if kind in LIFE and actor:
            self.life.setdefault(actor, []).append(self.cursor)
        if kind in ACTIVITY and actor:
            for identity in {actor, event["related"]} - {None}:
                if identity not in self.recent:
                    self.recent[identity] = deque(maxlen=12)
                self.recent[identity].append(event)
                self.recent.move_to_end(identity)
            if len(self.recent) > 256:
                self.recent.popitem(last=False)

        name = None
        if kind == "AntBorn" and stage == "Egg":
            name = "egg"
        elif kind == "StageChanged" and stage == "Larva":
            name = "hatch"
        elif kind == "StageChanged" and worker:
            name = "worker"
        elif kind == "FoodDelivered" and worker and sum(event["mass_ug"]) > event["mass_ug"][2]:
            name = "delivery"
        elif kind == "SoilExcavated" and worker:
            name = "excavation"
        elif kind == "FoundingRation" and sum(event["mass_ug"]):
            name = "nursing"
        elif kind == "NutritionTransferred" and sum(event["mass_ug"]):
            name = "trophallaxis"
        elif kind == "AntDied" and ant and ant["caste"] == 1:
            name = "queen-death"
        if "exit" not in self.first and actor:
            if kind == "AntDied":
                self.underground.discard(actor)
            if worker and kind in {"AntSeeded", "StageChanged", "Moved"}:
                if event["position_m"][1] < frame["surface"]["origin_m"][1]:
                    self.underground.add(actor)
                elif actor in self.underground:
                    self.underground.remove(actor)
                    if kind == "Moved":
                        name = "exit"
                        self.underground.clear()
        if name:
            self.first.setdefault(name, event)
