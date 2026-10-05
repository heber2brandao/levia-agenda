FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
ENV VITE_DEMO_MODE=false
RUN node -e 'if (!process.env.VITE_SUPABASE_PUBLISHABLE_KEY?.startsWith("sb_publishable_") || !process.env.VITE_API_URL?.startsWith("https://") || !process.env.VITE_SUPABASE_URL?.startsWith("https://")) process.exit(1)' && npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
