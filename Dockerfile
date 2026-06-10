# ==========================================
# STAGE 1: Build the React & Express Application
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency catalogs
COPY package*.json ./

# Install all dependencies (including devDependencies required for bundling)
RUN npm ci

# Copy the source code
COPY . .

# Build the custom Express server bundle & React static files
RUN npm run build

# ==========================================
# STAGE 2: Lightweight Production Execution
# ==========================================
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# Copy dependency definitions
COPY package*.json ./

# Install production dependencies only to reduce space
RUN npm ci --omit=dev && npm cache clean --force

# Copy the built distributions from build stage
COPY --from=builder /app/dist ./dist

# Expose port and start
EXPOSE 3000

CMD ["npm", "run", "start"]
