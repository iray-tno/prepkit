use std::io::{self, BufRead};

// This file is designed to test minification for size-constrained platforms
// Contains lots of comments and whitespace that should be removed

/*
 * Multi-line comment explaining the algorithm
 * This is a typical competitive programming solution
 * that needs to be minified for Codingame submission
 */

const GRID_SIZE: usize = 10;  // Grid dimensions
const MAX_MOVES: usize = 100; // Maximum number of moves

fn main() {
    // Read input dimensions
    let stdin = io::stdin();
    let mut lines = stdin.lock().lines();

    let first_line = lines.next().unwrap().unwrap();
    let dimensions: Vec<usize> = first_line
        .split_whitespace()
        .map(|s| s.parse().unwrap())
        .collect();

    let width = dimensions[0];
    let height = dimensions[1];

    // Create grid to store the game state
    let mut grid: Vec<Vec<i32>> = Vec::with_capacity(height);

    // Read the grid values
    for _ in 0..height {
        let line = lines.next().unwrap().unwrap();
        let row: Vec<i32> = line
            .split_whitespace()
            .map(|s| s.parse().unwrap())
            .collect();
        grid.push(row);  // Add row to grid
    }

    // Process the grid and find solution
    let mut result = 0;
    for y in 0..height {
        for x in 0..width {
            // Check all neighbors
            if x > 0 { result += grid[y][x - 1]; }           // Left
            if x < width - 1 { result += grid[y][x + 1]; }  // Right
            if y > 0 { result += grid[y - 1][x]; }           // Up
            if y < height - 1 { result += grid[y + 1][x]; } // Down
        }
    }

    // Output the final result
    println!("{}", result);

    // This is a comment with "code in strings" that should not affect minification
    let _debug_msg = "// This is not a comment, it's a string literal";
    let _another = "/* Also not a comment */";
}
