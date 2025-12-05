#ifndef UTILS_HPP
#define UTILS_HPP

#include <iostream>

namespace utils {
    inline int helper(int x) {
        // String in header should also be preserved
        std::cout << "Inside helper: #include should not be removed" << std::endl;
        return x * 2;
    }
}

#endif
