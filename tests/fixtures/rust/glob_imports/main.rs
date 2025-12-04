mod math;

use math::*;  // Glob import - imports all public items

fn main() {
    let a = 10;
    let b = 5;

    // All these functions come from glob import
    println!("Add: {}", add(a, b));
    println!("Sub: {}", sub(a, b));
    println!("Mul: {}", mul(a, b));
}
