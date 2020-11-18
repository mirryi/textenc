FROM ubuntu:18.04 as build
ENV PATH="/root/bin:${PATH}"

# Install packages
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y --fix-missing \
  r-base r-base-dev perl wget gnupg \
  fonts-firacode fontconfig
RUN fc-cache -f -v

# Install TinyTeX
WORKDIR /root
RUN wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh
RUN /root/.TinyTeX/bin/*/tlmgr path add
RUN tlmgr update --self

# Install extra TeX packages
WORKDIR /build
COPY packages.txt /build
RUN tlmgr install $(cat packages.txt)
RUN tlmgr path add

# Checkout project
COPY . /build

# Hydrate R packages
RUN Rscript -e "renv::restore()"

# Build PDF
RUN latexmk || latexmk

# Copy build to output
FROM scratch as export-stage
COPY --from=build /build/target .
