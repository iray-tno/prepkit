#include <iostream>
#include <vector>
#include <algorithm>
#include <string>
#include "template.hpp"
#include "math_utils.hpp"

constexpr int MOD = 998244353;
constexpr int MAXN = 300005;

// Typical AtCoder problem solution structure
int main() {
    fast_io();
    
    int n = read_int();
    std::vector<long long> a(n);
    
    for (int i = 0; i < n; i++) {
        a[i] = read_int();
    }
    
    // Calculate some result using utilities
    long long answer = 0;
    for (int i = 0; i < n; i++) {
        answer = add_mod(answer, multiply_mod(a[i], power_mod(2, i, MOD), MOD), MOD);
    }
    
    std::cout << answer << std::endl;
    
    return 0;
}