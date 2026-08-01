package com.arya.avatar.data.api

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.HTTP
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface AryaApi {
    @POST("api/v1/auth/login")
    suspend fun login(@Body body: LoginRequest): TokenResponse

    @POST("api/v1/auth/register")
    suspend fun register(@Body body: RegisterRequest): TokenResponse

    @GET("api/v1/auth/me")
    suspend fun me(): UserDto

    @POST("api/v1/auth/consent")
    suspend fun consent(@Body body: ConsentRequest): Map<String, Any>

    @GET("api/v1/bootstrap/me")
    suspend fun bootstrapMe(): BootstrapDto

    @GET("api/v1/bootstrap")
    suspend fun bootstrap(): BootstrapDto

    @GET("api/v1/avatars")
    suspend fun avatars(@Query("q") q: String? = null): List<AvatarDto>

    @GET("api/v1/avatars/{id}")
    suspend fun avatar(@Path("id") id: String): AvatarDto

    @POST("api/v1/sessions")
    suspend fun startSession(@Body body: SessionCreateRequest): SessionDto

    @HTTP(method = "DELETE", path = "api/v1/sessions/{id}", hasBody = true)
    suspend fun endSession(
        @Path("id") id: String,
        @Body body: SessionEndRequest = SessionEndRequest(),
    ): SessionDto
}
