#pragma once
#include <vector>
#include <algorithm>

// Utility functions for competitive programming

// GCD and LCM
long long gcd(long long a, long long b) {
    while (b != 0) {
        long long temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

long long lcm(long long a, long long b) {
    return (a / gcd(a, b)) * b;
}

// Modular arithmetic
long long mod_pow(long long base, long long exp, long long mod) {
    long long result = 1;
    while (exp > 0) {
        if (exp % 2 == 1) {
            result = (result * base) % mod;
        }
        base = (base * base) % mod;
        exp /= 2;
    }
    return result;
}

long long mod_inv(long long a, long long mod) {
    return mod_pow(a, mod - 2, mod);
}

// Array utilities
template<typename T>
void print_array(const std::vector<T>& arr) {
    for (size_t i = 0; i < arr.size(); i++) {
        std::cout << arr[i];
        if (i < arr.size() - 1) std::cout << " ";
    }
    std::cout << std::endl;
}

template<typename T>
T max_element_value(const std::vector<T>& arr) {
    return *std::max_element(arr.begin(), arr.end());
}

template<typename T>
T min_element_value(const std::vector<T>& arr) {
    return *std::min_element(arr.begin(), arr.end());
}