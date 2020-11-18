#include <iostream>
#include <optional>
#include <unicode/unistr.h>
#include <vector>

#include "utf8-decoder.hpp"

std::optional<codepoint>
next_codepoint(std::vector<byte>::const_iterator &iter,
               const std::vector<byte>::const_iterator &end) {
  if (iter == end) {
    return {};
  }

  auto b0 = *iter;

  // Decode 1 byte case
  if (b0 < 128) {
    iter++;
    return (codepoint)b0;
  }

  // Decode 2 byte case
  if (++iter == end) {
    return {};
  }
  byte b1 = *iter;

  if (b0 < 0xE0) {
    iter++;
    codepoint acc = ((codepoint)(b0 & B2_MASK)) << 6;
    return acc | (codepoint)(b1 & MB_MASK);
  }

  // Decode 3 byte case
  if (++iter == end) {
    return {};
  }
  byte b2 = *iter;

  if (b0 < 0xF0) {
    iter++;
    codepoint acc = ((codepoint)(b0 & B3_MASK)) << 12;
    return acc | ((codepoint)(b1 & MB_MASK) << 6) | (codepoint)(b2 & MB_MASK);
  }

  // Decode 4 byte case
  if (++iter == end) {
    return {};
  }
  byte b3 = *iter;

  iter++;
  codepoint acc = ((codepoint)(b0 & B4_MASK)) << 18;
  return acc | ((codepoint)(b1 & MB_MASK) << 12) |
         ((codepoint)(b2 & MB_MASK) << 6) | (codepoint)(b3 & MB_MASK);
}

std::vector<codepoint> decode(const std::vector<byte> &bytes) {
  auto iter = bytes.cbegin();
  auto end = bytes.cend();

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
