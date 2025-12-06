// AtCoder Marathon Example: Traveling Salesman Problem
// This demonstrates a typical marathon contest solution with tunable parameters
// Uses simulated annealing with 2-opt local search

#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <algorithm>
#include <chrono>

using namespace std;

// Tunable hyperparameters for optimization
constexpr double TEMP_START = 1000.0;      // @tune
constexpr double TEMP_END = 10.0;          // @tune
constexpr double COOLING_RATE = 0.995;     // @tune
constexpr int MAX_ITERATIONS = 100000;     // @tune
constexpr double ACCEPT_THRESHOLD = 0.01;  // @tune

// Fixed parameters
constexpr int N_CITIES = 50;
constexpr int RANDOM_SEED = 42;

struct Point {
    double x, y;
};

class TSPSolver {
private:
    vector<Point> cities;
    vector<int> tour;
    mt19937 rng;
    uniform_real_distribution<double> dist;

    double distance(const Point& a, const Point& b) const {
        double dx = a.x - b.x;
        double dy = a.y - b.y;
        return sqrt(dx * dx + dy * dy);
    }

    double tour_length(const vector<int>& t) const {
        double len = 0.0;
        for (int i = 0; i < N_CITIES; i++) {
            len += distance(cities[t[i]], cities[t[(i + 1) % N_CITIES]]);
        }
        return len;
    }

    // 2-opt swap: reverse the segment between i and j
    void two_opt_swap(vector<int>& t, int i, int j) {
        while (i < j) {
            swap(t[i], t[j]);
            i++;
            j--;
        }
    }

    // Calculate delta for 2-opt move (faster than recalculating full tour)
    double two_opt_delta(const vector<int>& t, int i, int j) const {
        int n = N_CITIES;
        int next_i = (i + 1) % n;
        int next_j = (j + 1) % n;

        double old_dist = distance(cities[t[i]], cities[t[next_i]]) +
                          distance(cities[t[j]], cities[t[next_j]]);

        double new_dist = distance(cities[t[i]], cities[t[j]]) +
                          distance(cities[t[next_i]], cities[t[next_j]]);

        return new_dist - old_dist;
    }

public:
    TSPSolver(const vector<Point>& c) : cities(c), rng(RANDOM_SEED), dist(0.0, 1.0) {
        // Initialize with nearest neighbor heuristic
        tour.resize(N_CITIES);
        vector<bool> visited(N_CITIES, false);

        tour[0] = 0;
        visited[0] = true;

        for (int i = 1; i < N_CITIES; i++) {
            int last = tour[i - 1];
            int best = -1;
            double best_dist = 1e18;

            for (int j = 0; j < N_CITIES; j++) {
                if (!visited[j]) {
                    double d = distance(cities[last], cities[j]);
                    if (d < best_dist) {
                        best_dist = d;
                        best = j;
                    }
                }
            }

            tour[i] = best;
            visited[best] = true;
        }
    }

    void solve() {
        double current_length = tour_length(tour);
        double best_length = current_length;
        vector<int> best_tour = tour;

        double temperature = TEMP_START;
        int iterations = 0;

        while (temperature > TEMP_END && iterations < MAX_ITERATIONS) {
            // Generate random 2-opt move
            int i = rng() % N_CITIES;
            int j = rng() % N_CITIES;
            if (i > j) swap(i, j);
            if (i == j) continue;

            // Calculate delta
            double delta = two_opt_delta(tour, i, j);

            // Accept or reject
            bool accept = false;
            if (delta < 0) {
                accept = true;  // Always accept improvements
            } else if (delta / current_length < ACCEPT_THRESHOLD) {
                // Accept with probability based on temperature
                double prob = exp(-delta / temperature);
                accept = (dist(rng) < prob);
            }

            if (accept) {
                two_opt_swap(tour, i + 1, j);
                current_length += delta;

                if (current_length < best_length) {
                    best_length = current_length;
                    best_tour = tour;
                }
            }

            temperature *= COOLING_RATE;
            iterations++;
        }

        tour = best_tour;
    }

    double get_tour_length() const {
        return tour_length(tour);
    }

    const vector<int>& get_tour() const {
        return tour;
    }
};

int main() {
    // Generate random cities
    mt19937 gen(RANDOM_SEED);
    uniform_real_distribution<double> coord_dist(0.0, 1000.0);

    vector<Point> cities(N_CITIES);
    for (auto& city : cities) {
        city.x = coord_dist(gen);
        city.y = coord_dist(gen);
    }

    // Solve
    auto start = chrono::high_resolution_clock::now();
    TSPSolver solver(cities);
    solver.solve();
    auto end = chrono::high_resolution_clock::now();

    double elapsed = chrono::duration<double>(end - start).count();

    // Output results
    cout << "Score: " << solver.get_tour_length() << endl;
    cout << "Time: " << elapsed << " seconds" << endl;

    // For verification (optional)
    // const auto& tour = solver.get_tour();
    // cout << "Tour: ";
    // for (int city : tour) cout << city << " ";
    // cout << endl;

    return 0;
}
