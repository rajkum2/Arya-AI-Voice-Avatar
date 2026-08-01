package com.arya.avatar.data

import com.arya.avatar.data.api.AryaApi
import com.arya.avatar.data.api.AvatarDto
import com.arya.avatar.data.api.BootstrapDto
import com.arya.avatar.data.api.ConsentRequest
import com.arya.avatar.data.api.LoginRequest
import com.arya.avatar.data.api.RegisterRequest
import com.arya.avatar.data.api.SessionCreateRequest
import com.arya.avatar.data.api.SessionDto
import com.arya.avatar.data.api.UserDto
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AryaRepository @Inject constructor(
    private val api: AryaApi,
    private val tokenStore: TokenStore,
) {
    suspend fun login(email: String, password: String) {
        val tokens = api.login(LoginRequest(email, password))
        tokenStore.save(tokens.access_token, tokens.refresh_token)
    }

    suspend fun register(email: String, password: String, name: String) {
        val tokens = api.register(RegisterRequest(email, password, name))
        tokenStore.save(tokens.access_token, tokens.refresh_token)
    }

    suspend fun logout() = tokenStore.clear()

    suspend fun me(): UserDto = api.me()

    suspend fun bootstrapMe(): BootstrapDto = api.bootstrapMe()

    suspend fun bootstrap(): BootstrapDto = api.bootstrap()

    suspend fun submitConsent(
        understand: Boolean,
        voice: Boolean,
        store: Boolean,
        improve: Boolean,
    ) {
        api.consent(
            ConsentRequest(
                understand_ai = understand,
                voice_processing = voice,
                store_transcripts = store,
                improve_service = improve,
            ),
        )
    }

    suspend fun avatars(): List<AvatarDto> = api.avatars()

    suspend fun avatar(id: String): AvatarDto = api.avatar(id)

    suspend fun startSession(avatarId: String): SessionDto =
        api.startSession(SessionCreateRequest(avatar_id = avatarId))

    suspend fun endSession(id: String): SessionDto = api.endSession(id)
}
