package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.repository.FeedRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val feedRepository: FeedRepository
) : ViewModel() {

    private val _events = MutableStateFlow<List<EventItem>>(emptyList())
    val events: StateFlow<List<EventItem>> = _events

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    fun loadFeed(userId: Long) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            val result = feedRepository.getFeed(userId)
            result.onSuccess { feedResponse ->
                _events.value = feedResponse.sections.flatMap { it.events }
            }.onFailure { error ->
                _error.value = error.message
            }
            _isLoading.value = false
        }
    }
}
