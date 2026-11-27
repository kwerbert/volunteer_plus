package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.models.OrganizationInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import javax.inject.Inject

enum class UserRole { VOLUNTEER, ORGANIZER, ADMIN }

@HiltViewModel
class ProfileViewModel @Inject constructor() : ViewModel() {
    val userName = MutableStateFlow("Иван Волонтеров")
    val userEmail = MutableStateFlow("ivan@example.com")
    val totalHours = MutableStateFlow("124 часа")
    val organizationsCount = MutableStateFlow(3)
    
    // Роль пользователя
    val currentRole = MutableStateFlow(UserRole.VOLUNTEER)
    val isAdmin = MutableStateFlow(false) // Флаг админа (по плану одноклассника)

    val registeredEvents = MutableStateFlow(
        listOf(
            EventItem(
                id = 101L, title = "Уборка парка Горького",
                organization = OrganizationInfo(1L, "Эко-Движение"),
                startTime = "15 мая 2026, 10:00",
                descriptionPreview = "Не забудьте взять перчатки и хорошее настроение!"
            )
        )
    )

    val pastEvents = MutableStateFlow(
        listOf(
            EventItem(
                id = 103L, title = "Сбор макулатуры",
                organization = OrganizationInfo(3L, "Зеленый мир"),
                startTime = "10 апреля 2026",
                descriptionPreview = "Собрали 500 кг бумаги. Спасибо за участие!"
            )
        )
    )

    val mySubscriptions = MutableStateFlow(
        listOf(
            OrganizationItem(1L, "Эко-Движение", "Помощь природе и городским паркам", 4.9f, true),
            OrganizationItem(2L, "Добрые руки", "Приют для бездомных животных", 4.7f, true)
        )
    )

    fun unsubscribe(orgId: Long) {
        mySubscriptions.value = mySubscriptions.value.filter { it.id != orgId }
    }
    
    // Имитация подачи заявки на организатора и одобрения админом
    fun becomeOrganizer() {
        currentRole.value = UserRole.ORGANIZER
    }
}
