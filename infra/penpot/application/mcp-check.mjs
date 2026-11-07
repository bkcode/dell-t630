import fs from 'node:fs';
import { McpProbe } from '/opt/penpot/resident-worker/dist/McpProbe.js';
const credentials = JSON.parse(fs.readFileSync('/run/secrets/worker-credentials', 'utf8'));
const base = 'http://penpot-frontend:8080/mcp/stream';
const params = {protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'dell-acceptance',version:'1'}};
const missing = await fetch(base,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json,text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',params})});
const missingStatus = missing.status;
await missing.body?.cancel();
let unauthenticatedDesignReadDenied=false;
const anonymousProbe=new McpProbe(base);
try {
  const a=await anonymousProbe.rpc('initialize',params);anonymousProbe.protocolVersion=a.protocolVersion;
  await anonymousProbe.rpc('notifications/initialized',undefined,true);
  const documentation=await anonymousProbe.rpc('tools/call',{name:'high_level_overview',arguments:{}});
  try { await anonymousProbe.readFile(); } catch { unauthenticatedDesignReadDenied=true; }
} finally { await anonymousProbe.close(); }
const probe = new McpProbe(base+'?userToken='+encodeURIComponent(credentials.mcpKey));
try {
  const initialized = await probe.rpc('initialize',params);
  probe.protocolVersion = initialized.protocolVersion;
  await probe.rpc('notifications/initialized',undefined,true);
  const overview = await probe.rpc('tools/call',{name:'high_level_overview',arguments:{}});
  if (overview.isError) throw new Error('overview_failed');
  const actual = await probe.readFile();
  console.log(JSON.stringify({authenticated_mcp:true,missing_key_http:missingStatus,unauthenticated_design_read_denied:unauthenticatedDesignReadDenied,first_tool:'high_level_overview',readonly_context:actual,design_mutations:0,key_emitted:false}));
} finally { await probe.close(); }
