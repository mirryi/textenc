#include <vector>

// Type alias for unsigned 8-bit integer.
using byte = unsigned char;
// Type alias for unsigned 32-bit integer.
using codepoint = unsigned int;

const byte B2_MASK = 0x1F; // 0001 1111
const byte B3_MASK = 0x0F; // 0000 1111
const byte B4_MASK = 0x07; // 0000 0111
const byte MB_MASK = 0x3F; // 0011 1111
