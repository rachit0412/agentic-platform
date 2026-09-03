FROM node:20.11.1-alpine

WORKDIR /app

# Install dependencies and gitleaks (optional - app works without it)
RUN apk add --no-cache git curl python3 py3-pip && \
    pip3 install --no-cache-dir gitleaks 2>/dev/null || echo "Gitleaks pip install skipped" && \
    which gitleaks || (echo "Gitleaks not available - secret scanning will have limited functionality")

COPY package.json ./
RUN npm install --production

COPY . .

EXPOSE 3001

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:3001/health || exit 1

CMD ["node", "server.js"]
