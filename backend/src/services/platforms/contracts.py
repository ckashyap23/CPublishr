from abc import ABC, abstractmethod


class PlatformAdapter(ABC):
    platform: str

    @abstractmethod
    def transform(self, master_document: str, context: dict) -> dict:
        raise NotImplementedError
