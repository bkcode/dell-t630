ARG BUILDPLATFORM
ARG PENPOT_EXPORTER_BUILD_IMAGE=penpotapp/exporter:2.18.5
ARG PENPOT_EXPORTER_IMAGE=penpotapp/exporter:2.18.5
ARG PENPOT_MCP_IMAGE=penpotapp/mcp:2.18.5
FROM --platform=$BUILDPLATFORM ${PENPOT_EXPORTER_BUILD_IMAGE} AS build
USER root
ENV NODE_OPTIONS="--max-old-space-size=512" npm_config_registry="https://registry.npmjs.org" npm_config_jobs="1"
WORKDIR /tmp/file-import
COPY package.json pnpm-lock.yaml tsconfig.json ./
RUN pnpm install --ignore-workspace --frozen-lockfile --child-concurrency=1 --network-concurrency=4
COPY src ./src
COPY verify-pure-js.mjs ./verify-pure-js.mjs
RUN pnpm run build \
    && pnpm exec node --experimental-strip-types --test --test-concurrency=1 src/*.test.ts \
    && pnpm prune --prod --ignore-workspace \
    && node verify-pure-js.mjs \
    && mkdir jobs

FROM ${PENPOT_MCP_IMAGE}
WORKDIR /opt/penpot/file-import
COPY --from=build /tmp/file-import/dist ./dist
COPY --from=build /tmp/file-import/node_modules ./node_modules
COPY package.json ./package.json
COPY --from=build --chown=node:node /tmp/file-import/jobs /data/jobs
EXPOSE 4405
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 CMD ["node", "-e", "fetch('http://127.0.0.1:4405/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "dist/index.js"]
