package com.arya.avatar.data.api

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class TokenResponse(
    val access_token: String,
    val refresh_token: String,
    val token_type: String = "bearer",
)

@JsonClass(generateAdapter = true)
data class LoginRequest(val email: String, val password: String)

@JsonClass(generateAdapter = true)
data class RegisterRequest(
    val email: String,
    val password: String,
    val display_name: String = "",
)

@JsonClass(generateAdapter = true)
data class UserDto(
    val id: String,
    val email: String,
    val display_name: String,
    val role: String,
    val remaining_minutes: Int,
    val quota_minutes: Int,
    val used_minutes: Int,
)

@JsonClass(generateAdapter = true)
data class ConsentRequest(
    val understand_ai: Boolean,
    val voice_processing: Boolean,
    val store_transcripts: Boolean = false,
    val improve_service: Boolean = false,
)

@JsonClass(generateAdapter = true)
data class BootstrapDto(
    val maintenance_mode: Boolean,
    val captions_default: Boolean,
    val barge_in_enabled: Boolean,
    val consent_version: String,
    val consent_required: Boolean,
    val ai_disclosure: String,
)

@JsonClass(generateAdapter = true)
data class AvatarDto(
    val id: String,
    val name: String,
    val description: String,
    val category: String,
    val thumbnail_url: String,
    val provider: String,
    val is_featured: Boolean = false,
    val greeting: String? = null,
)

@JsonClass(generateAdapter = true)
data class SessionCreateRequest(
    val avatar_id: String,
    val captions_enabled: Boolean? = null,
)

@JsonClass(generateAdapter = true)
data class SessionDto(
    val id: String,
    val avatar_id: String,
    val provider: String,
    val status: String,
    val room_url: String,
    val room_token: String,
    val captions_enabled: Boolean,
    val barge_in_enabled: Boolean,
    val mock_mode: Boolean = true,
    val greeting: String = "",
)

@JsonClass(generateAdapter = true)
data class SessionEndRequest(val reason: String = "user_ended")
