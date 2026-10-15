package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.data.models.EventRegistrationResponse
import com.example.myapplication.data.models.ParticipationResponse
import com.example.myapplication.data.models.SubscriptionResponse
import com.example.myapplication.data.models.SubscriptionCheckResponse
import com.example.myapplication.data.repository.EventRepository
import com.example.myapplication.data.repository.SubscriptionRepository
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class EventDetailsViewModel @Inject constructor(
    private val eventRepository: EventRepository,
    private val subscriptionRepository: SubscriptionRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _registrationResult = MutableStateFlow<Result<EventRegistrationResponse>?>(null)
    val registrationResult: StateFlow<Result<EventRegistrationResponse>?> = _registrationResult.asStateFlow()

    private val _subscriptionResult = MutableStateFlow<Result<SubscriptionResponse>?>(null)
    val subscriptionResult: StateFlow<Result<SubscriptionResponse>?> = _subscriptionResult.asStateFlow()

    private val _checkInResult = MutableStateFlow<Result<ParticipationResponse>?>(null)
    val checkInResult: StateFlow<Result<ParticipationResponse>?> = _checkInResult.asStateFlow()

    //НОВЫЕ ПОЛЯ для отписки/статуса
    private val _subscriptionStatus = MutableStateFlow<SubscriptionCheckResponse?>(null)
    val subscriptionStatus: StateFlow<SubscriptionCheckResponse?> = _subscriptionStatus.asStateFlow()

    private val _toggleSubscriptionResult = MutableStateFlow<Result<Unit>?>(null)
    val toggleSubscriptionResult: StateFlow<Result<Unit>?> = _toggleSubscriptionResult.asStateFlow()

    fun registerForEvent(eventId: Int) {
        viewModelScope.launch {
            val userId = sessionManager.getCurrentUserId().toInt()
            val result = eventRepository.registerForEvent(eventId, userId)
            _registrationResult.value = result
        }
    }

    fun subscribeToOrganization(orgId: Int) {
        viewModelScope.launch {
            val userId = sessionManager.getCurrentUserId().toInt()
            val result = subscriptionRepository.subscribe(orgId, userId)
            _subscriptionResult.value = result
        }
    }

    fun checkIn(eventId: Int, qrCode: String) {
        viewModelScope.launch {
            val userId = sessionManager.getCurrentUserId().toInt()
            val result = eventRepository.checkIn(eventId, userId, qrCode)
            _checkInResult.value = result
        }
    }

    //НОВЫЙ МЕТОД: загрузить статус подписки
    fun loadSubscriptionStatus(orgId: Int) {
        viewModelScope.launch {
            val userId = sessionManager.getCurrentUserId().toInt()
            val result = subscriptionRepository.checkSubscriptionStatus(userId, orgId)
            if (result.isSuccess) {
                _subscriptionStatus.value = result.getOrNull()
            } else {
                _subscriptionStatus.value = null
            }
        }
    }

    //НОВЫЙ МЕТОД: переключить подписку
    fun toggleOrganizationSubscription(orgId: Int) {
        viewModelScope.launch {
            val currentStatus = _subscriptionStatus.value
            if (currentStatus?.isSubscribed == true && currentStatus.subscriptionId != null) {
                // Отписка
                val result = subscriptionRepository.unsubscribe(currentStatus.subscriptionId)
                _toggleSubscriptionResult.value = result
                if (result.isSuccess) {
                    loadSubscriptionStatus(orgId) // обновить статус после отписки
                }
            } else {
                // Подписка
                val userId = sessionManager.getCurrentUserId().toInt()
                val result = subscriptionRepository.subscribe(orgId, userId)
                _toggleSubscriptionResult.value = result.map { Unit }
                if (result.isSuccess) {
                    loadSubscriptionStatus(orgId)
                }
            }
        }
    }
}