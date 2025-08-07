from ..base_interfaces import BasePreprocessor, BaseMinifier

class KotlinPreprocessor(BasePreprocessor):
    def preprocess(self, file_path: str, include_paths: list[str]) -> str:
        return f"// Kotlin Preprocessor: Preprocessing {file_path}\n// Includes: {include_paths}\n// (Dummy content for Kotlin preprocessing)"

    def get_supported_languages(self) -> list[str]:
        return ["kotlin"]

class KotlinMinifier(BaseMinifier):
    def minify(self, file_path: str) -> str:
        return f"// Kotlin Minifier: Minifying {file_path}\n// (Dummy content for Kotlin minification)"

    def get_supported_languages(self) -> list[str]:
        return ["kotlin"]

