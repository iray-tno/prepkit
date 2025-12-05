mod level1;

fn main() {
    let result = level1::level2::level3::core_function(10);
    println!("Deep nesting result: {}", result);
}
