import test from 'node:test';
import assert from 'node:assert/strict';
import { validAdminRedirect, validMcpResult, probe } from './node-health.mjs';
const good = 'http://192.168.21.22:9001/#/auth/login?callback-url=http%3A%2F%2F192.168.21.22%3A9001%2Fadmin-console%2F';
const result = { jsonrpc: '2.0', id: 'dell-health-readonly', result: {
    protocolVersion: '2024-11-05', serverInfo: { name: 'fixture-server', version: 'fixture-only' },
} };
test('exact observed admin redirect accepted', () => assert.equal(validAdminRedirect(307, good), true));
test('404 and arbitrary redirects rejected', () => {
    assert.equal(validAdminRedirect(404, good), false);
    assert.equal(validAdminRedirect(307, good.replace('192.168.21.22:9001', 'evil.invalid')), false);
    assert.equal(validAdminRedirect(307, '/login'), false);
});
test('wrong callback, extra query, duplicate callback rejected', () => {
    assert.equal(validAdminRedirect(307, good.replace('admin-console', 'wrong')), false);
    assert.equal(validAdminRedirect(307, good + '&other=unknown'), false);
    assert.equal(validAdminRedirect(307, good + '&callback-url=duplicate'), false);
    assert.equal(validAdminRedirect(307, good + '?ignored=unsafe'), false);
});
test('MCP requires actual structured initialize result', () => {
    assert.equal(validMcpResult(200, result), true);
    assert.equal(validMcpResult(404, result), false);
    assert.equal(validMcpResult(200, { id: result.id, error: { code: -1 } }), false);
    assert.equal(validMcpResult(200, { ...result, result: { protocolVersion: 'x', serverInfo: null } }), false);
    assert.equal(validMcpResult(200, { ...result, id: 'wrong' }), false);
});
test('MCP session removed and no tools invoked', async () => {
    const calls = [];
    const ok = await probe('mcp', async (url, args) => {
        calls.push(args);
        return args.method === 'POST' ? new Response(`data: ${JSON.stringify(result)}\n\n`, {
            status: 200, headers: { 'mcp-session-id': 'synthetic-session' },
        }) : new Response('', { status: 200 });
    });
    assert.equal(ok, true);
    assert.deepEqual(calls.map(c => c.method), ['POST', 'DELETE']);
    assert.equal(JSON.parse(calls[0].body).method, 'initialize');
});
test('session cleanup failure is unhealthy', async () => {
    assert.equal(await probe('mcp', async (url, args) => args.method === 'POST' ?
        new Response(JSON.stringify(result), { status: 200, headers: { 'mcp-session-id': 'fixture' } }) :
        new Response('', { status: 405 })), false);
});
test('malformed MCP result still cleans its created session', async () => {
    const calls = [];
    assert.equal(await probe('mcp', async (url, args) => {
        calls.push(args.method);
        return new Response(args.method === 'POST' ? 'not-a-result' : '', {
            status: 200, headers: args.method === 'POST' ? { 'mcp-session-id': 'fixture' } : {},
        });
    }), false);
    assert.deepEqual(calls, ['POST', 'DELETE']);
});
test('unknown mode makes no network request', async () => {
    let calls = 0;
    assert.equal(await probe('unknown', async () => { calls++; }), false);
    assert.equal(calls, 0);
});
