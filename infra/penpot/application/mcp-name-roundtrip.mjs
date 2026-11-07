import fs from 'node:fs';
import crypto from 'node:crypto';
import readline from 'node:readline';
import { McpProbe } from '/opt/penpot/resident-worker/dist/McpProbe.js';

// Target-only server permission acceptance. Never use this on a design file.
const FILE = '13a31dab-5204-818d-8008-e7004b9343a1';
const PAGE = '13a31dab-5204-818d-8008-e7004b9343a2';
const OLD = 'Page 1';
const NONCE = 'Dell MCP name acceptance ' + new Date().toISOString() + '-' + crypto.randomBytes(4).toString('hex');
if (process.env.DELL_MCP_NAME_ROUNDTRIP !== 'parent-approved-target250-window') {
  throw new Error('This controlled write requires the reviewed target250 window');
}
const credentials = JSON.parse(fs.readFileSync('/run/secrets/worker-credentials', 'utf8'));
const probe = new McpProbe('http://penpot-frontend:8080/mcp/stream?userToken=' + encodeURIComponent(credentials.mcpKey));
const receipt = { captured_at: new Date().toISOString(), file_id: FILE, page_id: PAGE,
  property: 'Page.name', original: OLD, nonce: NONCE, first_tool: 'high_level_overview',
  target_only: true, default_connector_used: false, events: [], restored: false };
let attempted = false;
const input = readline.createInterface({input: process.stdin, terminal: false});
const incoming = input[Symbol.asyncIterator]();
async function backend(label, expected) {
  console.log(JSON.stringify({backend_check: label, expected}));
  const line = await incoming.next();
  if (line.done) throw new Error('Independent backend verifier disconnected');
  const reply = JSON.parse(line.value);
  receipt.events.push({label, backend: reply});
  if (!reply.ok) throw new Error('Independent backend persistence unconfirmed: ' + label);
}

const guard = `if(penpot.currentFile.id!==${JSON.stringify(FILE)}||penpot.currentPage.id!==${JSON.stringify(PAGE)}||penpot.currentFile.name!=="Dell dedicated MCP acceptance")throw new Error("Wrong acceptance context");if(penpotUtils.shapeStructure(penpot.currentPage.root,1).children.length!==0||penpot.selection.length!==0)throw new Error("Acceptance page no longer empty");`;
async function execute(label, code) {
  const response = await probe.rpc('tools/call', { name: 'execute_code', arguments: { code: guard + code } });
  if (response.isError) throw new Error(label + ': execute_code rejected');
  const value = JSON.parse(response.content.filter(x => x.type === 'text').map(x => x.text).join('\n'));
  if (!Object.hasOwn(value, 'result')) throw new Error(label + ': result absent');
  receipt.events.push({ label, result: value.result });
  return value.result;
}
async function read(label) {
  return execute(label, 'return {fileId:penpot.currentFile.id,pageId:penpot.currentPage.id,name:penpot.currentPage.name};');
}
async function restore() {
  const now = await read('before-restore');
  if (now.name === NONCE) {
    await execute('restore-original', `if(penpot.currentPage.name!==${JSON.stringify(NONCE)})throw new Error("Concurrent name change");penpot.currentPage.name=${JSON.stringify(OLD)};return {restorationRequested:true};`);
  } else if (now.name !== OLD) throw new Error('Concurrent name change; restoration refused');
  const restored = await read('verify-restored');
  if (restored.name !== OLD) throw new Error('Original page name not restored');
  await backend('backend-verify-restored', OLD);
  receipt.restored = true;
}
try {
  const init = await probe.rpc('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'dell-controlled-name-roundtrip', version: '1' } });
  probe.protocolVersion = init.protocolVersion;
  await probe.rpc('notifications/initialized', undefined, true);
  const overview = await probe.rpc('tools/call', { name: 'high_level_overview', arguments: {} });
  if (overview.isError) throw new Error('Overview failed');
  const docs = await probe.rpc('tools/call', { name: 'penpot_api_info', arguments: { type: 'Page', member: 'name' } });
  const text = docs.content.filter(x => x.type === 'text').map(x => x.text).join('\n');
  if (docs.isError || !text.includes('name: string') || text.includes('readonly')) throw new Error('Writable Page.name documentation unconfirmed');
  receipt.api_member_documentation = text;
  const initial = await read('initial');
  if (initial.name !== OLD) throw new Error('Original page name changed since approval');
  await backend('backend-initial', OLD);
  attempted = true;
  await execute('set-nonce', `if(penpot.currentPage.name!==${JSON.stringify(OLD)})throw new Error("Concurrent name change");penpot.currentPage.name=${JSON.stringify(NONCE)};return {name:penpot.currentPage.name};`);
  const changed = await read('verify-nonce');
  if (changed.name !== NONCE) throw new Error('Authenticated MCP write not observable');
  await backend('backend-verify-nonce', NONCE);
  receipt.authenticated_write_read_confirmed = true;
  await restore();
  receipt.status = 'passed';
} catch (error) {
  receipt.status = 'failed';
  receipt.failure = error.message;
  if (attempted && !receipt.restored) {
    try { await restore(); } catch (cleanup) { receipt.restoration_failure = cleanup.message; }
  }
} finally {
  try { await probe.close(); } catch { receipt.session_close_failed = true; }
  input.close();
  console.log(JSON.stringify({receipt}));
}
if (receipt.status !== 'passed' || !receipt.restored) process.exitCode = 1;
