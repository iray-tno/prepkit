#pragma once
#include <vector>

// Common data structures for competitive programming

// Fenwick Tree (Binary Indexed Tree)
class FenwickTree {
private:
    std::vector<long long> tree;
    int n;

public:
    FenwickTree(int size) : n(size), tree(size + 1, 0) {}

    void update(int idx, long long val) {
        for (++idx; idx <= n; idx += idx & -idx) {
            tree[idx] += val;
        }
    }

    long long query(int idx) {
        long long sum = 0;
        for (++idx; idx > 0; idx -= idx & -idx) {
            sum += tree[idx];
        }
        return sum;
    }

    long long range_query(int l, int r) {
        return query(r) - (l > 0 ? query(l - 1) : 0);
    }
};

// Segment Tree for range queries
class SegmentTree {
private:
    std::vector<long long> tree;
    int size;

    void update_impl(int node, int start, int end, int idx, long long val) {
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

    void update(int idx, long long val) {
        update_impl(1, 0, size - 1, idx, val);
    }

    long long query(int l, int r) {
        return query_impl(1, 0, size - 1, l, r);
    }
};

// Union-Find (Disjoint Set Union)
class UnionFind {
private:
    std::vector<int> parent, rank;

public:
    UnionFind(int n) : parent(n), rank(n, 0) {
        for (int i = 0; i < n; i++) {
            parent[i] = i;
        }
    }

    int find(int x) {
        if (parent[x] != x) {
            parent[x] = find(parent[x]);
        }
        return parent[x];
    }

    bool unite(int x, int y) {
        int px = find(x), py = find(y);
        if (px == py) return false;

        if (rank[px] < rank[py]) {
            parent[px] = py;
        } else if (rank[px] > rank[py]) {
            parent[py] = px;
        } else {
            parent[py] = px;
            rank[px]++;
        }
        return true;
    }

    bool connected(int x, int y) {
        return find(x) == find(y);
    }
};