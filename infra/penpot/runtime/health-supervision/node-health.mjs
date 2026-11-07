// Fixed credential-free probes. Never prints responses or session IDs.
import { pathToFileURL } from 'node:url';
export function validAdminRedirect(status, raw) {
    try {
        const location = new URL(raw ?? '', 'http://127.0.0.1:3000');
        const fragment = location.hash.slice(1);
        const position = fragment.indexOf('?');
        const route = position < 0 ? fragment : fragment.slice(0, position);
        const parameters = new URLSearchParams(position < 0 ? '' : fragment.slice(position + 1));
        return status === 307 && location.origin === 'http://192.168.21.22:9001' &&
            location.pathname === '/' && location.search === '' && route === '/auth/login' &&
            [...parameters.keys()].length === 1 && parameters.get('callback-url') ===
            'http://192.168.21.22:9001/admin-console/';
    } catch { return false; }
}
export function validMcpResult(status, data) {
    return status === 200 && data?.id === 'dell-health-readonly' && !data.error &&
        typeof data.result?.protocolVersion === 'string' && data.result.protocolVersion.length > 0 &&
        typeof data.result?.serverInfo?.name === 'string' &&
        typeof data.result?.serverInfo?.version === 'string';
}
export async function probe(mode, fetcher = fetch) {
    let session;
    const mcpUrl = 'http://127.0.0.1:4401/mcp';
    let passed = false;
    try {
        if (mode === 'admin-console') {
            const response = await fetcher('http://127.0.0.1:3000/admin-console/', {
                redirect: 'manual', signal: AbortSignal.timeout(4000),
            });
            passed = validAdminRedirect(response.status, response.headers.get('location'));
            await response.body?.cancel();
        } else if (mode === 'mcp') {
            const response = await fetcher(mcpUrl, {
                method: 'POST', redirect: 'error', signal: AbortSignal.timeout(5000),
                headers: { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' },
                body: JSON.stringify({ jsonrpc: '2.0', id: 'dell-health-readonly', method: 'initialize',
                    params: { protocolVersion: '2024-11-05', capabilities: {},
                        clientInfo: { name: 'dell-health-supervision', version: '1.0' } } }),
            });
            session = response.headers.get('mcp-session-id');
            const raw = await response.text();
            let data;
            try { data = JSON.parse(raw); } catch {
                const line = raw.split('\n').find(value => value.startsWith('data: '));
                if (line) data = JSON.parse(line.slice(6));
            }
            passed = validMcpResult(response.status, data);
        }
    } catch { passed = false; }
    finally {
        if (session) {
            try {
                const closed = await fetcher(mcpUrl, {
                    method: 'DELETE', redirect: 'error', signal: AbortSignal.timeout(4000),
                    headers: { 'Mcp-Session-Id': session, Accept: 'application/json, text/event-stream' },
                });
                passed = passed && [200, 204].includes(closed.status);
                await closed.body?.cancel();
            } catch { passed = false; }
        }
    }
    return passed;
}
if (process.argv[1] === '-' || (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href)) {
    process.exit(await probe(process.argv[2]) ? 0 : 1);
}
