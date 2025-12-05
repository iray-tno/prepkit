mod module_a;
mod module_b;

const VALUE: i32 = 999;

fn main() {
    println!("Main VALUE: {}", VALUE);
    println!("Module A result: {}", module_a::get_value());
    println!("Module B result: {}", module_b::get_value());
}
