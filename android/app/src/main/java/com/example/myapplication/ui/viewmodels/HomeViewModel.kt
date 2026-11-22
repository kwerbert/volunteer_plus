package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.models.OrganizationInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor() : ViewModel() {
    private val _events = MutableStateFlow<List<EventItem>>(emptyList())
    val events: StateFlow<List<EventItem>> = _events

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    fun loadFeed(userId: Long) {
        // ВРЕМЕННЫЙ МОК: показываем карточки без интернета
        _events.value = listOf(
            EventItem(
                id = 10L,
                title = "Субботник в Сокольниках",
                organization = OrganizationInfo(10L, "Эко-Город"),
                startTime = "18 мая 2026",
                descriptionPreview = "Выходите на субботник! Вместе сделаем наш парк чище."
            ),
            EventItem(
                id = 11L,
                title = "Донорская акция",
                organization = OrganizationInfo(11L, "Красный Крест"),
                startTime = "22 мая 2026",
                descriptionPreview = "Сдайте кровь - спасите жизнь. Для доноров предусмотрены сувениры."
            )
        )
        _isLoading.value = false
    }
}
