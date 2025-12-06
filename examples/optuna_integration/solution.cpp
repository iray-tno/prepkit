// Example competitive programming solution with tunable parameters
// This demonstrates a simulated annealing approach with hyperparameters
#include <iostream>
#include <vector>
#include <random>
#include <cmath>

// Tunable hyperparameters for optimization
constexpr double TEMP_START = 1000.0;    // @tune
constexpr double TEMP_END = 10.0;        // @tune
constexpr int BEAM_WIDTH = 50;           // @tune
constexpr double COOLING_RATE = 0.995;   // @tune

// Fixed parameters (not tunable)
constexpr int MAX_ITERATIONS = 1000;
constexpr int RANDOM_SEED = 42;

// Simulated scoring function (replace with actual problem logic)
double evaluate_solution(const std::vector<int>& solution) {
    double score = 0.0;
    for (int val : solution) {
        score += val * val;
    }
    return score;
}

int main() {
    std::mt19937 rng(RANDOM_SEED);
    std::uniform_real_distribution<double> dist(0.0, 1.0);

    // Initialize solution
    std::vector<int> current_solution(BEAM_WIDTH, 1);
    double current_score = evaluate_solution(current_solution);

    // Simulated annealing
    double temperature = TEMP_START;
    int iterations = 0;

    while (temperature > TEMP_END && iterations < MAX_ITERATIONS) {
        // Generate neighbor solution
        std::vector<int> neighbor = current_solution;
        int idx = rng() % BEAM_WIDTH;
        neighbor[idx] = (neighbor[idx] + 1) % 10;

        double neighbor_score = evaluate_solution(neighbor);

        // Accept/reject with probability based on temperature
        double delta = neighbor_score - current_score;
        double acceptance_prob = std::exp(-delta / temperature);

        if (delta < 0 || dist(rng) < acceptance_prob) {
            current_solution = neighbor;
            current_score = neighbor_score;
        }

        temperature *= COOLING_RATE;
        iterations++;
    }

    std::cout << "Final score: " << current_score << std::endl;
    std::cout << "Iterations: " << iterations << std::endl;

    return 0;
}
