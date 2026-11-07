import fs from 'node:fs';
import { McpProbe } from '/opt/penpot/resident-worker/dist/McpProbe.js';
const c=JSON.parse(fs.readFileSync('/run/secrets/worker-credentials','utf8'));
const probe=new McpProbe('http://penpot-frontend:8080/mcp/stream?userToken='+encodeURIComponent(c.mcpKey));
try {
 const init=await probe.rpc('initialize',{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'dell-name-capability',version:'1'}});probe.protocolVersion=init.protocolVersion;await probe.rpc('notifications/initialized',undefined,true);
 const overview=await probe.rpc('tools/call',{name:'high_level_overview',arguments:{}});if(overview.isError)throw new Error('overview failed');
 const tools=await probe.rpc('tools/list',{});
 const schema=tools.tools.find(x=>x.name==='penpot_api_info');
 const docs={};
 for(const type of ['Page','File','PenpotPage','PenpotFile','PenpotUtils']) {
  const args={type};
  const d=await probe.rpc('tools/call',{name:'penpot_api_info',arguments:args});
  docs[type]={isError:!!d.isError,text:d.content?.filter(x=>x.type==='text').map(x=>x.text).join('\n')};
 }
 const state=await probe.rpc('tools/call',{name:'execute_code',arguments:{code:'return {fileId:penpot.currentFile.id,fileName:penpot.currentFile.name,pageId:penpot.currentPage.id,pageName:penpot.currentPage.name,selectionCount:penpot.selection.length,topLevel:penpotUtils.shapeStructure(penpot.currentPage.root,1)};'}});
 const tokens=await probe.rpc('tools/call',{name:'execute_code',arguments:{code:'return penpotUtils.tokenOverview();'}});
 console.log(JSON.stringify({first_tool:'high_level_overview',api_info_schema:schema?.inputSchema,docs,state,tokens,mutations:0,default_connector_used:false}));
} finally {await probe.close();}
