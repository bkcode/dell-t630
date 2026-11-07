import fs from 'node:fs';
import { McpProbe } from '/opt/penpot/resident-worker/dist/McpProbe.js';
const credentials = JSON.parse(fs.readFileSync('/run/secrets/worker-credentials', 'utf8'));
const base = 'http://penpot-frontend:8080/mcp/stream';
const params = { protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'dell-supervisor-readonly',version:'1'} };
const anonymous = new McpProbe(base);
const authenticated = new McpProbe(base+'?userToken='+encodeURIComponent(credentials.mcpKey));
let anonymousDenied = false;
let passed = false;
try {
    const init = await anonymous.rpc('initialize', params); anonymous.protocolVersion = init.protocolVersion;
    await anonymous.rpc('notifications/initialized',undefined,true);
    const docs = await anonymous.rpc('tools/call',{name:'high_level_overview',arguments:{}});
    if (docs.isError) throw new Error('anonymous-documentation-failed');
    try { await anonymous.readFile(); } catch { anonymousDenied = true; }
    const init2 = await authenticated.rpc('initialize',params);authenticated.protocolVersion=init2.protocolVersion;
    await authenticated.rpc('notifications/initialized',undefined,true);
    const overview = await authenticated.rpc('tools/call',{name:'high_level_overview',arguments:{}});
    if (overview.isError) throw new Error('overview-failed');
    const actual = await authenticated.readFile();
    passed = anonymousDenied && actual.fileId==='13a31dab-5204-818d-8008-e7004b9343a1' &&
        actual.pageId==='13a31dab-5204-818d-8008-e7004b9343a2';
} catch { passed = false; }
finally { await anonymous.close(); await authenticated.close(); }
console.log(JSON.stringify({status:passed?'passed':'failed',first_tool:'high_level_overview',
    authenticated_readonly_context_matches:passed,unauthenticated_design_read_denied:anonymousDenied,
    design_writes:0,HTTP_body_session_or_credentials_emitted:false}));
process.exit(passed?0:1);
