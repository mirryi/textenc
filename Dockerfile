FROM alpine:3.12 AS build
ARG CACHEBUST=1

RUN apk update
RUN apk add R R-dev perl \
            texlive texlive-luatex \
            texmf-dist-full \
            texmf-dist-fontsextra

COPY . /build

WORKDIR /build
RUN Rscript -e "renv::hydrate()"
RUN latexmk

FROM scratch as export-stage
COPY --from=build /build/target .
