#!/usr/bin/env python3
"""Apply the deployment configuration adapter to the isolated Auth snapshot only."""
import hashlib,json,re,shutil,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[3];WORK=BASE/'private/java-build';PATCH=Path(__file__).resolve().parent
TARGET=WORK/'repos/finger-auth';CONFIG=TARGET/'src/main/kotlin/com/sargia/finger/gateway/auth/config/AuthorizationServerConfig.kt'
EXPECTED_ORIGINAL_SHA='7b61fbaea447688f72e9a0880d2dec01ecf27b4cbeaf558c1f9d19a93ac0d3d2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree():
 records=[]
 for f in TARGET.rglob('*'):
  if f.is_file() and not any(x in {'build','.gradle','.git'} for x in f.relative_to(TARGET).parts):records.append((str(f.relative_to(TARGET)),sha(f)))
 return hashlib.sha256(json.dumps(sorted(records),separators=(',',':')).encode()).hexdigest()
def main():
 assert sha(CONFIG)==EXPECTED_ORIGINAL_SHA,'Auth snapshot differs; inspect rather than reapply'
 before=tree();text=CONFIG.read_text()
 text=text.replace('import org.springframework.context.annotation.Bean','import org.springframework.boot.context.properties.EnableConfigurationProperties\nimport org.springframework.context.annotation.Bean',1)
 text=text.replace('@Configuration\nclass AuthorizationServerConfig(', '@Configuration\n@EnableConfigurationProperties(AuthBootstrapProperties::class)\nclass AuthorizationServerConfig(',1)
 needle='    private val accountsUserInfoClient: AccountsUserInfoClient,'
 assert needle in text;text=text.replace(needle,needle+'\n    private val bootstrapProperties: AuthBootstrapProperties,',1)
 needle='return AuthorizationServerSettings.builder().build()'
 assert text.count(needle)==1;text=text.replace(needle,'return AuthorizationServerSettings.builder().issuer(bootstrapProperties.requiredIssuer()).build()',1)
 needle='        val registeredClientRepository = JdbcRegisteredClientRepository(jdbcTemplate)'
 assert needle in text;text=text.replace(needle,'        bootstrapProperties.validateAll()\n'+needle,1)
 count=0
 methods=[('initMallAdminClient','registeredMallAdminClient'),('initMallMerchantClient','registeredMallMerchantClient'),('initMallAppClient','registeredMallAppClient'),('initMallWebClient','registeredMallWebClient')]
 for index,(name,existing) in enumerate(methods):
  start=text.index('    private fun '+name+'(')
  end=text.index('    private fun ',start+8) if index<3 else text.rfind('}')
  block=text[start:end]
  pos=block.index('\n',block.index('        val clientId ='))
  block=block[:pos]+'\n        val deploymentClient = bootstrapProperties.requiredClient(clientId)'+block[pos:]
  block,n=re.subn(r'\.clientSecret\(encodeSecret\)', '.clientSecret(bootstrapProperties.encodedSecret(clientId, '+existing+'?.clientSecret, passwordEncoder))',block)
  assert n==1,'Expected exactly one client secret initializer'
  block,n=re.subn(r'^[ \t]*val encodeSecret = passwordEncoder\.encode\(clientSecret\)\s*$', '', block, flags=re.M);assert n==1
  block,n=re.subn(r'^[ \t]*val clientSecret = \"(?:[^\"\\]|\\.)*\"\s*$', '', block, flags=re.M);assert n==1
  block,n=re.subn(r'\.redirectUri\("(?:[^"\\]|\\.)*"\)', '.redirectUris { it.addAll(deploymentClient.redirectUris) }',block);assert n==1
  block,n=re.subn(r'\.postLogoutRedirectUri\("(?:[^"\\]|\\.)*"\)', '.postLogoutRedirectUris { it.addAll(deploymentClient.postLogoutRedirectUris) }',block);assert n==1
  text=text[:start]+block+text[end:];count+=1
 assert count==4
 CONFIG.write_text(text)
 for name,directory in [('AuthBootstrapProperties.kt',TARGET/'src/main/kotlin/com/sargia/finger/gateway/auth/config'),('AuthBootstrapPropertiesTest.kt',TARGET/'src/test/kotlin/com/sargia/finger/gateway/auth/config')]:
  directory.mkdir(parents=True,exist_ok=True);shutil.copyfile(PATCH/name,directory/name)
 result={'status':'applied-to-isolated-auth-only','original_config_sha256':EXPECTED_ORIGINAL_SHA,'adapted_config_sha256':sha(CONFIG),'before_source_tree_sha256':before,'after_source_tree_sha256':tree(),'client_ids_grants_scopes_unchanged':True,'runtime_secrets_embedded':False,'original_repository_modified':False,'changes':['explicit issuer binding','required per-client secrets/callbacks','fail-closed config validation','reuse matching encoded client secret for restart stability']}
 out=WORK/'auth-deployment-patch-manifest.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');out.chmod(0o600)
 print(json.dumps(result))
if __name__=='__main__':main()
