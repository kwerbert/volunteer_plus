package com.example.myapplication.data.api
import com.example.myapplication.data.models.ChatCreateRequest
import com.example.myapplication.data.models.ChatListResponse
import com.example.myapplication.data.models.ChatResponse
import com.example.myapplication.data.models.MessageCreateRequest
import com.example.myapplication.data.models.MessagesListResponse
import com.example.myapplication.data.models.MessageResponse
import retrofit2.Response
import retrofit2.http.*

interface ChatApi {
    @GET("api/v1/chats")
    suspend fun getUserChats(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): Response<ChatListResponse>

    @GET("api/v1/chats/{chat_id}")
    suspend fun getChat(
        @Path("chat_id") chatId: Int
    ): Response<ChatResponse>

    @GET("api/v1/chats/{chat_id}/messages")
    suspend fun getChatMessages(
        @Path("chat_id") chatId: Int,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("before_message_id") beforeMessageId: Int? = null
    ): Response<MessagesListResponse>

    @POST("api/v1/chats/{chat_id}/messages")
    suspend fun sendMessage(
        @Path("chat_id") chatId: Int,
        @Body request: MessageCreateRequest
    ): Response<MessageResponse>

    @POST("api/v1/chats")
    suspend fun createChat(
        @Body request: ChatCreateRequest
    ): Response<ChatResponse>

    // НОВОЕ: Специальный эндпоинт для чата с организатором
    @POST("api/v1/chats/organizer/{org_id}")
    suspend fun createOrganizerChat(
        @Path("org_id") orgId: Int
    ): Response<ChatResponse>

    @PUT("api/v1/messages/{message_id}/read")
    suspend fun markMessageRead(
        @Path("message_id") messageId: Int
    ): Response<Unit>

    @POST("api/v1/chats/{chat_id}/read-all")
    suspend fun markChatRead(
        @Path("chat_id") chatId: Int
    ): Response<Unit>

    @DELETE("api/v1/chats/{chat_id}")
    suspend fun leaveChat(
        @Path("chat_id") chatId: Int
    ): Response<Unit>

    @POST("api/v1/chats/event/{event_id}")
    suspend fun createEventChat(@Path("event_id") eventId: Int): Response<ChatResponse>
}