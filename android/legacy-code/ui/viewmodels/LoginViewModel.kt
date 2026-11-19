// File: app/src/main/java/com/example/myapplication/ui/viewmodels/LoginViewModel.kt
package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.data.repository.AuthRepository
import com.example.myapplication.util.JwtUtils
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Состояние UI экрана входа
 */
data class LoginUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val email: String = "",
    val password: String = ""
)

/**
 * События UI экрана входа
 */
sealed class LoginUiEvent {
    object LoginSuccess : LoginUiEvent()
    object RegisterSuccess : LoginUiEvent()
    object DevLoginSuccess : LoginUiEvent()
    data class ShowError(val message: String) : LoginUiEvent()
}

/**
 * ViewModel для экрана входа/регистрации
 */
@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    private val _events = MutableStateFlow<LoginUiEvent?>(null)
    val events: StateFlow<LoginUiEvent?> = _events.asStateFlow()

    /**
     * Вход пользователя
     */
    fun login(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            authRepository.login(email, password)
                .onSuccess { tokens ->
                    // Извлекаем роль из access токена
                    val role = JwtUtils.extractRole(tokens.accessToken)
                    sessionManager.saveAuthData(
                        accessToken = tokens.accessToken,
                        refreshToken = tokens.refreshToken,
                        userId = tokens.userId,
                        expiresIn = tokens.expiresIn,
                        role = role
                    )
                    sessionManager.isLoggedIn = true
                    _events.value = LoginUiEvent.LoginSuccess
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = error.message ?: "Ошибка входа"
                    )
                    _events.value = LoginUiEvent.ShowError(error.message ?: "Ошибка входа")
                }
        }
    }

    /**
     * Регистрация пользователя
     */
    fun register(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            authRepository.register(email, password)
                .onSuccess { tokens ->
                    val role = JwtUtils.extractRole(tokens.accessToken)
                    sessionManager.saveAuthData(
                        accessToken = tokens.accessToken,
                        refreshToken = tokens.refreshToken,
                        userId = tokens.userId,
                        expiresIn = tokens.expiresIn,
                        role = role
                    )
                    sessionManager.isLoggedIn = true
                    _uiState.value = _uiState.value.copy(isLoading = false)
                    _events.value = LoginUiEvent.RegisterSuccess
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = error.message ?: "Ошибка регистрации"
                    )
                    _events.value = LoginUiEvent.ShowError(error.message ?: "Ошибка регистрации")
                }
        }
    }

    /**
     * Быстрый вход для DEV-режима (без ввода данных)
     */
    fun devQuickLogin() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            authRepository.login("test@example.com", "password123")
                .onSuccess { tokens ->
                    val role = JwtUtils.extractRole(tokens.accessToken)
                    sessionManager.saveAuthData(
                        accessToken = tokens.accessToken,
                        refreshToken = tokens.refreshToken,
                        userId = tokens.userId,
                        expiresIn = tokens.expiresIn,
                        role = role
                    )
                    sessionManager.isLoggedIn = true
                    _uiState.value = _uiState.value.copy(isLoading = false)
                    _events.value = LoginUiEvent.DevLoginSuccess
                }
                .onFailure {
                    _uiState.value = _uiState.value.copy(isLoading = false)
                    _events.value = LoginUiEvent.ShowError("Не удалось войти в dev-режиме. Проверьте сервер.")
                }
        }
    }

    fun updateEmail(email: String) {
        _uiState.value = _uiState.value.copy(email = email)
    }

    fun updatePassword(password: String) {
        _uiState.value = _uiState.value.copy(password = password)
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}