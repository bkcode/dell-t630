package com.sargia.finger.gateway.mobile.config

import com.sargia.finger.common.redis.RedisConfig
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Import

/** Register the shared JSON RedisTemplate as user configuration before Redisson fallback beans. */
@Configuration(proxyBeanMethods = false)
@Import(RedisConfig::class)
class GatewayRedisConfiguration
