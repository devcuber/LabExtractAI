from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):

    @abstractmethod
    def ask(self, prompt: str) -> str:
        ...

    @abstractmethod
    def ask_with_file(self, prompt: str, file_bytes: bytes, mime_type: str = "application/pdf") -> str:
        ...