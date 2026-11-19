package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.models.OrganizationInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject

@HiltViewModel
class EventsViewModel @Inject constructor() : ViewModel() {

    sealed class UiState {
        object Loading : UiState()
        data class Success(val events: List<EventItem>) : UiState()
        data class Empty(val message: String) : UiState()
        data class Error(val message: String) : UiState()
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Success(getUpcomingEvents()))
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    fun selectTab(tabIndex: Int) {
        if (tabIndex == 0) {
            _uiState.value = UiState.Success(getUpcomingEvents())
        } else {
            _uiState.value = UiState.Empty("Нет прошедших мероприятий (заглушка)")
        }
    }

    private fun getUpcomingEvents(): List<EventItem> {
        return listOf(
            EventItem(
                id = 1L,
                title = "Уборка парка Горького",
                organization = OrganizationInfo(1L, "Эко-Движение"),
                startTime = "15 мая 2026",
                descriptionPreview = "Поможем природе и очистим парк от мусора. Присоединяйтесь к нашей команде!"
            ),
            EventItem(
                id = 2L,
                title = "Помощь приюту для животных",
                organization = OrganizationInfo(2L, "Добрые руки"),
                startTime = "20 мая 2026",
                descriptionPreview = "Погуляем с собаками и поможем с уборкой вольеров. Нужны добровольцы."
            ),
            EventItem(
                id = 3L,
                title = "Сбор макулатуры",
                organization = OrganizationInfo(3L, "Зеленый мир"),
                startTime = "25 мая 2026",
                descriptionPreview = "Сдай бумагу - спаси дерево!"
            )
        )
    }
}
