package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.data.models.OrgStats
import com.example.myapplication.data.models.ProfileData
import com.example.myapplication.data.models.UserResponse
import com.example.myapplication.data.repository.ProfileRepository
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

// Добавить класс MonthlyStat (если его нет в отдельном файле)
data class MonthlyStat(
    val year: Int,
    val month: Int,
    val hours: Float
)

sealed class ProfileUiState {
    object Loading : ProfileUiState()
    data class Success(
        val totalHours: Int = 0,
        val organizations: List<OrgStats> = emptyList(),
        val monthlyStats: List<MonthlyStat> = emptyList(),
        val userName: String = "",
        val userAvatar: String? = null,
        val email: String? = null,
        val phone: String? = null,
        val role: String = "volunteer"
    ) : ProfileUiState()
    data class Error(val message: String) : ProfileUiState()
}

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val repository: ProfileRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _uiState = MutableStateFlow<ProfileUiState>(ProfileUiState.Loading)
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    private val _becomeOrganizerResult = MutableStateFlow<Result<UserResponse>?>(null)
    val becomeOrganizerResult: StateFlow<Result<UserResponse>?> = _becomeOrganizerResult.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private var showOnlyOwnOrganizations = false
    private var selectedMainOrg: String? = null
    private var profileData: ProfileData? = null

    init {
        loadProfileData()
    }

    fun refreshProfileData() {
        loadProfileData()
    }

    private fun loadProfileData() {
        viewModelScope.launch {
            _uiState.value = ProfileUiState.Loading
            val userId = sessionManager.getCurrentUserId()
            val profileResult = repository.getProfileData(userId)
            val monthlyResult = repository.getMonthlyStats(userId)

            val monthlyStats = monthlyResult.getOrElse { emptyList() }

            profileResult.onSuccess { data ->
                profileData = data
                _uiState.value = ProfileUiState.Success(
                    totalHours = data.totalHours,
                    organizations = data.organizations,
                    monthlyStats = monthlyStats,
                    userName = data.userName,
                    userAvatar = data.avatarUrl,
                    email = data.email,
                    phone = data.phone,
                    role = data.role ?: "volunteer"
                )
            }.onFailure { error ->
                _uiState.value = ProfileUiState.Error(error.message ?: "Ошибка загрузки")
            }
        }
    }

    fun selectMainOrganization(orgName: String) {
        val org = profileData?.organizations?.find { it.name == orgName }
        if (org == null) {
            _errorMessage.value = "Организация не найдена в вашем профиле"
            return
        }
        if (org.organizationId <= 0L) {
            _errorMessage.value = "Некорректный ID организации"
            return
        }

        selectedMainOrg = orgName

        viewModelScope.launch {
            repository.updateMainOrganization(
                sessionManager.getCurrentUserId(),
                org.organizationId
            ).onSuccess {
                sessionManager.mainOrganizationName = orgName
                sessionManager.mainOrganizationId = org.organizationId
            }.onFailure { error ->
                _errorMessage.value = error.message ?: "Ошибка сохранения основной организации"
            }
        }
    }

    fun getSavedOrganizationName(): String? = sessionManager.mainOrganizationName

    fun setShowOnlyOwnOrganizations(show: Boolean) {
        showOnlyOwnOrganizations = show
        loadProfileData()
    }

    fun getProfileData(): ProfileData? = profileData

    fun becomeOrganizer() {
        viewModelScope.launch {
            val userId = sessionManager.getCurrentUserId()
            val result = repository.becomeOrganizer(userId)
            _becomeOrganizerResult.value = result
            if (result.isSuccess) {
                refreshProfileData()
            } else {
                _errorMessage.value = result.exceptionOrNull()?.message ?: "Ошибка при получении роли организатора"
            }
        }
    }

    fun clearErrorMessage() {
        _errorMessage.value = null
    }
}