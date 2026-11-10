/** SSH stdio bridge. Credentials are read only inside the existing VM250 importer. */
import { readFileSync } from 'node:fs';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema, McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';

const mode = process.argv[1];
let upstream;
let downstream;
let closing = false;
let phase = 'startup';

async function close() {
    if (closing) return;
    closing = true;
    await Promise.allSettled([upstream?.close(), downstream?.close()]);
}

async function main() {
    if (!['core', 'import'].includes(mode)) throw new Error('invalid_mode');
    const credentials = JSON.parse(readFileSync('/run/secrets/worker-credentials', 'utf8'));
    const token = credentials.mcpKey;
    if (typeof token !== 'string' || !/^[A-Za-z0-9._~+/=-]+$/.test(token)) {
        throw new Error('invalid_server_credential');
    }

    const url = new URL(mode === 'core'
        ? 'http://penpot-frontend:8080/mcp/stream'
        : 'http://127.0.0.1:4405/mcp');
    const options = {};
    if (mode === 'core') url.searchParams.set('userToken', token);
    else options.requestInit = { headers: { Authorization: `Bearer ${token}` } };

    upstream = new Client({ name: `dell-penpot-ssh-${mode}`, version: '1.0.0' }, { capabilities: {} });
    // Keep transport errors out of stdout and never print the credential-bearing URL.
    upstream.onerror = () => {};
    phase = 'upstream-connect';
    await upstream.connect(new StreamableHTTPClientTransport(url, options));

    downstream = new Server(
        { name: `dell-penpot-ssh-${mode}`, version: '1.0.0' },
        { capabilities: { tools: {} }, instructions: upstream.getInstructions() },
    );
    downstream.onerror = () => {};
    downstream.setRequestHandler(ListToolsRequestSchema, async (request, extra) => {
        try {
            return await upstream.listTools(request.params, { signal: extra.signal });
        } catch {
            throw new McpError(ErrorCode.InternalError, 'Penpot MCP tool discovery failed');
        }
    });
    downstream.setRequestHandler(CallToolRequestSchema, async (request, extra) => {
        try {
            return await upstream.callTool(request.params, undefined, { signal: extra.signal });
        } catch {
            throw new McpError(ErrorCode.InternalError, 'Penpot MCP tool request failed');
        }
    });
    downstream.onclose = () => { void close(); };
    phase = 'stdio-connect';
    await downstream.connect(new StdioServerTransport());
}

for (const signal of ['SIGINT', 'SIGTERM']) {
    process.once(signal, () => { void close().finally(() => process.exit(0)); });
}
process.stdin.once('end', () => { void close().finally(() => process.exit(0)); });
main().catch(() => {
    process.stderr.write(`Penpot MCP bridge unavailable (${phase}).\n`);
    void close().finally(() => process.exit(1));
});
