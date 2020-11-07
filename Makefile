TARGET ?= target

CPPFLAGS += -std=c++17 -lstdc++ -Wconversion -Wsign-conversion

RUSTC ?= rustc
RUSTC_FLAGS := --out-dir $(TARGET)

LATEXMK ?= latexmk

DOCKER ?= docker

.PHONY : index index-docker 32-ascii-decoder 41-utf8-decoder 42-utf8-encoder create-target

index : create-target index.tex $(wildcard sections/*) references.bib
	$(LATEXMK)

index-docker : create-target index.tex $(wildcard sections/*) references.bib
	DOCKER_BUILDKIT=1	$(DOCKER) build --output $(TARGET) .

32-ascii-decoder : sections/32-decoder.rs create-target
	$(RUSTC) $(RUSTC_FLAGS) $<

41-utf8-decoder : sections/41-utf8-parser.cpp create-target
	$(CC) $(CPPFLAGS) -o $(TARGET)/$@ $<

42-utf8-encoder : sections/42-utf8-encoder.cpp create-target
	$(CC) $(CPPFLAGS) -o $(TARGET)/$@ $^

create-target :
	@mkdir -p $(TARGET)
