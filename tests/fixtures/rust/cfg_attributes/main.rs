#[cfg(feature = "fast")]
mod fast_math;

#[cfg(not(feature = "fast"))]
mod slow_math;

fn main() {
    #[cfg(feature = "fast")]
    {
        println!("Using fast math");
    }

    #[cfg(not(feature = "fast"))]
    {
        println!("Using slow math");
    }

    let result = compute(10, 20);
    println!("Result: {}", result);
}

#[cfg(feature = "fast")]
fn compute(a: i32, b: i32) -> i32 {
    a + b // Fast version
}

#[cfg(not(feature = "fast"))]
fn compute(a: i32, b: i32) -> i32 {
    a + b // Slow version (same for demo)
}
