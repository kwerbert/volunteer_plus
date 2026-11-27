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
    
    val currentRole = MutableStateFlow(UserRole.VOLUNTEER)
    val isAdmin = MutableStateFlow(false)
    val isOrganizerSubScreenOpen = MutableStateFlow(false)

    val myOrganizationName = MutableStateFlow("Эко-Движение")
    val myOrganizationDesc = MutableStateFlow("Помощь природе и городским паркам")

    val organizedEvents = MutableStateFlow(
        listOf(
            EventItem(
                id = 201L, title = "Уборка парка Горького",
                organization = OrganizationInfo(1L, "Эко-Движение"),
                startTime = "15 мая 2026, 10:00",
                descriptionPreview = "Ежегодная акция по уборке парка.",
                whatToDo = "Сбор мусора, покраска лавочек, уборка листвы.",
                volunteerRequirements = "Возраст 18+, удобная обувь, наличие перчаток.",
                requiredVolunteers = 20,
                additionalInfo = "Сбор у главного входа в 09:45. С собой взять воду и перекус.",
                hoursReward = 4,
                isPast = false
            ),
            EventItem(
                id = 202L, title = "Высадка деревьев",
                organization = OrganizationInfo(1L, "Эко-Движение"),
                startTime = "25 мая 2026, 09:00",
                descriptionPreview = "Высадим 50 саженцев дуба.",
                whatToDo = "Копка ям, посадка саженцев, полив.",
                volunteerRequirements = "Физическая подготовка, инвентарь предоставляется.",
                requiredVolunteers = 15,
                additionalInfo = "Инвентарь будет ждать на месте. Одежда должна быть непромокаемой.",
                hoursReward = 5,
                isPast = false
            ),
            // ПРОШЕДШЕЕ МЕРОПРИЯТИЕ (для теста вкладки)
            EventItem(
                id = 203L, title = "Сбор макулатуры",
                organization = OrganizationInfo(1L, "Эко-Движение"),
                startTime = "10 апреля 2026, 12:00",
                descriptionPreview = "Собрали 500 кг бумаги. Спасибо всем участникам!",
                whatToDo = "Сортировка и взвешивание бумаги.",
                volunteerRequirements = "Ответственность.",
                requiredVolunteers = 10,
                additionalInfo = "Мероприятие завершено.",
                hoursReward = 3,
                isPast = true
            )
        )
    )

    val registeredEvents = MutableStateFlow(
        listOf(
            EventItem(
                id = 101L, title = "Уборка парка Горького",
                organization = OrganizationInfo(1L, "Эко-Движение"),
                startTime = "15 мая 2026, 10:00",
                descriptionPreview = "Не забудьте взять перчатки!"
            )
        )
    )

    val pastEvents = MutableStateFlow(
        listOf(
            EventItem(
                id = 103L, title = "Сбор макулатуры",
                organization = OrganizationInfo(3L, "Зеленый мир"),
                startTime = "10 апреля 2026",
                descriptionPreview = "Собрали 500 кг бумаги. Спасибо!"
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
    
    fun switchRole(role: UserRole) {
        currentRole.value = role
    }

    fun updateEvent(updatedEvent: EventItem) {
        organizedEvents.value = organizedEvents.value.map { 
            if (it.id == updatedEvent.id) updatedEvent else it 
        }
    }

    fun addEvent(newEvent: EventItem) {
        organizedEvents.value = listOf(newEvent) + organizedEvents.value
    }
}
