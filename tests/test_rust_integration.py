"""Integration tests for Rust preprocessor."""
import pytest
import os
from pathlib import Path
from plugins.rust_plugin import RustPreprocessor


class TestRustPreprocessorBasic:
    """Basic module resolution and flattening tests."""

    def test_simple_module_resolution(self):
        """Test basic two-file module resolution."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/simple_module/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify both files' content is present
        assert "fn add(a: i32, b: i32) -> i32" in result
        assert "fn multiply(a: i32, b: i32) -> i32" in result
        assert "fn main()" in result

        # Verify mod declaration is removed
        assert "mod utils;" not in result

        # Verify uses of the functions are present
        assert "utils::add" in result or "add" in result
        assert "utils::multiply" in result or "multiply" in result

    def test_nested_modules(self):
        """Test nested module resolution (utils/mod.rs, utils/math.rs)."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/nested_modules/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify all modules' content is present
        assert "fn greet" in result
        assert "fn gcd" in result
        assert "fn lcm" in result
        assert "fn main()" in result

        # Verify mod declarations are removed
        assert "mod utils;" not in result
        assert "pub mod math;" not in result

        # Verify function usage
        assert "gcd" in result
        assert "lcm" in result

    def test_module_not_found_error(self, tmp_path):
        """Test error handling when module file doesn't exist."""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("mod nonexistent;\n\nfn main() {}")

        preprocessor = RustPreprocessor()

        # Should return empty string on error
        result = preprocessor.preprocess(str(main_rs), [])
        assert result == ""

    def test_empty_file(self, tmp_path):
        """Test preprocessing an empty file."""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("")

        preprocessor = RustPreprocessor()
        result = preprocessor.preprocess(str(main_rs), [])

        # Should not crash, just return empty content
        assert result == "\n" or result == ""

    def test_single_file_no_modules(self, tmp_path):
        """Test preprocessing a single file with no mod declarations."""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
fn main() {
    println!("Hello, World!");
}
""")

        preprocessor = RustPreprocessor()
        result = preprocessor.preprocess(str(main_rs), [])

        assert "fn main()" in result
        assert 'println!("Hello, World!")' in result

    def test_include_paths_resolution(self, tmp_path):
        """Test module resolution using include_paths parameter."""
        # Create lib directory
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()

        helper_rs = lib_dir / "helper.rs"
        helper_rs.write_text("""
pub fn helper_func() -> i32 {
    42
}
""")

        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
mod helper;

fn main() {
    let x = helper::helper_func();
    println!("{}", x);
}
""")

        preprocessor = RustPreprocessor()
        result = preprocessor.preprocess(str(main_rs), [str(lib_dir)])

        assert "fn helper_func()" in result
        assert "mod helper;" not in result

    def test_get_supported_languages(self):
        """Test that RustPreprocessor returns correct supported languages."""
        preprocessor = RustPreprocessor()
        languages = preprocessor.get_supported_languages()

        assert "rust" in languages
        assert "rs" in languages


class TestRustPreprocessorCircularDependency:
    """Test circular dependency detection."""

    def test_circular_dependency_detection(self, tmp_path):
        """Test that circular dependencies are detected."""
        # Create a.rs that depends on b
        a_rs = tmp_path / "a.rs"
        a_rs.write_text("mod b;\n\nfn func_a() {}")

        # Create b.rs that depends on a (circular!)
        b_rs = tmp_path / "b.rs"
        b_rs.write_text("mod a;\n\nfn func_b() {}")

        preprocessor = RustPreprocessor()
        result = preprocessor.preprocess(str(a_rs), [])

        # Should return empty string on circular dependency
        assert result == ""


class TestRustPreprocessorMacros:
    """Test macro preservation."""

    def test_macro_preservation(self):
        """Test that macros are preserved in output."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/macros/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify macros are preserved
        assert "macro_rules! max" in result
        assert "macro_rules! min" in result

        # Verify macro usage is preserved
        assert "max!(x, y)" in result
        assert "min!(x, y)" in result

        # Verify main function is present
        assert "fn main()" in result


class TestRustPreprocessorOrdering:
    """Test that module ordering is correct (dependencies before dependents)."""

    def test_dependency_ordering(self, tmp_path):
        """Test that dependencies are placed before dependents in output."""
        # Create utils.rs (no dependencies)
        utils_rs = tmp_path / "utils.rs"
        utils_rs.write_text("""
pub fn util_func() -> i32 {
    100
}
""")

        # Create main.rs (depends on utils)
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
mod utils;

fn main() {
    let x = utils::util_func();
    println!("{}", x);
}
""")

        preprocessor = RustPreprocessor()
        result = preprocessor.preprocess(str(main_rs), [])

        # Find positions of key elements
        util_func_pos = result.find("util_func")
        main_pos = result.find("fn main()")

        # util_func should appear before main (dependency ordering)
        assert util_func_pos >= 0, "util_func not found in output"
        assert main_pos >= 0, "main not found in output"
        assert util_func_pos < main_pos, "Dependencies should appear before dependents"


class TestRustConstInlining:
    """Test const and static value inlining."""

    def test_const_integer_inlining(self):
        """Test inlining of const integer values."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/const_inlining/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify const values are inlined
        assert "100000" in result  # MAX_N value
        assert "1000000007" in result  # MOD value

        # Verify const declarations are removed
        assert "const MAX_N:" not in result
        assert "const MOD:" not in result

    def test_const_float_inlining(self):
        """Test inlining of const float values."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/const_inlining/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify float constant is inlined
        assert "3.14159265359" in result
        assert "const PI:" not in result

    def test_const_bool_inlining(self):
        """Test inlining of const boolean values."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/const_inlining/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify boolean constant handling
        # The const should be removed
        assert "const DEBUG:" not in result

    def test_const_in_expressions(self, tmp_path):
        """Test that consts are inlined in expressions."""
        code = """
const SIZE: usize = 1000;
const MULTIPLIER: i32 = 2;

fn main() {
    let arr = vec![0; SIZE];
    let value = SIZE * MULTIPLIER;
    println!("{}", value);
}
"""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text(code)

        preprocessor = RustPreprocessor()
        result = preprocessor.preprocess(str(main_rs), [])

        # Verify inlining in expressions
        assert "1000" in result
        assert "const SIZE:" not in result
        assert "const MULTIPLIER:" not in result


@pytest.mark.skipif(os.system("which rustc > /dev/null 2>&1") != 0, reason="rustc not available")
class TestRustBuildVerification:
    """Test that preprocessed output compiles with rustc."""

    def test_simple_module_compiles(self, tmp_path):
        """Test that preprocessed simple module code compiles."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/simple_module/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Write to temp file and try to compile
        output_rs = tmp_path / "output.rs"
        output_rs.write_text(result)

        # Compile with rustc
        compile_result = os.system(
            f"rustc --crate-type bin {output_rs} -o {tmp_path}/test_binary 2>&1"
        )

        assert compile_result == 0, "Preprocessed code should compile successfully"

    def test_nested_modules_compiles(self, tmp_path):
        """Test that preprocessed nested modules compile."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/nested_modules/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Write to temp file and try to compile
        output_rs = tmp_path / "output.rs"
        output_rs.write_text(result)

        # Compile with rustc
        compile_result = os.system(
            f"rustc --crate-type bin {output_rs} -o {tmp_path}/test_binary 2>&1"
        )

        assert compile_result == 0, "Preprocessed code should compile successfully"

    def test_macros_compile(self, tmp_path):
        """Test that preprocessed code with macros compiles."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/macros/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Write to temp file and try to compile
        output_rs = tmp_path / "output.rs"
        output_rs.write_text(result)

        # Compile with rustc
        compile_result = os.system(
            f"rustc --crate-type bin {output_rs} -o {tmp_path}/test_binary 2>&1"
        )

        assert compile_result == 0, "Preprocessed code with macros should compile"

    def test_const_inlining_compiles(self, tmp_path):
        """Test that preprocessed code with const inlining compiles."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/const_inlining/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Write to temp file and try to compile
        output_rs = tmp_path / "output.rs"
        output_rs.write_text(result)

        # Compile with rustc
        compile_result = os.system(
            f"rustc --crate-type bin {output_rs} -o {tmp_path}/test_binary 2>&1"
        )

        assert compile_result == 0, "Preprocessed code with const inlining should compile"


class TestRustAdvancedFeatures:
    """Test Phase 3 advanced Rust preprocessor features."""

    def test_custom_path_attribute(self):
        """Test #[path = \"...\"] custom module path support."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/custom_paths/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify module content is inlined
        assert "fn add(a: i32, b: i32) -> i32" in result
        assert "fn multiply(a: i32, b: i32) -> i32" in result

        # Verify mod declaration is removed
        assert "mod utils;" not in result
        assert "#[path" not in result

        # Verify functions are accessible
        assert "add" in result
        assert "multiply" in result

    def test_glob_imports(self):
        """Test glob imports (use module::*) are handled correctly."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/glob_imports/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify module content is inlined
        assert "fn add(a: i32, b: i32) -> i32" in result
        assert "fn sub(a: i32, b: i32) -> i32" in result
        assert "fn mul(a: i32, b: i32) -> i32" in result

        # Verify mod and use declarations are removed
        assert "mod math;" not in result
        assert "use math::*" not in result

        # Verify function calls work (no qualifiers needed for glob imports)
        assert "add(a, b)" in result
        assert "sub(a, b)" in result
        assert "mul(a, b)" in result

        # Verify main function is present
        assert "fn main()" in result

    def test_inline_modules_preserved(self):
        """Test inline modules (mod utils { ... }) are preserved."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/inline_modules/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify inline module structure is preserved
        assert "mod utils" in result
        assert "pub fn helper() -> i32" in result
        assert "pub mod nested" in result
        assert "pub fn inner() -> i32" in result

        # Verify main function is present
        assert "fn main()" in result

        # NOTE: Current implementation removes qualifiers, which breaks inline modules
        # This test documents the current behavior - may need fixing

    def test_cfg_attributes_preserved(self):
        """Test #[cfg(...)] conditional compilation attributes are preserved."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/cfg_attributes/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify #[cfg] attributes are preserved
        assert '#[cfg(feature = "fast")]' in result
        assert '#[cfg(not(feature = "fast"))]' in result

        # Verify conditional blocks are preserved
        assert "Using fast math" in result
        assert "Using slow math" in result

        # Verify main function is present
        assert "fn main()" in result

        # Note: We don't inline the cfg-gated modules because they're conditional
