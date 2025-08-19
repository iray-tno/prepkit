#include <iostream>
#include <vector>
#include <algorithm>
#include <string>
#include <map>
#include <set>
#include <queue>
#include <stack>
#include <cmath>
#include <climits>
using namespace std;

// Common constants for competitive programming
constexpr int MOD = 1000000007;
constexpr int INF = 1e9;
constexpr long long LINF = 1e18;

// Fast I/O setup
void fast_io() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);
}

int main() {
    fast_io();
    
    // Read input
    int n;
    cin >> n;
    
    // Example: read array
    vector<int> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    // TODO: Implement your solution here
    
    // Example output
    cout << "Answer: " << n << endl;
    
    return 0;
}