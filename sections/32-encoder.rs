// In this pseudo-Rust, pretend that

// Pretend `table(char)` translates that characters to its
// corresponding ASCII codepoint in base 10.
fn get_codepoint(c: char) -> u8 {
    table(c)
}

fn encode(s: &str) ->
