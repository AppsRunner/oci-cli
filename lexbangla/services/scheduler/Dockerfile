FROM node:20-alpine AS builder
WORKDIR /app

RUN corepack enable

COPY pnpm-workspace.yaml package.json tsconfig.base.json ./
COPY packages/core/package.json packages/core/tsconfig.json packages/core/
COPY services/scheduler/package.json services/scheduler/tsconfig.json services/scheduler/

RUN pnpm install

COPY packages/core/src/ packages/core/src/
COPY services/scheduler/src/ services/scheduler/src/

RUN pnpm --filter lexbangla-scheduler build

FROM node:20-alpine
WORKDIR /app
RUN corepack enable

COPY pnpm-workspace.yaml package.json ./
COPY packages/core/package.json packages/core/
COPY services/scheduler/package.json services/scheduler/

RUN pnpm install --prod

COPY --from=builder /app/packages/core/dist packages/core/dist/
COPY --from=builder /app/services/scheduler/dist services/scheduler/dist/

EXPOSE 3001
HEALTHCHECK --interval=15s --timeout=5s CMD wget -qO- http://localhost:3001/health || exit 1
CMD ["node", "services/scheduler/dist/index.js"]
