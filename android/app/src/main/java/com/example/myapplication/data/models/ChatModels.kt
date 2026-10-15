package com.example.myapplication.data.models

import com.google.gson.annotations.SerializedName
import android.os.Parcelable
import kotlinx.parcelize.Parcelize
import java.util.Date

// ==================== REQUEST MODELS ====================

data class ChatCreateRequest(
    @SerializedName("chat_type")
    val chatType: String,  // "organizer" или "event"
    @SerializedName("participant_ids")
    val participantIds: List<Int>,
    @SerializedName("title")
    val title: String? = null,
    @SerializedName("event_id")
    val eventId: Int? = null,
    @SerializedName("organization_id")
    val organizationId: Int? = null
)


data class MessageCreateRequest(
    @SerializedName("content")
    val content: String,
    @SerializedName("message_type")
    val messageType: String = "text", // "text", "image", "file"
    @SerializedName("attachment_url")
    val attachmentUrl: String? = null
)

// ==================== RESPONSE MODELS ====================

@Parcelize
data class ChatResponse(
    @SerializedName("id")
    val id: Int,
    @SerializedName("chat_type")
    val chatType: String,
    @SerializedName("title")
    val title: String? = null,
    @SerializedName("event_id")
    val eventId: Int? = null,
    @SerializedName("organization_id")
    val organizationId: Int? = null,
    @SerializedName("created_at")
    val createdAt: String,
    @SerializedName("updated_at")
    val updatedAt: String? = null,
    @SerializedName("last_message")
    val lastMessage: String? = null,
    @SerializedName("unread_count")
    val unreadCount: Int = 0,
    @SerializedName("members")
    val members: List<ChatMemberResponse> = emptyList()
) : Parcelable

@Parcelize
data class ChatMemberResponse(
    @SerializedName("user_id")
    val userId: Int,
    @SerializedName("role")
    val role: String,
    @SerializedName("joined_at")
    val joinedAt: String,
    @SerializedName("is_muted")
    val isMuted: Boolean = false
) : Parcelable

@Parcelize
data class MessageResponse(
    @SerializedName("id")
    val id: Int,
    @SerializedName("chat_id")
    val chatId: Int,
    @SerializedName("sender_id")
    val senderId: Int,
    @SerializedName("content")
    val content: String,
    @SerializedName("message_type")
    val messageType: String,
    @SerializedName("attachment_url")
    val attachmentUrl: String? = null,
    @SerializedName("is_read")
    val isRead: Boolean = false,
    @SerializedName("created_at")
    val createdAt: String,
    @SerializedName("updated_at")
    val updatedAt: String? = null
) : Parcelable

data class ChatListResponse(
    @SerializedName("chats")
    val chats: List<ChatResponse>,
    @SerializedName("total")
    val total: Int,
    @SerializedName("has_more")
    val hasMore: Boolean = false,
    @SerializedName("next_offset")
    val nextOffset: Int? = null
)

data class MessagesListResponse(
    @SerializedName("messages")
    val messages: List<MessageResponse>,
    @SerializedName("total")
    val total: Int,
    @SerializedName("has_more")
    val hasMore: Boolean = false,
    @SerializedName("next_offset")
    val nextOffset: Int? = null
)