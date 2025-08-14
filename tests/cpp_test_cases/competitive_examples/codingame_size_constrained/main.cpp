#include <iostream>
#include <vector>
#include <algorithm>

// This file is designed to test minification for size-constrained platforms
// Contains lots of comments and whitespace that should be removed

/*
 * Multi-line comment explaining the algorithm
 * This is a typical competitive programming solution
 * that needs to be minified for Codingame submission
 */

constexpr int GRID_SIZE = 10;  // Grid dimensions
constexpr int MAX_MOVES = 100; // Maximum number of moves

int main() {
    // Read input dimensions
    int width, height;
    std::cin >> width >> height;
    
    // Create grid to store the game state  
    std::vector<std::vector<int>> grid(height, std::vector<int>(width));
    
    // Read the grid values
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            std::cin >> grid[y][x];  // Read each cell
        }
    }
    
    // Process the grid and find solution
    int result = 0;
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            // Check all neighbors
            if (x > 0) result += grid[y][x-1];           // Left
            if (x < width-1) result += grid[y][x+1];     // Right  
            if (y > 0) result += grid[y-1][x];           // Up
            if (y < height-1) result += grid[y+1][x];    // Down
        }
    }
    
    // Output the final result
    std::cout << result << std::endl;
    
    return 0;  // Success exit code
}