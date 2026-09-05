FROM node:20.11.1-alpine

WORKDIR /app

# Install runtime tooling needed by admin-plane operations.
ARG GITLEAKS_VERSION=8.18.4
ARG TARGETARCH
RUN set -eux; \
        apk add --no-cache git curl python3 py3-pip docker-cli tar; \
        case "${TARGETARCH:-}" in \
            amd64) gitleaks_arch='x64' ;; \
            arm64) gitleaks_arch='arm64' ;; \
            *) apk_arch="$(apk --print-arch)"; \
                 case "$apk_arch" in \
                     x86_64) gitleaks_arch='x64' ;; \
                     aarch64) gitleaks_arch='arm64' ;; \
                     *) echo "Unsupported arch: $apk_arch" >&2; exit 1 ;; \
                 esac ;; \
        esac; \
        curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${gitleaks_arch}.tar.gz" -o /tmp/gitleaks.tar.gz; \
        tar -xzf /tmp/gitleaks.tar.gz -C /tmp; \
        install -m 0755 /tmp/gitleaks /usr/local/bin/gitleaks; \
        rm -f /tmp/gitleaks /tmp/gitleaks.tar.gz; \
        gitleaks version; \
        docker --version

COPY package.json ./
RUN npm install --production

COPY . .

EXPOSE 3001

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:3001/health || exit 1

CMD ["node", "server.js"]
