#!/usr/bin/env python3
"""Gateway-only isolated deployment patch; never modifies original/shared repos."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess
BASE=Path(__file__).resolve().parents[3];PATCH=Path(__file__).resolve().parent;WORK=BASE/'private/java-build';TARGET=WORK/'repos/finger-gateway-mobile';SOURCE=Path('/Users/yangzhaohui/work/www/finger/finger-master/projects/finger-gateway-mobile')
assert TARGET.resolve()==TARGET and TARGET.is_dir()
relative='src/main/kotlin/com/sargia/finger/gateway/mobile/config/GatewayRedisConfiguration.kt';dest=TARGET/relative
baseline='''package com.sargia.finger.gateway.mobile.config

import org.springframework.context.annotation.Configuration

@Configuration(proxyBeanMethods = false)
class GatewayRedisConfiguration
'''
final=(PATCH/'GatewayRedisConfiguration.kt').read_text();assert not dest.is_symlink() and (not dest.exists() or dest.read_text() in [baseline,final]),'Unexpected isolated config content'
original_status=subprocess.check_output(['/usr/bin/git','-C',str(SOURCE),'status','--porcelain'],env={'PATH':'/usr/bin:/bin','GIT_OPTIONAL_LOCKS':'0'},text=True)
main=SOURCE/'src/main/kotlin/com/sargia/finger/gateway/mobile/MobileGatewayApplication.kt';before=hashlib.sha256(main.read_bytes()).hexdigest()
assert not (SOURCE/relative).exists(),'Original source unexpectedly contains this deployment adaptation'
dest.write_text(final);dest.chmod(0o600)
test_rel='src/test/kotlin/com/sargia/finger/gateway/mobile/config/GatewayRedisConfigurationTest.kt';test=TARGET/test_rel;test.parent.mkdir(parents=True,exist_ok=True,mode=0o700);assert not test.is_symlink();test.write_bytes((PATCH/'GatewayRedisConfigurationTest.kt').read_bytes());test.chmod(0o600)
after=subprocess.check_output(['/usr/bin/git','-C',str(SOURCE),'status','--porcelain'],env={'PATH':'/usr/bin:/bin','GIT_OPTIONAL_LOCKS':'0'},text=True);assert after==original_status and hashlib.sha256(main.read_bytes()).hexdigest()==before
manifest={'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'scope':'Gateway-only isolated explicit import; original and common library untouched','files':[{'path':str(x.relative_to(TARGET)),'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in [dest,test]],'original_source_status_unchanged':True,'shared_library_modified':False,'global_bean_overriding_enabled':False,'effective_cached_common_redis_sha256':'0285f1638de714dffdb14f8d6adb038963b8d8d2ffb868632e12866e97a67182','cached_redis_template_missing_conditional':True,'current_original_shared_source_has_missing_bean_condition':True,'runtime_activation':'manager-only-pending'}
p=WORK/'gateway-redis-import-patch-manifest.json';p.write_text(json.dumps(manifest,indent=2)+'\n');p.chmod(0o600);print(json.dumps(manifest))
