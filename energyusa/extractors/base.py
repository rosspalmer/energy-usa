from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, mode: str, start_date: str = None, end_date: str = None):
        pass
