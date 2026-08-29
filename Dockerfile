# ─── Stage: base ──────────────────────────────────────────────────────────────
FROM node:22-alpine AS base
WORKDIR /workspace
COPY app/package*.json ./app/

# ─── Stage: dev (hot-reload) ──────────────────────────────────────────────────
FROM base AS dev
WORKDIR /workspace/app
RUN npm install
# Private data is mounted at /workspace/data (see docker-compose)
EXPOSE 5173
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]

# ─── Stage: builder (app only — no clinical data in the image) ────────────────
FROM base AS builder
WORKDIR /workspace
RUN cd app && npm install
COPY app/ ./app/
RUN cd app && npm run build

# ─── Stage: prod (nginx) ──────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS prod
COPY --from=builder /workspace/app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/nginx-entrypoint.sh /nginx-entrypoint.sh
RUN chmod +x /nginx-entrypoint.sh
EXPOSE 80
ENV DATA_DIR=/data
CMD ["/nginx-entrypoint.sh"]
