FROM alpine:3.12 AS build
ARG CACHEBUST=1

RUN apk update
RUN apk add R perl
RUN apk add texlive texlive-luatex
RUN apk add texmf-dist-full

COPY . /build

WORKDIR /build
RUN Rscript -e "renv::hydrate()"
RUN latexmk || :

FROM scratch as export-stage
COPY --from=build /build/target .
