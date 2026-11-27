package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

data class ChatItem(
    val id: Long,
    val title: String,
    val lastMessage: String,
    val time: String,
    val unreadCount: Int = 0
)

@HiltViewModel
class ChatViewModel @Inject constructor() : ViewModel() {
    
    // Актуальные чаты
    private val _activeChats = MutableStateFlow<List<ChatItem>>(emptyList())
    val activeChats: StateFlow<List<ChatItem>> = _activeChats

    // Прошедшие чаты
    private val _pastChats = MutableStateFlow<List<ChatItem>>(emptyList())
    val pastChats: StateFlow<List<ChatItem>> = _pastChats

    init {
        _activeChats.value = listOf(
            ChatItem(1L, "Эко-Движение", "Привет! Ждем тебя на уборке в субботу.", "12:30", 2),
            ChatItem(2L, "Добрые руки", "Спасибо за помощь с собаками!", "Вчера", 0),
            ChatItem(3L, "Организатор Иван", "Отправил тебе документы по проекту.", "10 мая", 0)
        )

        _pastChats.value = listOf(
            ChatItem(4L, "Сбор макулатуры", "Чат закрыт. Спасибо за участие!", "5 апреля", 0),
            ChatItem(5L, "Посадка деревьев", "Мероприятие завершено. Фото в альбоме.", "22 апреля", 0)
        )
    }
}
