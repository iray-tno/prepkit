#include <iostream>
#include <vector>
#include "segment_tree.hpp"

constexpr int MAXN = 100000;
constexpr int MOD = 1000000007;

int main() {
    int n;
    std::cin >> n;
    
    SegmentTree st(n);
    
    for (int i = 0; i < n; i++) {
        int x;
        std::cin >> x;
        st.update(i, x);
    }
    
    int q;
    std::cin >> q;
    
    while (q--) {
        int l, r;
        std::cin >> l >> r;
        std::cout << st.query(l, r) % MOD << std::endl;
    }
    
    return 0;
}