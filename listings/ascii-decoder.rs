// Pretend that the imported function from_codepoint()
// converts decimal code point values to their string
// representation.
use table::from_codepoint;

fn decode_ascii(memory: &[u8]) -> String {
    // Convert each codepoint to its corresponding ASCII
    // character.
    let codepoints = memory.iter().map(|n| from_codepoint(*n));

    // Collect each ASCII character string to one string.
    let string: String = codepoints.collect();

    // Return the string.
    string
}

mod table {
    pub fn from_codepoint(cp: u8) -> char {
        cp as char
    }
}

fn main() {
    let memory = vec![72, 101, 108, 108, 111, 32, 119, 111, 114, 108, 100, 33];
    let string = decode_ascii(&memory);
    println!("{}", string);
}
