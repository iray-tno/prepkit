mod utils {
    pub fn helper() -> i32 {
        42
    }

    pub mod nested {
        pub fn inner() -> i32 {
            100
        }
    }
}

fn main() {
    let x = utils::helper();
    let y = utils::nested::inner();
    println!("x: {}, y: {}", x, y);
}
