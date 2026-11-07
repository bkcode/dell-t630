# The exporter supplies a matching ARM64/AMD64 Chromium and its system libraries.
ARG BUILDPLATFORM
ARG PENPOT_EXPORTER_BUILD_IMAGE=penpotapp/exporter:2.18.5
ARG PENPOT_EXPORTER_IMAGE=penpotapp/exporter:2.18.5
ARG PENPOT_MCP_IMAGE=penpotapp/mcp:2.18.5
FROM --platform=$BUILDPLATFORM ${PENPOT_EXPORTER_BUILD_IMAGE} AS build
USER root
ENV NODE_OPTIONS="--max-old-space-size=512" npm_config_registry="https://registry.npmjs.org" npm_config_jobs="1"
WORKDIR /tmp/resident-worker
COPY package.json pnpm-lock.yaml tsconfig.json ./
RUN PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pnpm install --ignore-workspace --frozen-lockfile --child-concurrency=1 --network-concurrency=4
COPY src ./src
RUN pnpm run build && pnpm exec node --experimental-strip-types --test --test-concurrency=1 src/*.test.ts

FROM ${PENPOT_EXPORTER_IMAGE}
USER root
WORKDIR /opt/penpot/resident-worker
COPY --from=build /tmp/resident-worker/dist ./dist
RUN mkdir node_modules && ln -s /opt/penpot/exporter/node_modules/playwright node_modules/playwright && chown -R penpot:penpot .
USER penpot:penpot
EXPOSE 4404
HEALTHCHECK --interval=15s --timeout=5s --start-period=120s --retries=3 CMD node -e "fetch('http://127.0.0.1:4404/readyz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/index.js"]
