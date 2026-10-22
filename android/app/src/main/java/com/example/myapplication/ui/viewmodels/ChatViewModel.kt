package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.data.models.ChatResponse
import com.example.myapplication.data.models.MessageResponse
import com.example.myapplication.data.repository.ChatRepository
import com.example.myapplication.network.WebSocketManager
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject
import kotlinx.coroutines.Job

sealed class ChatUiState {
    object Loading : ChatUiState()
    data class Success(
        val chats: List<ChatResponse> = emptyList(),
        val messages: List<MessageResponse> = emptyList(),
        val currentChat: ChatResponse? = null
    ) : ChatUiState()
    data class Error(val message: String) : ChatUiState()
}

sealed class ChatUiEvent {
    object MessageSent : ChatUiEvent()
    data class ShowError(val message: String) : ChatUiEvent()
    data class ChatCreated(val chatId: Int) : ChatUiEvent()
    data class OrganizerChatCreated(val chatId: Int, val orgId: Int) : ChatUiEvent()
}

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val repository: ChatRepository,
    private val sessionManager: SessionManager,
    private val webSocketManager: WebSocketManager
) : ViewModel() {
    private var incomingMessagesJob: Job? = null
    private val _uiState = MutableStateFlow<ChatUiState>(ChatUiState.Loading)
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private val _events = MutableStateFlow<ChatUiEvent?>(null)
    val events: StateFlow<ChatUiEvent?> = _events.asStateFlow()

    private var currentPage = 1
    private val pageSize = 20
    private var currentChatId: Int? = null
    private var isLoadingMore = false
    private var hasMoreMessages = true

    init {
        loadChats()
    }

    fun loadChats() {
        viewModelScope.launch {
            _uiState.value = ChatUiState.Loading
            repository.getUserChats(currentPage, pageSize)
                .onSuccess { response ->
                    val currentState = _uiState.value
                    _uiState.value = if (currentState is ChatUiState.Success) {
                        currentState.copy(chats = response.chats)
                    } else {
                        ChatUiState.Success(chats = response.chats)
                    }
                }
                .onFailure { error ->
                    _uiState.value = ChatUiState.Error(error.message ?: "Ошибка загрузки чатов")
                }
        }
    }

    fun createOrganizerChat(orgId: Int) {
        viewModelScope.launch {
            _uiState.value = ChatUiState.Loading
            repository.createOrganizerChat(orgId)
                .onSuccess { chat ->
                    _events.value = ChatUiEvent.OrganizerChatCreated(chat.id, orgId)
                    loadChats()
                }
                .onFailure { error ->
                    _events.value = ChatUiEvent.ShowError(error.message ?: "Ошибка создания чата")
                }
        }
    }

    fun createEventChat(eventId: Int) {
        viewModelScope.launch {
            _uiState.value = ChatUiState.Loading
            repository.createEventChat(eventId)
                .onSuccess { chat ->
                    _events.value = ChatUiEvent.ChatCreated(chat.id)
                    selectChat(chat.id)
                }
                .onFailure { error ->
                    _events.value = ChatUiEvent.ShowError(error.message ?: "Ошибка создания чата мероприятия")
                }
        }
    }

    fun selectChat(chatId: Int) {
        // Отключаем предыдущий WebSocket
        webSocketManager.disconnect()
        currentChatId = chatId
        currentPage = 1
        isLoadingMore = false
        hasMoreMessages = true

        // Подключаем WebSocket
        val token = sessionManager.accessToken
        if (!token.isNullOrEmpty()) {
            webSocketManager.connect(chatId, token)
        }

        viewModelScope.launch {
            _uiState.value = ChatUiState.Loading
            repository.getChat(chatId)
                .onSuccess { chat ->
                    loadMessages(chatId, append = false)
                    val currentState = _uiState.value
                    _uiState.value = if (currentState is ChatUiState.Success) {
                        currentState.copy(currentChat = chat)
                    } else {
                        ChatUiState.Success(currentChat = chat)
                    }
                }
                .onFailure { error ->
                    _uiState.value = ChatUiState.Error(error.message ?: "Ошибка получения чата")
                }
        }

        // Сбор входящих сообщений через WebSocket
        incomingMessagesJob?.cancel()
        incomingMessagesJob = viewModelScope.launch {
            webSocketManager.incomingMessages.collect { payload ->
                if (payload.chatId == currentChatId) {
                    val newMessage = MessageResponse(
                        id = payload.id,
                        chatId = payload.chatId,
                        senderId = payload.senderId,
                        content = payload.content,
                        messageType = payload.messageType,
                        attachmentUrl = payload.attachmentUrl,
                        isRead = payload.isRead,
                        createdAt = payload.createdAt,
                        updatedAt = payload.updatedAt
                    )
                    val currentState = _uiState.value
                    if (currentState is ChatUiState.Success) {
                        _uiState.value = currentState.copy(
                            messages = currentState.messages + newMessage
                        )
                        _events.value = ChatUiEvent.MessageSent
                    }
                }
            }
        }
    }

    fun loadMoreMessages() {
        if (isLoadingMore || !hasMoreMessages) return
        val chatId = currentChatId ?: return
        isLoadingMore = true
        loadMessages(chatId, append = true)
    }

    private fun loadMessages(chatId: Int, append: Boolean) {
        viewModelScope.launch {
            repository.getChatMessages(chatId, currentPage, pageSize)
                .onSuccess { response ->
                    val currentState = _uiState.value
                    val updatedMessages = if (append && currentState is ChatUiState.Success) {
                        response.messages + currentState.messages
                    } else {
                        response.messages
                    }
                    _uiState.value = if (currentState is ChatUiState.Success) {
                        currentState.copy(messages = updatedMessages)
                    } else {
                        ChatUiState.Success(messages = updatedMessages)
                    }
                    hasMoreMessages = response.hasMore
                    if (response.hasMore) currentPage++
                    isLoadingMore = false
                }
                .onFailure { error ->
                    _events.value = ChatUiEvent.ShowError(error.message ?: "Ошибка загрузки сообщений")
                    isLoadingMore = false
                }
        }
    }

    fun sendMessage(content: String) {
        val chatId = currentChatId ?: return
        if (content.isBlank()) return

        // Отправляем через WebSocket (мгновенно)
        webSocketManager.sendMessage(content)

        // Дублируем через HTTP для гарантии сохранения
        viewModelScope.launch {
            repository.sendMessage(chatId, content)
                .onSuccess {
                    // WebSocket уже добавил сообщение в список
                }
                .onFailure { error ->
                    _events.value = ChatUiEvent.ShowError(error.message ?: "Ошибка отправки")
                }
        }
    }

    fun createChat(
        chatType: String,
        participantIds: List<Int>,
        title: String? = null,
        organizationId: Int? = null
    ) {
        viewModelScope.launch {
            val request = com.example.myapplication.data.models.ChatCreateRequest(
                chatType = chatType,
                participantIds = participantIds,
                title = title,
                organizationId = organizationId
            )
            repository.createChat(request)
                .onSuccess { chat ->
                    _events.value = ChatUiEvent.ChatCreated(chat.id)
                    currentChatId = chat.id
                    loadChats()
                }
                .onFailure { error ->
                    _events.value = ChatUiEvent.ShowError(error.message ?: "Ошибка создания чата")
                }
        }
    }

    fun markChatAsRead(chatId: Int) {
        viewModelScope.launch {
            repository.markChatRead(chatId)
                .onFailure { error ->
                    _events.value = ChatUiEvent.ShowError(error.message ?: "Ошибка отметки прочтения")
                }
        }
    }

    fun leaveChat(chatId: Int) {
        viewModelScope.launch {
            repository.leaveChat(chatId)
                .onSuccess {
                    if (currentChatId == chatId) {
                        currentChatId = null
                        webSocketManager.disconnect()
                    }
                    loadChats()
                }
                .onFailure { error ->
                    _events.value = ChatUiEvent.ShowError(error.message ?: "Ошибка выхода из чата")
                }
        }
    }

    override fun onCleared() {
        super.onCleared()
        webSocketManager.disconnect()
    }
}