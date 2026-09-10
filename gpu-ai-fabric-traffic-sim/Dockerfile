FROM alpine:3.20

LABEL maintainer="Netris Solutions Architecture"
LABEL description="Pretend GPU Node container for AI Fabric traffic simulation with multi-rail iPerf3 daemons"

RUN apk update && \
    apk add --no-cache \
        bash \
        iperf3 \
        iproute2 \
        net-tools \
        ethtool \
        procps \
        coreutils \
        curl \
        jq \
        python3

WORKDIR /workspace

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose ports for 8 rails (5201 through 5208)
EXPOSE 5201-5208

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
