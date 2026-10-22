package com.example.myapplication.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.data.models.ChatResponse
import java.text.SimpleDateFormat
import java.util.*
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

class ChatListAdapter(
    private val onChatClick: (ChatResponse) -> Unit
) : ListAdapter<ChatResponse, ChatListAdapter.ChatViewHolder>(ChatDiffCallback()) {

    companion object {
        private val DATE_FORMAT = SimpleDateFormat("dd.MM.yyyy", Locale("ru"))
        private val TIME_FORMAT = SimpleDateFormat("HH:mm", Locale("ru"))
    }

    inner class ChatViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val titleText: TextView = itemView.findViewById(R.id.tv_chat_title)
        private val lastMessageText: TextView = itemView.findViewById(R.id.tv_last_message)
        private val timeText: TextView = itemView.findViewById(R.id.tv_chat_time)
        private val unreadCountText: TextView = itemView.findViewById(R.id.tv_unread_count)

        fun bind(chat: ChatResponse) {
            titleText.text = chat.title ?: "Чат #${chat.id}"
            lastMessageText.text = chat.lastMessage ?: "Нет сообщений"

            // Форматирование времени
            timeText.text = try {
                val date = OffsetDateTime.parse(chat.createdAt)
                date.format(DateTimeFormatter.ofPattern("HH:mm", Locale("ru")))
            } catch (e: Exception) {
                ""
            }

            // Счётчик непрочитанных
            if (chat.unreadCount > 0) {
                unreadCountText.visibility = View.VISIBLE
                unreadCountText.text = chat.unreadCount.toString()
            } else {
                unreadCountText.visibility = View.GONE
            }

            itemView.setOnClickListener { onChatClick(chat) }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ChatViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_chat, parent, false)
        return ChatViewHolder(view)
    }

    override fun onBindViewHolder(holder: ChatViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    class ChatDiffCallback : DiffUtil.ItemCallback<ChatResponse>() {
        override fun areItemsTheSame(oldItem: ChatResponse, newItem: ChatResponse): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: ChatResponse, newItem: ChatResponse): Boolean {
            return oldItem.id == newItem.id &&
                    oldItem.title == newItem.title &&
                    oldItem.lastMessage == newItem.lastMessage &&
                    oldItem.unreadCount == newItem.unreadCount &&
                    oldItem.updatedAt == newItem.updatedAt
        }
    }
}