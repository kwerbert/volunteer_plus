package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.repository.FeedRepository
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import javax.inject.Inject

@HiltViewModel
class EventsViewModel @Inject constructor(
    private val feedRepository: FeedRepository,
    private val sessionManager: SessionManager
) : ViewModel() {

    sealed class UiState {
        object Loading : UiState()
        data class Success(val events: List<EventItem>) : UiState()
        data class Empty(val message: String) : UiState()
        data class Error(val message: String) : UiState()
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    private var currentTab = 0 // 0 - upcoming, 1 - past
    private var allEvents: List<EventItem> = emptyList()
    private val formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss")

    init {
        loadEvents()
    }

    fun selectTab(tabIndex: Int) {
        currentTab = tabIndex
        filterAndEmit()
    }

    fun refresh() {
        _isRefreshing.value = true
        loadEvents()
    }

    private fun loadEvents() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            try {
                val userId = sessionManager.getCurrentUserId()
                val result = feedRepository.getFeed(userId = userId, page = 1, pageSize = 50)
                result.onSuccess { feed ->
                    // собираем все события из всех секций
                    allEvents = feed.sections.flatMap { it.events }
                    filterAndEmit()
                }.onFailure { error ->
                    // fallback to cache
                    feedRepository.getCachedFeed().onSuccess { cached ->
                        // cached содержит CachedEventEntity, конвертируем в EventItem (упрощённо)
                        allEvents = cached.map { entity ->
                            EventItem(
                                id = entity.id,
                                title = entity.title,
                                organization = com.example.myapplication.data.models.OrganizationInfo(0, entity.organizationName, null, 0f, false, null),
                                startTime = entity.startTime,
                                endTime = entity.endTime ?: entity.startTime,
                                descriptionPreview = entity.descriptionPreview,
                                locationLat = entity.locationLat,
                                locationLon = entity.locationLon,
                                distanceKm = entity.distanceKm
                            )
                        }
                        filterAndEmit()
                    }.onFailure {
                        _uiState.value = UiState.Error(error.message ?: "Ошибка загрузки")
                    }
                }
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "Неизвестная ошибка")
            } finally {
                _isRefreshing.value = false
            }
        }
    }

    private fun filterAndEmit() {
        val now = java.time.OffsetDateTime.now()
        val upcoming = allEvents.filter { event ->
            try {
                java.time.OffsetDateTime.parse(event.startTime).isAfter(now)
            } catch (e: Exception) { false }
        }.sortedBy { it.startTime }

        val past = allEvents.filter { event ->
            try {
                java.time.OffsetDateTime.parse(event.startTime).isBefore(now)
            } catch (e: Exception) { false }
        }.sortedByDescending { it.startTime }

        val eventsToShow = if (currentTab == 0) upcoming else past

        _uiState.value = if (eventsToShow.isEmpty()) {
            UiState.Empty(if (currentTab == 0) "Нет предстоящих мероприятий" else "Нет прошедших мероприятий")
        } else {
            UiState.Success(eventsToShow)
        }
    }
}