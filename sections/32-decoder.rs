// Pretend that the imported function from_codepoint()
// converts decimal code point values to their string
// representation.
mod table;
use table::from_codepoint;

fn decode_ascii(memory: Vec<u8>) -> String {
    // Convert each codepoint to its corresponding ASCII
    // character.
    let codepoints = memory.iter().map(|n| from_codepoint(n));

    // Collect each ASCII character string to one string.
    let string: String = codepoints.collect();

    // Return the string.
    string
}
