pub fn helper(x: i32) -> i32 {
    // String in module should also be preserved
    println!("Inside helper: mod should not be removed");
    x * 2
}
