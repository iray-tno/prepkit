#pragma once
#include <vector>
#include <queue>
#include <stack>
#include <climits>

// Graph algorithms for competitive programming

// Basic graph representation
using Graph = std::vector<std::vector<int>>;
using WeightedGraph = std::vector<std::vector<std::pair<int, long long>>>;

// DFS traversal
void dfs(const Graph& graph, int start, std::vector<bool>& visited) {
    visited[start] = true;
    
    for (int neighbor : graph[start]) {
        if (!visited[neighbor]) {
            dfs(graph, neighbor, visited);
        }
    }
}

// BFS traversal
std::vector<int> bfs(const Graph& graph, int start) {
    int n = graph.size();
    std::vector<int> distances(n, -1);
    std::queue<int> q;
    
    distances[start] = 0;
    q.push(start);
    
    while (!q.empty()) {
        int current = q.front();
        q.pop();
        
        for (int neighbor : graph[current]) {
            if (distances[neighbor] == -1) {
                distances[neighbor] = distances[current] + 1;
                q.push(neighbor);
            }
        }
    }
    
    return distances;
}

// Dijkstra's shortest path
std::vector<long long> dijkstra(const WeightedGraph& graph, int start) {
    int n = graph.size();
    std::vector<long long> distances(n, LLONG_MAX);
    std::priority_queue<std::pair<long long, int>, 
                       std::vector<std::pair<long long, int>>,
                       std::greater<std::pair<long long, int>>> pq;
    
    distances[start] = 0;
    pq.push({0, start});
    
    while (!pq.empty()) {
        auto [dist, u] = pq.top();
        pq.pop();
        
        if (dist > distances[u]) continue;
        
        for (auto [v, weight] : graph[u]) {
            if (distances[u] + weight < distances[v]) {
                distances[v] = distances[u] + weight;
                pq.push({distances[v], v});
            }
        }
    }
    
    return distances;
}

// Check if graph is bipartite
bool is_bipartite(const Graph& graph) {
    int n = graph.size();
    std::vector<int> color(n, -1);
    
    for (int start = 0; start < n; start++) {
        if (color[start] == -1) {
            std::queue<int> q;
            q.push(start);
            color[start] = 0;
            
            while (!q.empty()) {
                int u = q.front();
                q.pop();
                
                for (int v : graph[u]) {
                    if (color[v] == -1) {
                        color[v] = 1 - color[u];
                        q.push(v);
                    } else if (color[v] == color[u]) {
                        return false;
                    }
                }
            }
        }
    }
    
    return true;
}

// Topological sort
std::vector<int> topological_sort(const Graph& graph) {
    int n = graph.size();
    std::vector<int> in_degree(n, 0);
    
    for (int u = 0; u < n; u++) {
        for (int v : graph[u]) {
            in_degree[v]++;
        }
    }
    
    std::queue<int> q;
    for (int i = 0; i < n; i++) {
        if (in_degree[i] == 0) {
            q.push(i);
        }
    }
    
    std::vector<int> result;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        result.push_back(u);
        
        for (int v : graph[u]) {
            in_degree[v]--;
            if (in_degree[v] == 0) {
                q.push(v);
            }
        }
    }
    
    return result.size() == n ? result : std::vector<int>();
}