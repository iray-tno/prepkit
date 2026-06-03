mod helpers;

use std::cmp::Reverse;
use std::collections::HashMap;

fn main() {
    // std sub-module path: must stay `std::collections::HashMap`,
    // and the associated function must stay `HashMap::new()`.
    let mut counts: HashMap<i32, i32> = HashMap::new();

    // Associated function on a generic type / std type.
    let mut values: Vec<i32> = Vec::new();
    values.push(3);
    values.push(1);
    values.push(2);

    // `Type::method` and enum-variant style paths.
    values.sort_by_key(|&x| Reverse(x));
    let top = values.first().copied().unwrap_or_default();

    *counts.entry(top).or_insert(0) += 1;

    // Crate-internal qualified path must keep its segments.
    let scaled = helpers::scale::by_two(top);

    println!("{} {:?}", scaled, counts);
}
