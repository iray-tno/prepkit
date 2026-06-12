import pytest
import os
from plugins.cpp_plugin import CppPreprocessor, CppMinifier

@pytest.fixture
def cpp_preprocessor():
    return CppPreprocessor()

@pytest.fixture
def cpp_minifier():
    return CppMinifier()

@pytest.fixture
def temp_files(tmp_path):
    # Setup for include resolution tests
    (tmp_path / "constants.hpp").write_text("#pragma once\n#define GREETING \"World\"\n")
    (tmp_path / "header.hpp").write_text("#pragma once\n#include \"constants.hpp\"\n")
    (tmp_path / "main.cpp").write_text("#include <iostream>\n#include \"header.hpp\"\nint main() { std::cout << \"Hello, \" << GREETING << \"!\" << std::endl; return 0; }\n")

    # Setup for comment removal test
    (tmp_path / "comments_test.cpp").write_text("// Single line comment\n/* Multi-line\n * comment */\nint main() { return 0; }\n")

    # Setup for minification test
    (tmp_path / "minify_test.cpp").write_text("\n\n#include <iostream>\n\n// This is a test comment\nint main() {\n    int x = 10; // Another comment\n    /* Block comment */\n    return x;\n}\n")

    # Setup for tunable parameter tests
    (tmp_path / "tune_single.cpp").write_text("constexpr int VALUE = 100;  // @tune\nint main() { return VALUE; }\n")
    (tmp_path / "tune_multiple.cpp").write_text("constexpr double TEMP_START = 1000.0;  // @tune\nconstexpr int BEAM_WIDTH = 50;  // @tune\nconstexpr int MAX_TURNS = 100;  // Fixed\nint main() { return TEMP_START + BEAM_WIDTH + MAX_TURNS; }\n")
    (tmp_path / "tune_types.cpp").write_text("constexpr double PI = 3.14;  // @tune\nconstexpr int COUNT = 10;  // @tune\nconstexpr bool DEBUG = true;  // @tune\nint main() { return 0; }\n")

    return tmp_path

def test_cpp_preprocess_includes(cpp_preprocessor, temp_files):
    main_file = temp_files / "main.cpp"
    output = cpp_preprocessor.preprocess(str(main_file), [str(temp_files)])

    assert "#include <iostream>" in output
    assert "#define GREETING \"World\"" in output
    assert "Hello, \" << GREETING" in output # Ensure replacement happened
    assert "#include \"header.hpp\"" not in output # Ensure local include is removed
    assert "#include \"constants.hpp\"" not in output # Ensure local include is removed

def test_cpp_preprocess_does_not_create_fixed_temp_file(cpp_preprocessor, temp_files, monkeypatch):
    monkeypatch.chdir(temp_files)

    main_file = temp_files / "main.cpp"
    cpp_preprocessor.preprocess(str(main_file), [str(temp_files)])

    assert not (temp_files / "temp_combined.cpp").exists()

def test_cpp_preprocess_comments(cpp_preprocessor, temp_files):
    comments_file = temp_files / "comments_test.cpp"
    output = cpp_preprocessor.preprocess(str(comments_file), [])
    
    assert "// Single line comment" not in output
    assert "/* Multi-line" not in output
    assert "* comment */" not in output
    assert "int main() { return 0; }" in output

def test_cpp_minify(cpp_minifier, temp_files):
    minify_file = temp_files / "minify_test.cpp"
    output = cpp_minifier.minify(str(minify_file))

    # Updated expectations for improved minifier that preserves compilation compatibility
    assert "#include <iostream>" in output  # Includes preserved with proper formatting
    assert "int main(){" in output          # Main function properly minified
    assert "int x = 10;" in output          # Variable declaration minified
    assert "return x;" in output            # Return statement minified
    assert "//" not in output               # Single-line comments removed
    assert "/*" not in output               # Multi-line comments removed
    assert "*/" not in output               # Multi-line comments removed
    # Note: Some whitespace and newlines are preserved for compilation compatibility

def test_cpp_minify_does_not_create_fixed_temp_file(cpp_minifier, temp_files, monkeypatch):
    monkeypatch.chdir(temp_files)

    minify_file = temp_files / "minify_test.cpp"
    cpp_minifier.minify(str(minify_file))

    assert not (temp_files / "temp_minify.cpp").exists()

def test_cpp_tunable_params_single(cpp_preprocessor, temp_files):
    """Test single tunable parameter injection."""
    tune_file = temp_files / "tune_single.cpp"

    # Without defines - should keep original value
    output = cpp_preprocessor.preprocess(str(tune_file), [])
    assert "100" in output

    # With defines - should inject new value
    output = cpp_preprocessor.preprocess(str(tune_file), [], defines={"VALUE": "200"})
    assert "200" in output
    assert "100" not in output

def test_cpp_tunable_params_multiple(cpp_preprocessor, temp_files):
    """Test multiple tunable parameters with selective injection."""
    tune_file = temp_files / "tune_multiple.cpp"

    # Without defines - should keep original values
    output = cpp_preprocessor.preprocess(str(tune_file), [])
    assert "1000.0" in output
    assert "50" in output
    assert "100" in output

    # With selective defines - only marked params replaced
    output = cpp_preprocessor.preprocess(str(tune_file), [],
        defines={"TEMP_START": "1500.0", "BEAM_WIDTH": "75"})
    assert "1500.0" in output
    assert "75" in output
    assert "100" in output  # Fixed parameter unchanged

def test_cpp_tunable_params_types(cpp_preprocessor, temp_files):
    """Test tunable parameter injection with different types."""
    tune_file = temp_files / "tune_types.cpp"

    # Inject different types
    output = cpp_preprocessor.preprocess(str(tune_file), [],
        defines={"PI": "3.14159", "COUNT": "20", "DEBUG": "false"})
    assert "3.14159" in output
    assert "20" in output
    assert "false" in output

def test_cpp_tunable_params_preserves_unmarked(cpp_preprocessor, temp_files):
    """Test that unmarked constexpr declarations are not affected."""
    tune_file = temp_files / "tune_multiple.cpp"

    # Try to define unmarked param - should have no effect
    output = cpp_preprocessor.preprocess(str(tune_file), [],
        defines={"MAX_TURNS": "9999"})
    # MAX_TURNS is not marked with @tune, so should remain 100
    assert "100" in output
    assert "9999" not in output

def test_cpp_tunable_params_marker_removal(cpp_preprocessor, temp_files):
    """Test that @tune markers are removed with comments."""
    tune_file = temp_files / "tune_single.cpp"

    output = cpp_preprocessor.preprocess(str(tune_file), [], defines={"VALUE": "200"})
    # Comments (including @tune markers) should be removed
    assert "@tune" not in output
    assert "//" not in output
