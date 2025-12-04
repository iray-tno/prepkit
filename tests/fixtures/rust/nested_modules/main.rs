mod utils;

use utils::math::{gcd, lcm};

fn main() {
    utils::greet("World");

    let a = 12;
    let b = 18;
    println!("GCD({}, {}) = {}", a, b, gcd(a, b));
    println!("LCM({}, {}) = {}", a, b, lcm(a, b));
}
