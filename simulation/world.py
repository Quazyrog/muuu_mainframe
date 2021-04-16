#!/usr/bin/python3
import csv
from datetime import date, timedelta
from enum import Enum


class EventCode(Enum):
    MAINFRAME_RELEASED = "MAINFRAME_RELEASED"
    MAINFRAME_WITHDRAWN = "MAINFRAME_WITHDRAWN"
    MAINFRAME_END_OF_SUPPORT = "MAINFRAME_END_OF_SUPPORT"
    BOUGHT_VOLUME_INCREASED = "BOUGHT_VOLUME_INCREASED"

class Transaction:
    def __init__(self, buyer, product, volume, time):
        self.buyer = buyer
        self.product = product
        self.volume = volume
        self.timestamp = time


class World:
    def __init__(self, start_date: date):
        self._time = start_date
        self._start_time = start_date
        self._entreprises = []
        self._products = {}
        self._changed_volumes = set()
        self._broadcasts = []
        self._timeline = []
        self._timeline_index = None

    def broadcast(self, code, **kwargs):
        kwargs["code"] = code
        self._broadcasts.append(kwargs)

    def schedule_broadcast(self, time: date, code, **kwargs):
        assert time >= self._time
        kwargs["code"] = code
        self._timeline.append((time, kwargs))
        self._timeline_index = None

    def step(self):
        if self._timeline_index is None:
            self._timeline_index = 0
            self._timeline.sort(key=lambda ev: ev[0])
        while self._timeline_index < len(self._timeline) \
                and (event := self._timeline[self._timeline_index])[0] <= self._time:
            if event[0] == self._time:
                self._broadcasts.append(event[1])
            self._timeline_index += 1
        self._time += timedelta(days=1)

        for b in self._broadcasts:
            if b["code"] is EventCode.MAINFRAME_RELEASED:
                self._products[b["name"]] = {"available": True, "history": [], "volume": 0}
            elif b["code"] is EventCode.MAINFRAME_WITHDRAWN:
                self._products[b["name"]]["available"] = False

        # prepare broadcasts
        for family in self._changed_volumes:
            self.broadcast(EventCode.BOUGHT_VOLUME_INCREASED, family=family)
        self._changed_volumes.clear()
        # step entreprises
        for e in self._entreprises:
            for b in self._broadcasts:
                e._notifications.append(b)
            e._step()
        self._broadcasts.clear()

    def register_buying(self, buyer, product, volume):
        if product not in self._products:
            raise KeyError(f"invalid product name '{product}'")
        if volume < 1:
            raise ValueError("illegal volume")
        v = self._products[product]
        if not v["available"]:
            raise RuntimeError("Product bought after withdraval")
        v["volume"] += volume
        v["history"].append(Transaction(buyer, product, volume, self._time))
        self._changed_volumes.add(product)

    def run_until(self, time: date):
        while self._time < time:
            self.step()

    def released_products(self):
        yield from self._products

    def transactions(self, product_name):
        yield from self._products[product_name]["history"]

    @property
    def time(self):
        return self._time

    @property
    def start_time(self):
        return self._start_time


class Enterprise:
    def __init__(self, ai):
        self._simulation = None
        self._ai = ai
        self._notifications = []

    def bind(self, world):
        assert self._simulation is None
        self._simulation = world
        world._entreprises.append(self)

    def _step(self):
        self._ai(self, self._notifications)
        self._notifications.clear()

    def _notify(self, code, **kwargs):
        kwargs["code"] = code
        self._notifications.append(kwargs)

    def buy(self, family, volume):
        self._simulation.register_buying(self, family, volume)

    def get_time(self):
        return self._simulation.time


class Creator:
    def __init__(self):
        self._ais = {}
        self.quiet = True

    def register_ai(self, ai):
        self._ais[ai.NAME] = ai

    def create(self, **config):
        def log(*args, **kwargs):
            if not self.quiet:
                print(*args, **kwargs)

        world = World(config["start_time"])

        for player_data in config["players"]:
            params = player_data.get("ai_params", {})
            ai = self._ais[player_data["ai"]]
            for n in range(player_data.get("ncopies", 1)):
                e = Enterprise(ai(**params))
                e.bind(world)
        with open(config["mainframes_timeline"]) as f:
            for row in csv.DictReader(f):
                if not row["GA"]:
                    continue
                world.schedule_broadcast(date.fromisoformat(row["GA"]), EventCode.MAINFRAME_RELEASED, name=row["Family"])
                if row["HWFM"]:
                    world.schedule_broadcast(date.fromisoformat(row["HWFM"]), EventCode.MAINFRAME_WITHDRAWN, name=row["Family"])
                if row["EOS"]:
                    world.schedule_broadcast(date.fromisoformat(row["EOS"]), EventCode.MAINFRAME_WITHDRAWN, name=row["Family"])
        return world
