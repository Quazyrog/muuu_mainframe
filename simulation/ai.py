from random import random
from .world import EventCode, Creator


class SimpleMarkovAI:
    """
    Pomysł drugiej grupy na łańcuch Markowa.
    Z pewnym prawdopodobieństwem kupuje pierwszego mainframe.
    Później z pewnym prawdopodobieństwem kupuje nową generację w dniu jej wyjścia.
    Jeżeli nie kupi iluś kolejnych nowych generacji, zupełnie rezygnuje.
    """

    def __init__(self, renew_probability, buy_first_probability, max_stagnancy):
        self._state = None
        self._q = buy_first_probability
        self._p = renew_probability
        self._max = max_stagnancy

    def __call__(self, entreprise, notifications):
        for n in notifications:
            if n["code"] is not EventCode.MAINFRAME_RELEASED:
                continue
            if self._state is None:
                if random() <= self._q:
                    entreprise.buy(n["name"], 1)
                    self._state = 0
            elif self._state < self._max:
                if random() < self._p:
                    entreprise.buy(n["name"], 1)
                    self._state = 0
                else:
                    self._state += 1

    NAME = "SIMPLE_MARKOV"


class GrowingMarkovAI:
    """
    - Działa z rozdzielczością jednego miesiąca.
    - Nieposiadając komputerów z prawdopodobieństwem `p_engage` kupuje `init_size` najnowszego modelu
    - Z prawdopodobieństwem `p_grow` zwiększa zapotrzebowanie na komputery o `growth` i dokupuje najbliższy
    - Po HWFDM z prawdopodobieństwem `p_renew` wymienia komputery na najnowsze
    - Po EOS z prawdopodobieństwem `p_resign` wycowuje się, wpp odnawia na najnowsze
    """

    NAME = "GROWING_MARKOV"
    _mainframes = {}
    _latest_mainframe = ""

    @staticmethod
    def _mainframe_available(name):
        if name == GrowingMarkovAI._latest_mainframe:
            return
        if GrowingMarkovAI._latest_mainframe:
            GrowingMarkovAI._mainframes[GrowingMarkovAI._latest_mainframe]["next"] = name
        GrowingMarkovAI._latest_mainframe = name
        GrowingMarkovAI._mainframes[name] = {"avail": True, "next": None, "name": name}

    @staticmethod
    def _mainframe_unavailable(name):
        GrowingMarkovAI._mainframes[name]["avail"] = False

    @staticmethod
    def _find_nearest(name):
        mf = GrowingMarkovAI._mainframes[name]
        while mf and not mf["avail"]:
            mf = GrowingMarkovAI._mainframes.get(mf["next"], None)
        return mf["name"]

    def __init__(self, **kwargs):
        self.init_size = kwargs["init_size"]
        self.growth = kwargs["growth"]
        self.p_engage = kwargs["p_engage"]
        self.p_grow = kwargs["p_grow"]
        self.p_renew = kwargs["p_renew"]
        self.p_resign = kwargs["p_resign"]

        self._owned_model = None
        self._own_withdrawn = False
        self._own_outdated = False
        self._dead = False
        self._size = 0

    def __call__(self, enterprise, notifications):
        for n in notifications:
            if n["code"] is EventCode.MAINFRAME_RELEASED:
                GrowingMarkovAI._mainframe_available(n["name"])
            elif n["code"] is EventCode.MAINFRAME_WITHDRAWN:
                GrowingMarkovAI._mainframe_unavailable(n["name"])
                if self._owned_model == n["name"]:
                    self._own_withdrawn = False
            elif n["code"] is EventCode.MAINFRAME_END_OF_SUPPORT and n["name"] == self._owned_model:
                self._own_outdated = True
        if enterprise.get_time().day != 1:
            return

        if self._dead:
            return

        # Not in the maket yet --> buy your first IBM Mainframe today
        if not self._owned_model:
            if random() < self.p_engage:
                self._owned_model = GrowingMarkovAI._latest_mainframe
                enterprise.buy(self._owned_model, self.init_size)
                self._size = self.init_size
            return

        # Your hardware is ancient! You look bad...
        if self._own_outdated:
            if random() < self.p_resign:
                self._dead = True
            else:
                self.renew_all(enterprise)
            return

        # You're running old hardware; maybe buy newer version?
        if self._own_withdrawn and random() < self.p_renew:
            self.renew_all(enterprise)
            return

        # You seem like you could use more computational power
        if random() < self.p_grow:
            enterprise.buy(GrowingMarkovAI._find_nearest(self._owned_model), self.growth)
            self._size += self.growth
            return

    def renew_all(self, enterprise):
        enterprise.buy(GrowingMarkovAI._latest_mainframe, self._size)
        self._owned_model = GrowingMarkovAI._latest_mainframe
        self._own_withdrawn = False
        self._own_outdated = False



def default_creator():
    c = Creator()
    c.register_ai(SimpleMarkovAI)
    c.register_ai(GrowingMarkovAI)
    return c