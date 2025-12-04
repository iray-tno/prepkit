#[path = "my_utilities.rs"]
mod utils;

fn main() {
    let result = utils::add(5, 3);
    println!("Result: {}", result);
}
