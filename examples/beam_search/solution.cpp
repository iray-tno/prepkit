// Beam Search Example: Job Scheduling Problem
// This is a typical heuristic contest pattern where beam search parameters
// significantly affect solution quality

#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <random>

using namespace std;

// Tunable hyperparameters for Optuna optimization
constexpr int BEAM_WIDTH = 100;           // @tune
constexpr int SEARCH_DEPTH = 20;          // @tune
constexpr double RANDOMNESS = 0.1;        // @tune
constexpr double GREEDY_WEIGHT = 0.7;     // @tune

// Fixed parameters
constexpr int NUM_JOBS = 50;
constexpr int NUM_MACHINES = 5;
constexpr int RANDOM_SEED = 42;

struct State {
    vector<vector<int>> schedule;  // schedule[machine] = list of jobs
    vector<int> machine_loads;     // total time on each machine
    double score;

    State() : schedule(NUM_MACHINES), machine_loads(NUM_MACHINES, 0), score(0.0) {}

    bool operator<(const State& other) const {
        return score > other.score;  // Max heap
    }
};

class BeamSearchSolver {
private:
    vector<int> job_times;
    mt19937 rng;

    double evaluate(const State& state) const {
        // Minimize makespan (max machine load)
        int makespan = *max_element(state.machine_loads.begin(), state.machine_loads.end());

        // Add variance penalty to balance load
        double avg_load = 0.0;
        for (int load : state.machine_loads) avg_load += load;
        avg_load /= NUM_MACHINES;

        double variance = 0.0;
        for (int load : state.machine_loads) {
            variance += (load - avg_load) * (load - avg_load);
        }
        variance /= NUM_MACHINES;

        // Lower is better, so negate for max heap
        return -(makespan + 0.1 * sqrt(variance));
    }

    vector<State> expand(const State& state, int job_idx) {
        vector<State> neighbors;

        if (job_idx >= NUM_JOBS) return neighbors;

        // Try assigning next job to each machine
        vector<pair<double, int>> candidates;
        for (int m = 0; m < NUM_MACHINES; m++) {
            State next = state;
            next.schedule[m].push_back(job_idx);
            next.machine_loads[m] += job_times[job_idx];
            next.score = evaluate(next);

            // Greedy score: prefer machines with lower load
            double greedy_score = -next.machine_loads[m];
            double total_score = GREEDY_WEIGHT * greedy_score + (1 - GREEDY_WEIGHT) * next.score;

            candidates.push_back({total_score, m});
        }

        // Sort candidates
        sort(candidates.begin(), candidates.end(), greater<pair<double, int>>());

        // Add some randomness
        uniform_real_distribution<double> dist(0.0, 1.0);

        for (auto [score, m] : candidates) {
            if (dist(rng) < RANDOMNESS) continue;  // Skip with probability

            State next = state;
            next.schedule[m].push_back(job_idx);
            next.machine_loads[m] += job_times[job_idx];
            next.score = evaluate(next);
            neighbors.push_back(next);
        }

        return neighbors;
    }

public:
    BeamSearchSolver(const vector<int>& times) : job_times(times), rng(RANDOM_SEED) {}

    State solve() {
        priority_queue<State> beam;
        State initial;
        initial.score = evaluate(initial);
        beam.push(initial);

        for (int job = 0; job < min(NUM_JOBS, SEARCH_DEPTH); job++) {
            priority_queue<State> next_beam;

            // Expand beam
            while (!beam.empty()) {
                State current = beam.top();
                beam.pop();

                vector<State> neighbors = expand(current, job);
                for (const State& neighbor : neighbors) {
                    next_beam.push(neighbor);
                }
            }

            // Keep top BEAM_WIDTH states
            beam = priority_queue<State>();
            int count = 0;
            while (!next_beam.empty() && count < BEAM_WIDTH) {
                beam.push(next_beam.top());
                next_beam.pop();
                count++;
            }

            if (beam.empty()) break;
        }

        return beam.empty() ? State() : beam.top();
    }
};

int main() {
    // Generate job times (deterministic for testing)
    mt19937 gen(RANDOM_SEED);
    uniform_int_distribution<int> dist(10, 100);

    vector<int> job_times(NUM_JOBS);
    for (int& t : job_times) {
        t = dist(gen);
    }

    // Solve
    BeamSearchSolver solver(job_times);
    State solution = solver.solve();

    // Output results
    cout << "Score: " << -solution.score << endl;
    cout << "Makespan: " << *max_element(solution.machine_loads.begin(), solution.machine_loads.end()) << endl;
    cout << "Machine loads: ";
    for (int load : solution.machine_loads) {
        cout << load << " ";
    }
    cout << endl;

    return 0;
}
