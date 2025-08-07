from ..plugins import BasePreprocessor, BaseMinifier

class RustPreprocessor(BasePreprocessor):
    def preprocess(self, file_path: str, include_paths: list[str]) -> str:
        return f"// Rust Preprocessor: Preprocessing {file_path}\n// Includes: {include_paths}\n// (Dummy content for Rust preprocessing)"

    def get_supported_languages(self) -> list[str]:
        return ["rust"]

class RustMinifier(BaseMinifier):
    def minify(self, file_path: str) -> str:
        return f"// Rust Minifier: Minifying {file_path}\n// (Dummy content for Rust minification)"

    def get_supported_languages(self) -> list[str]:
        return ["rust"]

