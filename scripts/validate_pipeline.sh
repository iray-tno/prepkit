#!/bin/bash

# PrepKit Pipeline Validation Script
# Use this for daily dogfooding and continuous validation

set -e

echo "🔧 PrepKit Pipeline Validation"
echo "=============================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success_count=0
total_tests=0

check_command() {
    local cmd="$1"
    local desc="$2"
    
    echo -n "Testing: $desc... "
    total_tests=$((total_tests + 1))
    
    if eval "$cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}✗${NC}"
    fi
}

# Test CLI availability
echo -e "\n${YELLOW}1. CLI Availability${NC}"
check_command "poetry run python -m main --help" "Main CLI help"
check_command "poetry run python -m main cpp --help" "C++ module help"
check_command "poetry run python -m main kaggle --help" "Kaggle module help"
check_command "poetry run python -m main ai-config --help" "AI config module help"

# Test C++ preprocessing
echo -e "\n${YELLOW}2. C++ Preprocessing${NC}"
mkdir -p /tmp/prepkit_test
cd /tmp/prepkit_test

# Create test files
cat > main.cpp << 'EOF'
#include <iostream>
#include "utils.hpp"

constexpr int MOD = 1000000007;
constexpr bool DEBUG = false;
constexpr double PI = 3.14159;

int main() {
    std::cout << "Test: " << add_numbers(5, 3) << std::endl;
    if (DEBUG) std::cout << "Debug mode" << std::endl;
    return 0;
}
EOF

cat > utils.hpp << 'EOF'
#pragma once
int add_numbers(int a, int b) {
    return a + b;
}
EOF

cd - > /dev/null

check_command "cd /tmp/prepkit_test && poetry run python -m main cpp preprocess main.cpp" "Basic preprocessing"
check_command "cd /tmp/prepkit_test && g++ -o test_solution <(poetry run python -m main cpp preprocess main.cpp)" "Build verification"
check_command "cd /tmp/prepkit_test && poetry run python -m main cpp minify main.cpp" "Code minification"

# Test project scaffolding
echo -e "\n${YELLOW}3. Project Scaffolding${NC}"
check_command "cd /tmp && poetry run python -m main project new test_project --lang cpp --type atcoder-algorithm" "AtCoder project creation"
check_command "test -f /tmp/test_project/prepkit_config.yaml" "Config file generation"
check_command "test -f /tmp/test_project/main.cpp" "Main file generation"

# Test AI assistant configuration
echo -e "\n${YELLOW}4. AI Assistant Configuration${NC}"
check_command "poetry run python -m main ai-config status" "AI config status"
check_command "cd /tmp && poetry run python -m main ai-config setup claude-code" "Claude Code setup"
check_command "test -f /tmp/.prepkit/ai-assistants/claude-code.md" "Claude Code config file"

# Test suite execution
echo -e "\n${YELLOW}5. Test Suite${NC}"
check_command "poetry run pytest tests/test_cpp_preprocessor.py -q" "Unit tests"
check_command "poetry run pytest tests/test_cpp_integration.py::TestCppPreprocessorEnhanced::test_build_verification_segment_tree -q" "Build verification test"

# Performance benchmark (if available)
echo -e "\n${YELLOW}6. Performance${NC}"
check_command "timeout 30 poetry run pytest --benchmark-only -q" "Performance benchmarks"

# Clean up
rm -rf /tmp/prepkit_test /tmp/test_project

# Summary
echo -e "\n${YELLOW}Summary${NC}"
echo "=============================="
if [ $success_count -eq $total_tests ]; then
    echo -e "${GREEN}All $total_tests tests passed! ✓${NC}"
    echo "PrepKit pipeline is healthy and ready for development."
else
    failed=$((total_tests - success_count))
    echo -e "${RED}$failed out of $total_tests tests failed.${NC}"
    echo "Please check the failing components before using PrepKit."
fi

echo ""
echo "💡 Dogfooding Tips:"
echo "- Run this script daily during development"
echo "- Test with real competitive programming problems"
echo "- Monitor processing times for performance regressions"
echo "- Use AI assistants during actual coding sessions"
echo ""

exit $(($total_tests - $success_count))