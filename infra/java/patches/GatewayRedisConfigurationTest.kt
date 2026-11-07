package com.sargia.finger.gateway.mobile.config

import com.sargia.finger.common.redis.RedisConfig
import java.lang.reflect.Proxy
import java.util.function.Supplier
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertSame
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.redisson.api.RedissonClient
import org.redisson.api.RedissonReactiveClient
import org.redisson.api.RedissonRxClient
import org.redisson.spring.starter.RedissonAutoConfigurationV2
import org.springframework.boot.autoconfigure.AutoConfigurations
import org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration
import org.springframework.boot.test.context.runner.ApplicationContextRunner
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.DeferredImportSelector
import org.springframework.context.annotation.Import
import org.springframework.core.type.AnnotationMetadata
import org.springframework.data.redis.connection.RedisConnectionFactory
import org.springframework.data.redis.core.RedisTemplate
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer
import org.springframework.data.redis.serializer.StringRedisSerializer

class GatewayRedisConfigurationTest {
    private fun <T> disconnected(type: Class<T>): T =
        type.cast(
            Proxy.newProxyInstance(type.classLoader, arrayOf(type)) { proxy, method, args ->
                when (method.name) {
                    "toString" -> "disconnected-unit-fixture-${type.simpleName}"
                    "hashCode" -> System.identityHashCode(proxy)
                    "equals" -> proxy === args?.firstOrNull()
                    else -> throw AssertionError("Unexpected infrastructure interaction: ${type.simpleName}.${method.name}")
                }
            }
        )

    private val factory = disconnected(RedisConnectionFactory::class.java)
    private val client = disconnected(RedissonClient::class.java)
    private val reactive = disconnected(RedissonReactiveClient::class.java)
    private val rx = disconnected(RedissonRxClient::class.java)

    private fun runner() =
        ApplicationContextRunner()
            .withAllowBeanDefinitionOverriding(false)
            .withBean(RedisConnectionFactory::class.java, Supplier { factory })
            .withBean(RedissonClient::class.java, Supplier { client })
            .withBean(RedissonReactiveClient::class.java, Supplier { reactive })
            .withBean(RedissonRxClient::class.java, Supplier { rx })

    private fun assertSharedJsonTemplate(context: org.springframework.boot.test.context.assertj.AssertableApplicationContext) {
        assertNull(context.startupFailure, context.startupFailure?.javaClass?.name)
        val template = context.getBean("redisTemplate", RedisTemplate::class.java)
        assertTrue(template.keySerializer is StringRedisSerializer)
        assertTrue(template.hashKeySerializer is StringRedisSerializer)
        assertTrue(template.valueSerializer is GenericJackson2JsonRedisSerializer)
        assertTrue(template.hashValueSerializer is GenericJackson2JsonRedisSerializer)
        assertSame(factory, template.connectionFactory)
        assertSame(client, context.getBean(RedissonClient::class.java))
        assertNotNull(context.getBean(RedissonAutoConfigurationV2::class.java))
    }

    @Test
    fun `gateway user import preserves JSON template with actual auto configurations`() {
        runner()
            .withUserConfiguration(GatewayRedisConfiguration::class.java)
            .withConfiguration(
                AutoConfigurations.of(
                    RedisAutoConfiguration::class.java,
                    RedissonAutoConfigurationV2::class.java,
                    RedisConfig::class.java,
                )
            )
            .run { assertSharedJsonTemplate(it) }
    }

    @Configuration(proxyBeanMethods = false)
    @Import(ObservedRedisImportSelector::class)
    class ObservedRedisAutoConfigurationOrder

    // Preserve the real deferred-import phase while reproducing the observed runtime order.
    class ObservedRedisImportSelector : DeferredImportSelector {
        override fun selectImports(importingClassMetadata: AnnotationMetadata): Array<String> =
            arrayOf(
                RedissonAutoConfigurationV2::class.java.name,
                RedisConfig::class.java.name,
                RedisAutoConfiguration::class.java.name,
            )
    }

    @Test
    fun `gateway import survives the observed Redisson before legacy shared config order`() {
        runner()
            .withUserConfiguration(
                GatewayRedisConfiguration::class.java,
                ObservedRedisAutoConfigurationOrder::class.java,
            )
            .run { assertSharedJsonTemplate(it) }
    }
}
