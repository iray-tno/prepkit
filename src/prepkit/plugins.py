from abc import ABC, abstractmethod

class BasePreprocessor(ABC):
    @abstractmethod
    def preprocess(self, file_path: str, include_paths: list[str]) -> str:
        pass

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        pass

class BaseMinifier(ABC):
    @abstractmethod
    def minify(self, file_path: str) -> str:
        pass

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        pass
