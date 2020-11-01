FROM alpine:3.12 AS build
ARG CACHEBUST=1

RUN apk update
RUN apk add R R-dev
RUN apk add perl
RUN apk add texlive texlive-luatex
RUN apk add texmf-dist-full
RUN apk add texmf-dist-fontsextra

COPY . /build

WORKDIR /build
RUN Rscript -e "renv::hydrate()"
RUN latexmk || :

FROM scratch as export-stage
COPY --from=build /build/target .
