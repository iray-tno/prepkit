// Mix of custom path, const inlining, and modules
#[path = "helpers/math_functions.rs"]
mod math;

mod inline_utils {
    pub const MULTIPLIER: i32 = 10;

    pub fn scale(x: i32) -> i32 {
        x * MULTIPLIER
    }
}

const BASE_VALUE: i32 = 100;

fn main() {
    let result1 = math::add(BASE_VALUE, 50);
    let result2 = inline_utils::scale(5);

    println!("Result 1: {}", result1);
    println!("Result 2: {}", result2);
}
