package com.example.myapplication.network

import android.util.Log
import com.example.myapplication.util.Constants
import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import okhttp3.*
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit
import com.example.myapplication.BuildConfig
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class WebSocketManager @Inject constructor(
    private val authInterceptor: AuthInterceptor
) {

    private val client: OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
        })
        .connectTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    private var currentWebSocket: WebSocket? = null
    private val _incomingMessages = MutableSharedFlow<MessagePayload>(extraBufferCapacity = 64)
    val incomingMessages: SharedFlow<MessagePayload> = _incomingMessages.asSharedFlow()

    data class MessagePayload(
        val id: Int,
        val chatId: Int,
        val senderId: Int,
        val content: String,
        val messageType: String,
        val attachmentUrl: String?,
        val isRead: Boolean,
        val createdAt: String,
        val updatedAt: String?
    )

    fun connect(chatId: Int, token: String) {
        if (currentWebSocket != null) {
            Log.d("WebSocketManager", "Already connected to chat $chatId")
            return
        }
        val url = "${Constants.CHAT_WS_BASE_URL}$chatId?token=$token"
        val request = Request.Builder().url(url).build()
        currentWebSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("WebSocketManager", "Connected to chat $chatId")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val payload = Gson().fromJson(text, MessagePayload::class.java)
                    _incomingMessages.tryEmit(payload) // Отправка в SharedFlow
                } catch (e: Exception) {
                    Log.e("WebSocketManager", "Failed to parse message", e)
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.d("WebSocketManager", "Closing connection: $reason")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                currentWebSocket = null
                Log.d("WebSocketManager", "Closed: $reason")
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e("WebSocketManager", "WebSocket error", t)
                currentWebSocket = null
            }
        })
    }

    fun disconnect() {
        currentWebSocket?.close(1000, "Normal closure")
        currentWebSocket = null
    }

    fun sendMessage(content: String) {
        currentWebSocket?.send(content)
    }
}