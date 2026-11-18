package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.data.repository.OrganizationRepository
import com.example.myapplication.data.repository.SubscriptionRepository
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OrganizationDisplayItem(
    val id: Int,
    val name: String,
    val description: String?,
    val rating: Float,
    val verified: Boolean,
    val isSubscribed: Boolean,
    val subscriptionId: Int?,
    val avatarUrl: String?
)

@HiltViewModel
class OrganizationsViewModel @Inject constructor(
    private val organizationRepository: OrganizationRepository,
    private val subscriptionRepository: SubscriptionRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    sealed class UiState {
        object Loading : UiState()
        data class Success(val organizations: List<OrganizationDisplayItem>) : UiState()
        data class Empty(val message: String) : UiState()
        data class Error(val message: String) : UiState()
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    private var currentTab = 0 // 0 - subscriptions, 1 - explore
    private var allOrgs: List<OrganizationDisplayItem> = emptyList()
    private var subscribedIds: Set<Int> = emptySet()

    init {
        loadData()
    }

    fun selectTab(tabIndex: Int) {
        currentTab = tabIndex
        emitFiltered()
    }

    fun refresh() {
        _isRefreshing.value = true
        loadData()
    }

    private fun loadData() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            try {
                val userId = sessionManager.getCurrentUserId().toInt()
                val orgsResult = organizationRepository.getOrganizations()
                val subsResult = subscriptionRepository.getSubscriptions(userId)

                if (orgsResult.isFailure) {
                    _uiState.value = UiState.Error(orgsResult.exceptionOrNull()?.message ?: "Ошибка загрузки организаций")
                    return@launch
                }

                val orgs = orgsResult.getOrDefault(emptyList())
                val subs = subsResult.getOrDefault(emptyList())

                val subsMap = subs.associate { it.orgId to it.id } // orgId -> subscriptionId

                allOrgs = orgs.map { org ->
                    val subscriptionId = subsMap[org.id]
                    OrganizationDisplayItem(
                        id = org.id,
                        name = org.name,
                        description = org.description,
                        rating = org.rating,
                        verified = org.isVerified,
                        isSubscribed = subscriptionId != null,
                        subscriptionId = subscriptionId,
                        avatarUrl = org.avatarUrl
                    )
                }
                emitFiltered()
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "Неизвестная ошибка")
            } finally {
                _isRefreshing.value = false
            }
        }
    }

    fun toggleSubscription(orgId: Int) {
        viewModelScope.launch {
            val currentItem = allOrgs.find { it.id == orgId } ?: return@launch
            if (currentItem.isSubscribed && currentItem.subscriptionId != null) {
                // Отписка
                val result = subscriptionRepository.unsubscribe(currentItem.subscriptionId)
                if (result.isSuccess) {
                    refresh()  // перезагружаем список
                } else {
                    _uiState.value = UiState.Error(result.exceptionOrNull()?.message ?: "Ошибка отписки")
                }
            } else {
                // Подписка
                val userId = sessionManager.getCurrentUserId().toInt()
                val result = subscriptionRepository.subscribe(orgId, userId)
                if (result.isSuccess) {
                    refresh()
                } else {
                    _uiState.value = UiState.Error(result.exceptionOrNull()?.message ?: "Ошибка подписки")
                }
            }
        }
    }

    private fun emitFiltered() {
        val filtered = if (currentTab == 0) {
            allOrgs.filter { it.isSubscribed }
        } else {
            allOrgs
        }

        _uiState.value = if (filtered.isEmpty()) {
            val msg = if (currentTab == 0) "У вас пока нет подписок на организации" else "Нет доступных организаций"
            UiState.Empty(msg)
        } else {
            UiState.Success(filtered)
        }
    }
}