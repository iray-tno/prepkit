#pragma once
#include <vector>

class SegmentTree {
private:
    std::vector<long long> tree;
    int size;
    
    void update_impl(int node, int start, int end, int idx, int val) {
        if (start == end) {
            tree[node] = val;
        } else {
            int mid = (start + end) / 2;
            if (idx <= mid) {
                update_impl(2 * node, start, mid, idx, val);
            } else {
                update_impl(2 * node + 1, mid + 1, end, idx, val);
            }
            tree[node] = tree[2 * node] + tree[2 * node + 1];
        }
    }
    
    long long query_impl(int node, int start, int end, int l, int r) {
        if (r < start || end < l) {
            return 0;
        }
        if (l <= start && end <= r) {
            return tree[node];
        }
        int mid = (start + end) / 2;
        return query_impl(2 * node, start, mid, l, r) + 
               query_impl(2 * node + 1, mid + 1, end, l, r);
    }
    
public:
    SegmentTree(int n) : size(n) {
        tree.resize(4 * n);
    }
    
    void update(int idx, int val) {
        update_impl(1, 0, size - 1, idx, val);
    }
    
    long long query(int l, int r) {
        return query_impl(1, 0, size - 1, l, r);
    }
};