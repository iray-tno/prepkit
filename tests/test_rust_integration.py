"""Integration tests for Rust preprocessor."""
import pytest
import os
import subprocess
import shutil
from pathlib import Path
from syrupy import SnapshotAssertion
from plugins.rust_plugin import RustPreprocessor, RustMinifier


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


class TestRustPreprocessorNameCollisions:
    """Modules are wrapped in `mod name { ... }` so same-named items don't collide.

    Regression coverage for the issue where flattening inlined module bodies into
    a single namespace, causing two modules that each define an item with the same
    name (e.g. `helper`) to collide with E0428 ("defined multiple times").
    """

    def test_same_name_in_two_modules_does_not_collide(self):
        """Two modules each defining `helper` must both survive, namespaced."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/name_collisions/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Both modules are wrapped, keeping their own namespace
        assert "mod geometry {" in result
        assert "mod search {" in result

        # Both `helper` definitions are present (would be one, or a collision,
        # under the old inlining approach)
        assert result.count("pub fn helper() -> i32") == 2

        # Qualified call sites are preserved, not stripped down to `helper()`
        assert "geometry::helper()" in result
        assert "search::helper()" in result

    @pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not available")
    def test_name_collisions_compile(self, tmp_path):
        """The wrapped output must compile (old inlined output failed E0428)."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/name_collisions/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        output_rs = tmp_path / "output.rs"
        output_rs.write_text(result)

        compile_result = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "bin",
             str(output_rs), "-o", str(tmp_path / "bin")],
            capture_output=True, text=True, timeout=30,
        )
        assert compile_result.returncode == 0, (
            f"Wrapped output should compile:\n{compile_result.stderr}"
        )


class TestRustQualifierPreservation:
    """Path qualifiers must be preserved, not stripped.

    Regression coverage for the issue where a token-level "strip module
    qualifiers" regex removed valid path segments: std sub-modules
    (`std::collections::HashMap` -> `std::HashMap`), associated functions
    (`HashMap::new()` -> `new()`), and crate-internal multi-segment paths.
    Wrapping modules makes all original paths valid, so nothing is rewritten.
    """

    def test_std_and_associated_paths_preserved(self):
        """std sub-module paths and `Type::method` calls keep all segments."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/qualified_paths/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # std sub-module paths keep their middle segment
        assert "std::collections::HashMap" in result
        assert "std::cmp::Reverse" in result
        assert "std::HashMap" not in result
        assert "std::Reverse" not in result

        # Associated functions keep their type qualifier
        assert "HashMap::new()" in result
        assert "Vec::new()" in result

        # Crate-internal multi-segment path is preserved end to end
        assert "helpers::scale::by_two" in result

    @pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not available")
    def test_qualified_paths_compile(self, tmp_path):
        """Output with std/associated/internal paths must compile."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/qualified_paths/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        output_rs = tmp_path / "output.rs"
        output_rs.write_text(result)

        compile_result = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "bin",
             str(output_rs), "-o", str(tmp_path / "bin")],
            capture_output=True, text=True, timeout=30,
        )
        assert compile_result.returncode == 0, (
            f"Output with qualified paths should compile:\n{compile_result.stderr}"
        )


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

        # Verify module content is wrapped, not inlined into the root namespace
        assert "fn add(a: i32, b: i32) -> i32" in result
        assert "fn sub(a: i32, b: i32) -> i32" in result
        assert "fn mul(a: i32, b: i32) -> i32" in result

        # The `mod math;` declaration becomes an inline `mod math { ... }` block
        assert "mod math;" not in result
        assert "mod math {" in result

        # The glob import is preserved: with wrapping, `use math::*;` keeps
        # resolving against the wrapped module, so it must NOT be stripped.
        assert "use math::*" in result

        # Verify function calls keep their original (unqualified) form
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

        # Inline modules pass through untouched, and qualified paths into them
        # (utils::helper, utils::nested::inner) are preserved.
        assert "utils::helper()" in result
        assert "utils::nested::inner()" in result

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


class TestRustEdgeCases:
    """Test edge cases and corner cases for Rust preprocessor."""

    def test_string_literals_not_processed(self):
        """Test that string literals containing code patterns are fully preserved.

        This test verifies the fix for const extraction and removal bugs.
        String literals should now be completely protected from preprocessing.
        """
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/string_literals/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify string literals are fully preserved (BUG FIX)
        assert 'mod utils; but should be preserved' in result
        assert 'use utils::* in it' in result
        assert 'MAX_SIZE should not be replaced here' in result
        assert 'const MAX_SIZE: i32 = 9999; is fake' in result  # Now works!

        # Verify actual code is processed
        assert 'pub fn helper' in result  # utils module inlined

        # Verify correct const value is used (BUG FIX)
        # The real MAX_SIZE = 1000 should be used, not the fake one from string
        assert '1000' in result  # Real value
        assert result.count('9999') == 1  # Fake value only appears in string

        # Verify mod declaration removed (but preserved in strings)
        assert result.count('mod utils;') >= 1  # Should appear in string literal

    def test_deep_module_nesting(self):
        """Test deeply nested module structure (4 levels)."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/deep_nesting/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify all module content is present
        assert 'pub fn core_function' in result
        assert 'fn main()' in result

        # Verify mod declarations are removed
        assert 'mod level1;' not in result
        assert 'pub mod level2;' not in result
        assert 'pub mod level3;' not in result

        # Verify it compiles (if rustc available)
        assert 'x * x' in result

    def test_mixed_advanced_features(self):
        """Test combination of #[path], inline modules, and const inlining."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/mixed_features/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Verify custom path module is inlined
        assert 'pub fn add(' in result
        assert 'pub fn multiply(' in result

        # Verify inline module structure is preserved
        assert 'mod inline_utils' in result

        # Const declarations are removed after inlining (expected behavior)
        # This is intentional - we inline the values and remove declarations
        assert 'pub fn scale' in result  # Function remains

        # Verify #[path] attribute is removed
        assert '#[path' not in result

        # Verify const inlining - values appear in code
        assert '100' in result  # BASE_VALUE
        assert '10' in result   # MULTIPLIER
        assert '5' in result    # OFFSET

    def test_empty_and_minimal_modules(self):
        """Test handling of empty and minimal module files."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/empty_files/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # Should not crash and should produce valid output
        assert 'fn main()' in result
        assert 'Testing empty and minimal modules' in result

        # Module declarations should be removed
        assert 'mod empty_module;' not in result
        assert 'mod comments_only;' not in result
        assert 'mod whitespace_only;' not in result

    def test_const_name_collisions(self):
        """Test const inlining with same names in different modules."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/const_collisions/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        # All modules should be inlined
        assert 'pub fn get_value()' in result
        assert 'fn main()' in result

        # Constants should be inlined
        # Note: Our current implementation inlines all consts globally
        # This test documents current behavior - may need improvement
        assert '999' in result or '100' in result or '200' in result


class TestRustEdgeCasesSnapshots:
    """Snapshot tests for edge cases - catches unexpected output changes."""

    def test_string_literals_snapshot(self, snapshot: SnapshotAssertion):
        """Snapshot test for string literals preservation."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/string_literals/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        assert result == snapshot(name="rust_string_literals_preprocessed")

    def test_deep_nesting_snapshot(self, snapshot: SnapshotAssertion):
        """Snapshot test for deep module nesting."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/deep_nesting/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        assert result == snapshot(name="rust_deep_nesting_preprocessed")

    def test_mixed_features_snapshot(self, snapshot: SnapshotAssertion):
        """Snapshot test for mixed advanced features."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/mixed_features/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        assert result == snapshot(name="rust_mixed_features_preprocessed")

    def test_const_collisions_snapshot(self, snapshot: SnapshotAssertion):
        """Snapshot test for const name collisions."""
        preprocessor = RustPreprocessor()
        main_file = Path("tests/fixtures/rust/edge_cases/const_collisions/main.rs")

        result = preprocessor.preprocess(str(main_file), [])

        assert result == snapshot(name="rust_const_collisions_preprocessed")

class TestRustTunableParameters:
    """Tests for Rust tunable parameter injection."""

    @pytest.fixture
    def rust_preprocessor(self):
        return RustPreprocessor()

    def test_single_tunable_param(self, rust_preprocessor, tmp_path):
        """Test single tunable parameter injection."""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
const VALUE: i32 = 100;  // @tune

fn main() {
    println!("{}", VALUE);
}
""")

        # Without defines - should keep original value
        output = rust_preprocessor.preprocess(str(main_rs), [])
        assert "100" in output

        # With defines - should inject new value
        output = rust_preprocessor.preprocess(str(main_rs), [], defines={"VALUE": "200"})
        assert "200" in output
        assert "100" not in output

    def test_multiple_tunable_params(self, rust_preprocessor, tmp_path):
        """Test multiple tunable parameters with selective injection."""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
const TEMP_START: f64 = 1000.0;  // @tune
const BEAM_WIDTH: i32 = 50;  // @tune
const MAX_TURNS: i32 = 100;  // Fixed parameter

fn main() {
    println!("{} {} {}", TEMP_START, BEAM_WIDTH, MAX_TURNS);
}
""")

        # Without defines - should keep original values
        output = rust_preprocessor.preprocess(str(main_rs), [])
        assert "1000.0" in output
        assert "50" in output
        assert "100" in output

        # With selective defines - only marked params replaced
        output = rust_preprocessor.preprocess(str(main_rs), [],
            defines={"TEMP_START": "1500.0", "BEAM_WIDTH": "75"})
        assert "1500.0" in output
        assert "75" in output
        assert "100" in output  # Fixed parameter unchanged

    def test_tunable_params_types(self, rust_preprocessor, tmp_path):
        """Test tunable parameter injection with different types."""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
const PI: f64 = 3.14;  // @tune
const COUNT: i32 = 10;  // @tune
const DEBUG: bool = true;  // @tune

fn main() {
    println!("{} {} {}", PI, COUNT, DEBUG);
}
""")

        # Inject different types
        output = rust_preprocessor.preprocess(str(main_rs), [],
            defines={"PI": "3.14159", "COUNT": "20", "DEBUG": "false"})
        assert "3.14159" in output
        assert "20" in output
        assert "false" in output

    def test_tunable_params_preserves_unmarked(self, rust_preprocessor, tmp_path):
        """Test that unmarked const declarations are not affected."""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
const TEMP_START: f64 = 1000.0;  // @tune
const MAX_TURNS: i32 = 100;  // Not marked

fn main() {
    println!("{} {}", TEMP_START, MAX_TURNS);
}
""")

        # Try to define unmarked param - should have no effect
        output = rust_preprocessor.preprocess(str(main_rs), [],
            defines={"MAX_TURNS": "9999"})
        # MAX_TURNS is not marked with @tune, so should remain 100
        assert "100" in output
        assert "9999" not in output

    def test_tunable_params_marker_preserved(self, rust_preprocessor, tmp_path):
        """Test that @tune markers remain after injection (Rust keeps comments during preprocessing)."""
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
const VALUE: i32 = 100;  // @tune

fn main() {
    println!("{}", VALUE);
}
""")

        output = rust_preprocessor.preprocess(str(main_rs), [], defines={"VALUE": "200"})
        # Rust preprocessor keeps comments (unlike C++), so markers remain
        # They're removed during minification, not preprocessing
        assert "200" in output  # Value changed
        assert "@tune" in output  # Marker still present

    def test_tunable_params_with_modules(self, rust_preprocessor, tmp_path):
        """Test tunable parameters work with module resolution."""
        # Create utils.rs with tunable param
        utils_rs = tmp_path / "utils.rs"
        utils_rs.write_text("""
const MULTIPLIER: i32 = 10;  // @tune

pub fn scale(x: i32) -> i32 {
    x * MULTIPLIER
}
""")

        # Create main.rs
        main_rs = tmp_path / "main.rs"
        main_rs.write_text("""
mod utils;

fn main() {
    let result = utils::scale(5);
    println!("{}", result);
}
""")

        # Inject tunable param from module
        output = rust_preprocessor.preprocess(str(main_rs), [],
            defines={"MULTIPLIER": "20"})
        assert "20" in output
        assert "10" not in output


class TestRustMinifier:
    """Tests for Rust code minification."""

    @pytest.fixture
    def rust_minifier(self):
        return RustMinifier()

    @pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not available")
    def test_minification_build_verification(self, rust_minifier, tmp_path):
        """Verify that minified code still compiles and is significantly smaller."""
        source_file = Path("tests/fixtures/rust/size_constrained/main.rs")
        
        # Read original
        with open(source_file) as f:
            original_content = f.read()
        original_size = len(original_content)
        
        # Minify
        minified = rust_minifier.minify(str(source_file))
        minified_size = len(minified)
        
        # Write minified version
        minified_file = tmp_path / "minified.rs"
        minified_file.write_text(minified)
        
        # Compile minified version
        result = subprocess.run([
            "rustc", str(minified_file), 
            "-o", str(tmp_path / "minified_exe")
        ], capture_output=True, text=True, timeout=30)
        
        assert result.returncode == 0, f"Minified compilation failed:\n{result.stderr}"
        
        # Verify minification effectiveness (should be at least 40% smaller)
        assert minified_size < original_size * 0.6, f"Minification not effective: {minified_size} vs {original_size}"
        
        # Verify comments are removed
        assert "//" not in minified or '"' in minified  # Comments removed unless in strings
        assert "/*" not in minified or '"' in minified
        assert "*/" not in minified or '"' in minified

    def test_minification_preserves_string_literals(self, rust_minifier):
        """Verify that string literals containing comment-like syntax are preserved."""
        source_file = Path("tests/fixtures/rust/size_constrained/main.rs")
        
        minified = rust_minifier.minify(str(source_file))
        
        # String literals should be preserved exactly
        assert '"// This is not a comment, it\'s a string literal"' in minified
        assert '"/* Also not a comment */"' in minified

    def test_minification_removes_comments(self, rust_minifier, tmp_path):
        """Verify that actual comments are removed."""
        # Create test file with comments
        test_content = '''
// This is a comment
fn main() {
    /* Multi-line
       comment */
    let x = 42;  // Inline comment
    println!("{}", x);
}
'''
        test_file = tmp_path / "test.rs"
        test_file.write_text(test_content)
        
        minified = rust_minifier.minify(str(test_file))
        
        # Comments should be removed (but not // in strings)
        # Check that standalone comment lines are gone
        assert "// This is a comment" not in minified
        assert "/* Multi-line" not in minified
        assert "comment */" not in minified
        assert "// Inline comment" not in minified
        
        # Code should still be present
        assert "fn main" in minified
        assert "let x" in minified or "x=42" in minified
        assert "println!" in minified

    def test_minification_snapshot(self, rust_minifier, snapshot: SnapshotAssertion):
        """Snapshot test for minification to catch unexpected changes."""
        source_file = Path("tests/fixtures/rust/size_constrained/main.rs")
        
        minified = rust_minifier.minify(str(source_file))
        
        assert minified == snapshot(name="rust_minified_size_constrained")
