mod utils;

const MAX_SIZE: i32 = 1000;

fn main() {
    // String literals should NOT be processed
    println!("This string contains mod utils; but should be preserved");
    println!("This has use utils::* in it");
    println!("MAX_SIZE should not be replaced here");
    println!("const MAX_SIZE: i32 = 9999; is fake");

    // But actual usage should work
    let size = MAX_SIZE;
    let result = utils::helper(size);

    println!("Result: {}", result);

    // Edge case: String with quote escaping
    println!("She said \"mod test;\" in the string");
    println!("Path: \"./utils.rs\"");
}
