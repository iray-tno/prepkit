#pragma once

// Common mathematical utilities for competitive programming
inline long long add_mod(long long a, long long b, long long mod) {
    return (a + b) % mod;
}

inline long long multiply_mod(long long a, long long b, long long mod) {
    return (a * b) % mod;
}

inline long long power_mod(long long base, long long exp, long long mod) {
    long long result = 1;
    while (exp > 0) {
        if (exp % 2 == 1) {
            result = multiply_mod(result, base, mod);
        }
        base = multiply_mod(base, base, mod);
        exp /= 2;
    }
    return result;
}

inline long long gcd(long long a, long long b) {
    while (b != 0) {
        long long temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}