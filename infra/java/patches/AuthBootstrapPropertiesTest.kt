package com.sargia.finger.gateway.auth.config

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import org.springframework.boot.context.properties.bind.Bindable
import org.springframework.boot.context.properties.bind.Binder
import org.springframework.boot.context.properties.source.MapConfigurationPropertySource
import org.springframework.security.crypto.factory.PasswordEncoderFactories

class AuthBootstrapPropertiesTest {
    private fun configured(): AuthBootstrapProperties = AuthBootstrapProperties().apply {
        issuer = "http://10.63.20.20:9999"
        clients = AuthBootstrapProperties.REQUIRED_CLIENTS.associateWith {
            AuthBootstrapProperties.ClientSettings().apply {
                secret = "unit-fixture-not-a-runtime-secret-$it"
                redirectUris = listOf("http://10.63.20.20:9999/test-callback")
                postLogoutRedirectUris = listOf("http://10.63.20.20:9999/test-logout")
            }
        }
    }

    @Test fun `missing issuer fails before client initialization`() {
        val p = configured().apply { issuer = "" }
        assertThrows(IllegalArgumentException::class.java) { p.validateAll() }
    }

    @Test fun `missing required client or secret fails closed`() {
        val p = configured()
        p.clients = p.clients - "finger-admin"
        assertThrows(IllegalArgumentException::class.java) { p.validateAll() }
        val other = configured()
        other.clients.getValue("finger-admin").secret = ""
        assertThrows(IllegalArgumentException::class.java) { other.validateAll() }
    }

    @Test fun `issuer and callbacks are explicit external properties`() {
        val p = configured()
        p.validateAll()
        assertEquals("http://10.63.20.20:9999", p.requiredIssuer())
        assertEquals(listOf("http://10.63.20.20:9999/test-callback"), p.requiredClient("finger-admin").redirectUris)
        assertThrows(IllegalArgumentException::class.java) {
            p.clients.getValue("finger-admin").redirectUris = listOf("file:///etc/passwd")
            p.validateAll()
        }
    }

    @Test fun `unchanged configuration reuses encoded client secret across restarts`() {
        val first = configured()
        val encoder = PasswordEncoderFactories.createDelegatingPasswordEncoder()
        val encoded = first.encodedSecret("finger-admin", null, encoder)
        val second = configured()
        assertEquals(encoded, second.encodedSecret("finger-admin", encoded, encoder))
        second.clients.getValue("finger-admin").secret = "different-unit-fixture-not-a-runtime-secret"
        val rotated = second.encodedSecret("finger-admin", encoded, encoder)
        assertNotEquals(encoded, rotated)
        assertTrue(encoder.matches(second.requiredClient("finger-admin").secret, rotated))
    }

    @Test fun `binding supplies runtime values without any network or infrastructure`() {
        val values = mutableMapOf<String, Any>("finger.auth.bootstrap.issuer" to "http://10.63.20.20:9999")
        AuthBootstrapProperties.REQUIRED_CLIENTS.forEach { id ->
            val key = "finger.auth.bootstrap.clients[$id]"
            values["$key.secret"] = "unit-binding-not-a-runtime-secret-$id"
            values["$key.redirect-uris[0]"] = "http://10.63.20.20:9999/test-callback"
            values["$key.post-logout-redirect-uris[0]"] = "http://10.63.20.20:9999/test-logout"
        }
        val bound = Binder(MapConfigurationPropertySource(values))
            .bind("finger.auth.bootstrap", Bindable.of(AuthBootstrapProperties::class.java)).get()
        bound.validateAll()
        assertEquals("http://10.63.20.20:9999", bound.requiredIssuer())
        assertFalse(bound.toString().contains("unit-binding"))
        assertFalse(bound.requiredClient("finger-admin").toString().contains("unit-binding"))
    }
}
