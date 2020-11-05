#include <Rcpp.h>
#include <iostream>
#include <vector>

#include "41-utf8-parser.hpp"

// [[Rcpp::plugins(cpp17)]]

// [[Rcpp::export]]
std::vector<unsigned int> test() {
  std::string str(u8"¢€한𐍈");
  std::vector<unsigned char> bytes(str.begin(), str.end());

  return decode(bytes);
}
