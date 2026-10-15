package com.example.myapplication.data.repository
import com.example.myapplication.data.api.ChatApi
import com.example.myapplication.data.models.ChatCreateRequest
import com.example.myapplication.data.models.ChatListResponse
import com.example.myapplication.data.models.ChatResponse
import com.example.myapplication.data.models.MessageCreateRequest
import com.example.myapplication.data.models.MessagesListResponse
import com.example.myapplication.data.models.MessageResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton
@Singleton
class ChatRepository @Inject constructor(
    private val chatApi: ChatApi
) {
    suspend fun getUserChats(
        page: Int = 1,
        pageSize: Int = 20
    ): Result<ChatListResponse> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.getUserChats(page, pageSize)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка получения чатов: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun getChat(chatId: Int): Result<ChatResponse> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.getChat(chatId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка получения чата: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun getChatMessages(
        chatId: Int,
        page: Int = 1,
        pageSize: Int = 20,
        beforeMessageId: Int? = null
    ): Result<MessagesListResponse> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.getChatMessages(chatId, page, pageSize, beforeMessageId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка получения сообщений: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun sendMessage(
        chatId: Int,
        content: String,
        messageType: String = "text"
    ): Result<MessageResponse> = withContext(Dispatchers.IO) {
        try {
            val request = MessageCreateRequest(content, messageType)
            val response = chatApi.sendMessage(chatId, request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)  // ← Возвращаем MessageResponse
            } else {
                Result.failure(Exception("Ошибка отправки сообщения: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun createChat(request: ChatCreateRequest): Result<ChatResponse> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.createChat(request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка создания чата: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun markMessageRead(messageId: Int): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.markMessageRead(messageId)
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Ошибка отметки прочтения: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun markChatRead(chatId: Int): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.markChatRead(chatId)
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Ошибка отметки чата: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun leaveChat(chatId: Int): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.leaveChat(chatId)
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Ошибка выхода из чата: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun createOrganizerChat(orgId: Int): Result<ChatResponse> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.createOrganizerChat(orgId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка создания чата: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    suspend fun createEventChat(eventId: Int): Result<ChatResponse> = withContext(Dispatchers.IO) {
        try {
            val response = chatApi.createEventChat(eventId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка создания чата мероприятия: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}