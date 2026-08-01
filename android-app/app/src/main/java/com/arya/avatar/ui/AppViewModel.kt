package com.arya.avatar.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.arya.avatar.data.AryaRepository
import com.arya.avatar.data.TokenStore
import com.arya.avatar.data.api.AvatarDto
import com.arya.avatar.data.api.SessionDto
import com.arya.avatar.data.api.UserDto
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@HiltViewModel
class AppViewModel @Inject constructor(
    private val repo: AryaRepository,
    private val tokenStore: TokenStore,
) : ViewModel() {

    private val _user = MutableStateFlow<UserDto?>(null)
    val user: StateFlow<UserDto?> = _user

    private val _avatars = MutableStateFlow<List<AvatarDto>>(emptyList())
    val avatars: StateFlow<List<AvatarDto>> = _avatars

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading

    var lastSession: SessionDto? = null
        private set

    var disclosure: String = ""
        private set

    suspend fun resolveStartDestination(): String {
        val token = tokenStore.accessToken.first()
        if (token.isNullOrBlank()) return Routes.ONBOARDING
        return try {
            _user.value = repo.me()
            val boot = repo.bootstrapMe()
            disclosure = boot.ai_disclosure
            if (boot.consent_required) Routes.CONSENT else Routes.GALLERY
        } catch (_: Exception) {
            tokenStore.clear()
            Routes.LOGIN
        }
    }

    fun login(email: String, password: String, onDone: (needsConsent: Boolean) -> Unit) {
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            try {
                repo.login(email, password)
                _user.value = repo.me()
                val boot = repo.bootstrapMe()
                disclosure = boot.ai_disclosure
                onDone(boot.consent_required)
            } catch (e: Exception) {
                _error.value = e.message ?: "Login failed"
            } finally {
                _loading.value = false
            }
        }
    }

    fun loadDisclosure(onReady: (String) -> Unit) {
        viewModelScope.launch {
            try {
                val b = repo.bootstrap()
                disclosure = b.ai_disclosure
                onReady(b.ai_disclosure)
            } catch (_: Exception) {
                onReady("You will be talking to an AI avatar, not a human.")
            }
        }
    }

    fun submitConsent(
        understand: Boolean,
        voice: Boolean,
        store: Boolean,
        improve: Boolean,
        onDone: () -> Unit,
    ) {
        viewModelScope.launch {
            _loading.value = true
            try {
                repo.submitConsent(understand, voice, store, improve)
                onDone()
            } catch (e: Exception) {
                _error.value = e.message
            } finally {
                _loading.value = false
            }
        }
    }

    fun loadGallery() {
        viewModelScope.launch {
            try {
                _avatars.value = repo.avatars()
                _user.value = repo.me()
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun startSession(avatarId: String, onReady: (String) -> Unit) {
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            try {
                val session = repo.startSession(avatarId)
                lastSession = session
                onReady(session.id)
            } catch (e: Exception) {
                _error.value = e.message
            } finally {
                _loading.value = false
            }
        }
    }

    fun endSession(id: String, onDone: () -> Unit) {
        viewModelScope.launch {
            try {
                repo.endSession(id)
            } catch (_: Exception) {
            }
            onDone()
        }
    }

    suspend fun accessToken(): String? = tokenStore.getAccess()
}
