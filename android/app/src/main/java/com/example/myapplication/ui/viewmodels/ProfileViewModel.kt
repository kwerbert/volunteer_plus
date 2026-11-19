package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.models.OrganizationInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class ProfileViewModel @Inject constructor() : ViewModel() {
    val userName = MutableStateFlow("Иван Волонтеров")
    val userEmail = MutableStateFlow("ivan@example.com")
    val totalHours = MutableStateFlow("124 часа")
    val organizationsCount = MutableStateFlow(3)

    // Мероприятия, куда пользователь записан (текущие)
    val registeredEvents = MutableStateFlow(
        listOf(
            EventItem(
                id = 101L,
                title = "Уборка парка Горького",
                organization = OrganizationInfo(1L, "Эко-Движение"),
                startTime = "15 мая 2026, 10:00",
                descriptionPreview = "Не забудьте взять перчатки и хорошее настроение!"
            ),
            EventItem(
                id = 102L,
                title = "Помощь приюту для животных",
                organization = OrganizationInfo(2L, "Добрые руки"),
                startTime = "20 мая 2026, 12:00",
                descriptionPreview = "Погуляем с собаками и поможем с уборкой вольеров."
            )
        )
    )

    // Мероприятия, которые уже прошли
    val pastEvents = MutableStateFlow(
        listOf(
            EventItem(
                id = 103L,
                title = "Сбор макулатуры",
                organization = OrganizationInfo(3L, "Зеленый мир"),
                startTime = "10 апреля 2026",
                descriptionPreview = "Собрали 500 кг бумаги. Спасибо за участие!"
            ),
            EventItem(
                id = 104L,
                title = "Посадка деревьев",
                organization = OrganizationInfo(1L, "Эко-Движение"),
                startTime = "22 апреля 2026",
                descriptionPreview = "Высадили 50 саженцев дуба в парке."
            )
        )
    )
}
