package com.sargia.finger.gateway.auth.config

import java.net.URI
import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.security.crypto.password.PasswordEncoder

/** Deployment-only binding. No client secrets or endpoints are embedded. */
@ConfigurationProperties(prefix = "finger.auth.bootstrap")
class AuthBootstrapProperties {
    var issuer: String = ""
    var clients: Map<String, ClientSettings> = emptyMap()

    class ClientSettings {
        var secret: String = ""
        var redirectUris: List<String> = emptyList()
        var postLogoutRedirectUris: List<String> = emptyList()
        override fun toString(): String = "ClientSettings([redacted])"
    }

    fun requiredIssuer(): String {
        requireHttpUri(issuer, "Missing or invalid explicit authorization issuer")
        return issuer.trim().removeSuffix("/")
    }

    fun requiredClient(clientId: String): ClientSettings {
        val settings = clients[clientId]
            ?: throw IllegalArgumentException("Missing required OAuth client settings: $clientId")
        require(settings.secret.length >= 24) { "Missing or short OAuth client secret: $clientId" }
        require(settings.redirectUris.isNotEmpty()) { "Missing OAuth redirect URI list: $clientId" }
        require(settings.postLogoutRedirectUris.isNotEmpty()) { "Missing OAuth logout URI list: $clientId" }
        settings.redirectUris.forEach { requireHttpUri(it, "Invalid OAuth redirect URI: $clientId") }
        settings.postLogoutRedirectUris.forEach { requireHttpUri(it, "Invalid OAuth logout URI: $clientId") }
        return settings
    }

    fun validateAll() {
        requiredIssuer()
        REQUIRED_CLIENTS.forEach(::requiredClient)
    }

    fun encodedSecret(clientId: String, existingEncoded: String?, encoder: PasswordEncoder): String {
        val raw = requiredClient(clientId).secret
        if (!existingEncoded.isNullOrBlank()) {
            val matches = try { encoder.matches(raw, existingEncoded) } catch (_: IllegalArgumentException) { false }
            if (matches) return existingEncoded
        }
        return encoder.encode(raw)
    }

    override fun toString(): String = "AuthBootstrapProperties([redacted])"

    private fun requireHttpUri(raw: String, message: String) {
        val value = raw.trim()
        val uri = try { URI(value) } catch (_: Exception) { throw IllegalArgumentException(message) }
        require(value.isNotEmpty() && uri.isAbsolute && uri.scheme in setOf("http", "https") &&
            !uri.host.isNullOrBlank() && uri.rawUserInfo == null && uri.rawQuery == null &&
            uri.rawFragment == null) { message }
    }

    companion object {
        val REQUIRED_CLIENTS = listOf("finger-admin", "finger-merchant", "finger-app", "finger-web")
    }
}
