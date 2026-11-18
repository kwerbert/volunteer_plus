package com.example.myapplication.util

import com.example.myapplication.BuildConfig

object Constants {
    // Базовый URL для всех микросервисов (зависит от сборки)
    private const val BASE_URL_DEBUG = "http://10.0.2.2"
    private const val BASE_URL_RELEASE = "https://api.volunteer-plus.ru"

    private val BASE_URL = if (BuildConfig.DEBUG) BASE_URL_DEBUG else BASE_URL_RELEASE

    // Порты для debug (в release порты не используются, т.к. маршрутизация через gateway)
    private const val PORT_FEED = 8001
    private const val PORT_SUBSCRIPTION = 8002
    private const val PORT_EVENT = 8003
    private const val PORT_ORGANIZATION = 8004
    private const val PORT_ANALYTICS = 8005
    private const val PORT_NOTIFICATION = 8006
    private const val PORT_CHAT = 8007
    private const val PORT_USER = 8008

    // URLs микросервисов
    val FEED_SERVICE_URL: String
        get() = if (BuildConfig.DEBUG) "$BASE_URL:$PORT_FEED/" else "$BASE_URL/feed-service/"

    val SUBSCRIPTION_SERVICE_URL: String
        get() = if (BuildConfig.DEBUG) "$BASE_URL:$PORT_SUBSCRIPTION/" else "$BASE_URL/subscription-service/"

    val EVENT_SERVICE_URL: String
        get() = if (BuildConfig.DEBUG) "$BASE_URL:$PORT_EVENT/" else "$BASE_URL/event-service/"

    val ORGANIZATION_SERVICE_URL: String
        get() = if (BuildConfig.DEBUG) "$BASE_URL:$PORT_ORGANIZATION/" else "$BASE_URL/organization-service/"

    val ANALYTICS_SERVICE_URL: String
        get() = if (BuildConfig.DEBUG) "$BASE_URL:$PORT_ANALYTICS/" else "$BASE_URL/analytics-service/"

    val NOTIFICATION_SERVICE_URL: String
        get() = if (BuildConfig.DEBUG) "$BASE_URL:$PORT_NOTIFICATION/" else "$BASE_URL/notification-service/"

    val USER_SERVICE_URL: String
        get() = if (BuildConfig.DEBUG) "$BASE_URL:$PORT_USER/" else "$BASE_URL/user-service/"

    val CHAT_SERVICE_URL: String
        get() = if (BuildConfig.DEBUG) "$BASE_URL:$PORT_CHAT/" else "$BASE_URL/chat-service/"

    val CHAT_WS_BASE_URL: String
        get() = if (BuildConfig.DEBUG) "ws://10.0.2.2:$PORT_CHAT/ws/chat/" else "wss://api.volunteer-plus.ru/chat-ws/"

    // Остальные константы без изменений
    const val CONNECT_TIMEOUT = 30L
    const val READ_TIMEOUT = 30L
    const val WRITE_TIMEOUT = 30L
    const val DEFAULT_PAGE_SIZE = 20
    const val INITIAL_PAGE = 1
    const val DEV_FALLBACK_USER_ID = 1L
}