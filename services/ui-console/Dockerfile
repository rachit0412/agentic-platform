FROM node:20.11.1-alpine

WORKDIR /app

# Install gitleaks for secret scanning (from official source)
RUN apk add --no-cache curl git && \
    curl -sL https://github.com/gitleaks/gitleaks/releases/download/v8.18.1/gitleaks-linux-arm64 -o /usr/local/bin/gitleaks && \
    chmod +x /usr/local/bin/gitleaks && \
    gitleaks version

COPY package.json ./
RUN npm install --production

COPY . .

EXPOSE 3001

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:3001/health || exit 1

CMD ["node", "server.js"]
