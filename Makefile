TARGET ?= target

CPPFLAGS += -std=c++17 -lstdc++ -Wconversion -Wsign-conversion

RUSTC ?= rustc
RUSTC_FLAGS := --out-dir $(TARGET)

LATEXMK ?= latexmk

DOCKER ?= docker

.PHONY : index index-docker ascii-decoder utf8-decoder utf8-encoder create-target

index : create-target index.tex $(wildcard sections/*) references.bib
	$(LATEXMK)

index-docker : create-target index.tex $(wildcard sections/*) references.bib
	DOCKER_BUILDKIT=1	$(DOCKER) build --output $(TARGET) .

ascii-decoder : listings/ascii-decoder.rs create-target
	$(RUSTC) $(RUSTC_FLAGS) $<

utf8-decoder : listings/utf8-decoder.cpp create-target
	$(CC) $(CPPFLAGS) -o $(TARGET)/$@ $<

utf8-encoder : listings/utf8-encoder.cpp create-target
	$(CC) $(CPPFLAGS) -o $(TARGET)/$@ $<

create-target :
	@mkdir -p $(TARGET)
