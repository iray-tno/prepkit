#pragma once
#include <iostream>

// Fast I/O template commonly used in competitive programming
inline void fast_io() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    std::cout.tie(nullptr);
}

inline int read_int() {
    int x;
    std::cin >> x;
    return x;
}

inline long long read_ll() {
    long long x;
    std::cin >> x;
    return x;
}

inline std::string read_string() {
    std::string s;
    std::cin >> s;
    return s;
}