#include <iostream>
#include "utils.hpp"

constexpr int MAX_SIZE = 1000;
constexpr double PI = 3.14159;

int main() {
    // String literals should NOT be processed
    std::cout << "This contains #include <vector> but should be preserved" << std::endl;
    std::cout << "const expr MAX_SIZE = 9999; is fake" << std::endl;
    std::cout << "MAX_SIZE should not be replaced here in string" << std::endl;

    // But actual usage should be replaced
    int size = MAX_SIZE;
    double pi = PI;

    std::cout << "Actual MAX_SIZE: " << size << std::endl;
    std::cout << "Actual PI: " << pi << std::endl;

    // Edge case: Escaped quotes
    std::cout << "She said \"#include <test>\" in the string" << std::endl;
    std::cout << "Path: \"./utils.hpp\"" << std::endl;

    int result = utils::helper(size);
    std::cout << "Result: " << result << std::endl;

    return 0;
}
