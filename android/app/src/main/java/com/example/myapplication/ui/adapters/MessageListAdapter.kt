package com.example.myapplication.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.data.models.MessageResponse
import java.text.SimpleDateFormat
import java.util.*

class MessageListAdapter(
    private val currentUserId: Long = 1L
) : ListAdapter<MessageResponse, MessageListAdapter.MessageViewHolder>(MessageDiffCallback()) {

    companion object {
        private const val VIEW_TYPE_MY_MESSAGE = 1
        private const val VIEW_TYPE_OTHER_MESSAGE = 2
        private val TIME_FORMAT = SimpleDateFormat("HH:mm", Locale("ru"))
    }

    inner class MessageViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val messageText: TextView = itemView.findViewById(R.id.tv_message_content)
        private val timeText: TextView = itemView.findViewById(R.id.tv_message_time)
        private val readStatusText: TextView? = itemView.findViewById(R.id.tv_read_status) // Сделал nullable

        fun bind(message: MessageResponse) {
            messageText.text = message.content
            timeText.text = try {
                val date = TIME_FORMAT.parse(message.createdAt) ?: Date()
                TIME_FORMAT.format(date)
            } catch (e: Exception) {
                ""
            }

            // Показываем статус прочтения только для своих сообщений И если view существует
            if (message.senderId.toLong() == currentUserId) {
                readStatusText?.visibility = View.VISIBLE
                readStatusText?.text = if (message.isRead) "✓✓" else "✓"
                readStatusText?.setTextColor(
                    if (message.isRead)
                        ContextCompat.getColor(itemView.context, R.color.primary)
                    else
                        ContextCompat.getColor(itemView.context, R.color.secondary)
                )
            } else {
                readStatusText?.visibility = View.GONE
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): MessageViewHolder {
        val layoutId = when (viewType) {
            VIEW_TYPE_MY_MESSAGE -> R.layout.item_message_sent
            else -> R.layout.item_message_received
        }
        val view = LayoutInflater.from(parent.context)
            .inflate(layoutId, parent, false)
        return MessageViewHolder(view)
    }

    override fun onBindViewHolder(holder: MessageViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    override fun getItemViewType(position: Int): Int {
        return if (getItem(position).senderId.toLong() == currentUserId) {
            VIEW_TYPE_MY_MESSAGE
        } else {
            VIEW_TYPE_OTHER_MESSAGE
        }
    }

    class MessageDiffCallback : DiffUtil.ItemCallback<MessageResponse>() {
        override fun areItemsTheSame(oldItem: MessageResponse, newItem: MessageResponse): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: MessageResponse, newItem: MessageResponse): Boolean {
            return oldItem.id == newItem.id &&
                    oldItem.content == newItem.content &&
                    oldItem.isRead == newItem.isRead &&
                    oldItem.createdAt == newItem.createdAt
        }
    }
}