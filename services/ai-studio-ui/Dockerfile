FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install --production

# Copy source
COPY server.js .
COPY index.html .

# Expose port
EXPOSE 4000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:4000/health || exit 1

# Run
CMD ["npm", "start"]
