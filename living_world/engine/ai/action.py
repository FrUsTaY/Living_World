from abc import ABC, abstractmethod

class Action(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        pass

    @abstractmethod
    def calculate_utility(self, npc, simulation, time_dict) -> float:
        pass

    @abstractmethod
    def execute(self, npc, simulation, time_dict):
        pass
