# Not compatible with musl
FROM frolvlad/alpine-glibc AS build
ENV PATH="/root/bin:${PATH}"
ARG CACHEBUST=1

# Install packages
RUN apk update
RUN apk add R R-dev perl wget gnupg

# Install TinyTeX
WORKDIR /root
RUN wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh
RUN /root/.TinyTeX/bin/*/tlmgr path add
RUN tlmgr update --self

# Checkout project
COPY . /build
WORKDIR /build

# Install extra TeX packages
RUN tlmgr install $(cat packages.txt)
RUN tlmgr path add

# Hydrate R packages
RUN Rscript -e "renv::hydrate()"

# Build PDF
RUN latexmk

# Copy build to output
FROM scratch as export-stage
COPY --from=build /build/target .
