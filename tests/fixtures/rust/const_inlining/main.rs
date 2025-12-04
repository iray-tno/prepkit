const MAX_N: i32 = 100000;
const MOD: i64 = 1000000007;
const PI: f64 = 3.14159265359;
const DEBUG: bool = true;

fn main() {
    let mut arr = vec![0; MAX_N as usize];

    for i in 0..10 {
        arr[i] = (i as i64 * i as i64) % MOD;
    }

    if DEBUG {
        println!("Array initialized with size: {}", MAX_N);
        println!("Using modulo: {}", MOD);
        println!("PI value: {}", PI);
    }
}
