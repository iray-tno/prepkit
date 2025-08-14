#include <iostream>
#include <vector>

constexpr int MOD = 1000000007;
constexpr double PI = 3.14159265359;
constexpr bool DEBUG = true;
constexpr int MAXN = 200005;
constexpr long long INF = 1e18;

int main() {
    std::vector<int> arr(MAXN);
    
    long long result = 0;
    for (int i = 0; i < 1000; i++) {
        result = (result + i) % MOD;
    }
    
    if (DEBUG) {
        std::cout << "Result: " << result << std::endl;
        std::cout << "PI approximation: " << PI << std::endl;
        std::cout << "Max value: " << INF << std::endl;
    }
    
    return result == 0 ? 0 : 1;
}