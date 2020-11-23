#include <iostream>
#include <optional>
#include <unicode/unistr.h>
#include <vector>

#include "utf8-decoder.hpp"

std::optional<codepoint>
next_codepoint(std::vector<byte>::const_iterator &iter,
               const std::vector<byte>::const_iterator &end) {
  if (iter == end) { // Check if iterator has reached end;
    return {};       // return nothing.
  }

  auto b0 = *iter; // Get next byte from iterator.

  // Decode 1 byte case
  if (b0 < 128) {
    iter++;               // Consume this byte from iterator.
    return (codepoint)b0; // Convert byte value to 32-bit int.
  }

  // Decode 2 byte case
  if (++iter == end) { // Check if iterator reached end;
    return {};         // return nothing.
  }
  auto b1 = *iter; // Get next byte.

  if (b0 < 0xE0) { // Check if within range for 2-byte case.
    iter++;        // Consume this byte from iterator.

    // Decode the 2 bytes and return a int value.
    codepoint acc = ((codepoint)(b0 & B2_MASK)) << 6;
    return acc | (codepoint)(b1 & MB_MASK);
  }

  // Decode 3 byte case
  if (++iter == end) {
    return {};
  }
  auto b2 = *iter;

  if (b0 < 0xF0) { // Check if within range for 3-byte case.
    iter++;

    // Decode the 3 bytes and return an int value.
    codepoint acc = ((codepoint)(b0 & B3_MASK)) << 12;
    acc = acc | ((codepoint)(b1 & MB_MASK) << 6);
    return acc | (codepoint)(b2 & MB_MASK);
  }

  // Decode 4 byte case
  if (++iter == end) {
    return {};
  }
  auto b3 = *iter;

  // Assume first byte must start with 11110.
  iter++;

  // Decode 4 bytes and return an int value.
  codepoint acc = ((codepoint)(b0 & B4_MASK)) << 18;
  acc = acc | ((codepoint)(b1 & MB_MASK) << 12);
  acc = acc | ((codepoint)(b2 & MB_MASK) << 6);
  return acc | (codepoint)(b3 & MB_MASK);
}

// Pass in a vector of bytes to decode into codepoints.
std::vector<codepoint> decode(const std::vector<byte> &bytes) {
  // Initialize iterators pointing to start and end of bytes.
  auto iter = bytes.cbegin();
  auto end = bytes.cend();

  // Decode codepoints until there are no more bytes.
  std::vector<codepoint> codepoints = {};
  while (iter != end) {
    auto cp = next_codepoint(iter, end);
    codepoints.push_back(*cp);
  }

  return codepoints;
}

int main() {
  std::string str(u8"¢€한𐍈");
  std::vector<byte> bytes(str.begin(), str.end());

  auto codepoints = decode(bytes);
  for (auto it = codepoints.cbegin(); it != codepoints.cend(); ++it) {
    std::cout << *it << " ";
  }
  std::cout << '\n';

  return 0;
}
