package com.example.myapplication.firebase

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.example.myapplication.MainActivity
import com.example.myapplication.R
import com.example.myapplication.api.NotificationApiService
import com.example.myapplication.api.RegisterTokenRequest
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class MyFirebaseMessagingService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "MyFirebaseMsgService"
        private const val CHANNEL_ID = "volunteer_notifications"
        private const val CHANNEL_NAME = "Volunteer+ Notifications"

        // Статический метод для удаления токена (можно вызывать из ProfileFragment)
        fun unregisterToken(deviceToken: String, jwtToken: String) {
            // Создаём временный экземпляр (или можно использовать инжект, но для простоты так)
            val service = MyFirebaseMessagingService()
            service.unregisterTokenOnLogout(deviceToken, jwtToken)
        }
    }

    @Inject
    lateinit var notificationApiService: NotificationApiService

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "New FCM token: $token")
        sendTokenToBackend(token)
        // Сохраняем токен локально для последующего удаления
        val prefs = getSharedPreferences("volunteer_session", Context.MODE_PRIVATE)
        prefs.edit().putString("fcm_token", token).apply()
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        Log.d(TAG, "Message received from: ${message.from}")

        message.notification?.let {
            Log.d(TAG, "Notification: ${it.title} - ${it.body}")
            showNotification(
                title = it.title,
                body = it.body,
                data = message.data
            )
        }

        if (message.data.isNotEmpty()) {
            Log.d(TAG, "Data payload: ${message.data}")
            handleDataPayload(message.data)
        }
    }

    private fun sendTokenToBackend(token: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val userId = getUserIdFromStorage()
                if (userId == null) {
                    Log.w(TAG, "User not logged in, skipping token registration")
                    return@launch
                }

                val appVersion = try {
                    packageManager.getPackageInfo(packageName, 0).versionName
                } catch (e: PackageManager.NameNotFoundException) {
                    "1.0.0"
                }

                val request = RegisterTokenRequest(
                    user_id = userId,
                    device_token = token,
                    platform = "ANDROID",
                    app_version = appVersion
                )

                val response = notificationApiService.registerToken(request)
                if (response.isSuccessful) {
                    Log.d(TAG, "Token registered successfully")
                } else {
                    Log.e(TAG, "Failed to register token: ${response.code()} - ${response.errorBody()?.string()}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error sending token to backend", e)
            }
        }
    }

    // Публичный метод для удаления токена (вызывается из companion object)
    fun unregisterTokenOnLogout(deviceToken: String, jwtToken: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val response = notificationApiService.unregisterToken(deviceToken, jwtToken)
                if (response.isSuccessful) {
                    Log.d(TAG, "Token unregistered successfully on logout")
                } else {
                    Log.w(TAG, "Failed to unregister token: ${response.code()}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error unregistering token on logout", e)
            }
        }
    }

    private fun showNotification(
        title: String?,
        body: String?,
        data: Map<String, String>
    ) {
        createNotificationChannel()

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra("notification_title", title)
            putExtra("notification_body", body)
            data["notification_id"]?.toIntOrNull()?.let {
                putExtra("notification_id", it)
            }
            data["chat_id"]?.toIntOrNull()?.let {
                putExtra("chat_id", it)
            }
            data["event_id"]?.toIntOrNull()?.let {
                putExtra("event_id", it)
            }
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            System.currentTimeMillis().toInt(),
            intent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )

        val notificationIcon = if (resources.getIdentifier("ic_notification", "drawable", packageName) != 0) {
            R.drawable.ic_notification
        } else {
            R.mipmap.ic_launcher
        }

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(notificationIcon)
            .setContentTitle(title ?: "Volunteer+")
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications for Volunteer+ app"
                enableLights(true)
                enableVibration(true)
            }
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun handleDataPayload(data: Map<String, String>) {
        when (data["notification_type"]) {
            "CHAT" -> Log.d(TAG, "New chat message received")
            "NEW_EVENT" -> Log.d(TAG, "New event created")
            "EVENT_REMINDER" -> Log.d(TAG, "Event reminder")
            "SYSTEM" -> Log.d(TAG, "System notification")
        }
    }

    private fun getUserIdFromStorage(): Int? {
        val prefs = getSharedPreferences("volunteer_session", Context.MODE_PRIVATE)
        val userId = prefs.getInt("user_id", -1)
        return if (userId != -1) userId else null
    }
}