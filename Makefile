index.pdf : index.tex $(wildcard sections/*)
	mkdir -p build
	latexmk index.tex
	cp build/index.pdf index.pdf

.PHONY : ascii-decoder
ascii-decoder : listings/ascii-decoder.rs
	mkdir -p build
	rustc --out-dir build $<

CPPFLAGS += -std=c++17 -lstdc++ -Wconversion -Wsign-conversion
.PHONY : utf8-decoder
utf8-decoder : listings/utf8-decoder.cpp
	mkdir -p build
	$(CC) $(CPPFLAGS) -o build/$@ $<
