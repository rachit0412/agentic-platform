FROM node:20.11.1-alpine

WORKDIR /app

# Install gitleaks for secret scanning
RUN apk add --no-cache gitleaks git

COPY package.json ./
RUN npm install --production

COPY . .

EXPOSE 3001

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:3001/health || exit 1

CMD ["node", "server.js"]
