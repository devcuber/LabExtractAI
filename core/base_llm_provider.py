from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):

    @abstractmethod
    def ask(self, prompt: str) -> str:
        ...