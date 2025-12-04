macro_rules! max {
    ($a:expr, $b:expr) => {
        if $a > $b { $a } else { $b }
    };
}

macro_rules! min {
    ($a:expr, $b:expr) => {
        if $a < $b { $a } else { $b }
    };
}

fn main() {
    let x = 10;
    let y = 20;

    println!("Max: {}", max!(x, y));
    println!("Min: {}", min!(x, y));
}
