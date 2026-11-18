package com.example.myapplication.di

import com.example.myapplication.BuildConfig
import com.example.myapplication.data.api.AuthApi
import com.example.myapplication.data.api.FeedApi
import com.example.myapplication.data.api.ProfileApi
import com.example.myapplication.data.api.AnalyticsApi
import com.example.myapplication.data.api.ChatApi
import com.example.myapplication.api.NotificationApiService
import com.example.myapplication.data.api.EventApi
import com.example.myapplication.data.api.SubscriptionApi
import com.example.myapplication.network.AuthInterceptor
import com.example.myapplication.util.Constants
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Qualifier
import javax.inject.Singleton
import com.example.myapplication.data.api.OrganizationApi

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class FeedRetrofit

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class UserRetrofit

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class AnalyticsRetrofit

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class AuthRetrofit

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class ChatRetrofit

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class NotificationRetrofit

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class EventRetrofit

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class SubscriptionRetrofit

    @Provides
    @Singleton
    fun provideOkHttpClient(authInterceptor: AuthInterceptor): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (com.example.myapplication.BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .connectTimeout(Constants.CONNECT_TIMEOUT, TimeUnit.SECONDS)
            .readTimeout(Constants.READ_TIMEOUT, TimeUnit.SECONDS)
            .writeTimeout(Constants.READ_TIMEOUT, TimeUnit.SECONDS)
            .build()
    }

    @AuthRetrofit
    @Provides
    @Singleton
    fun provideAuthRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.USER_SERVICE_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @Provides
    @Singleton
    fun provideAuthApi(@AuthRetrofit retrofit: Retrofit): AuthApi =
        retrofit.create(AuthApi::class.java)

    @Provides
    @Singleton
    fun provideGsonConverterFactory(): GsonConverterFactory =
        GsonConverterFactory.create()

    @FeedRetrofit
    @Provides
    @Singleton
    fun provideFeedRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.FEED_SERVICE_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @UserRetrofit
    @Provides
    @Singleton
    fun provideUserRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.USER_SERVICE_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @AnalyticsRetrofit
    @Provides
    @Singleton
    fun provideAnalyticsRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.ANALYTICS_SERVICE_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @ChatRetrofit
    @Provides
    @Singleton
    fun provideChatRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.CHAT_SERVICE_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @NotificationRetrofit
    @Provides
    @Singleton
    fun provideNotificationRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.NOTIFICATION_API_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @EventRetrofit
    @Provides
    @Singleton
    fun provideEventRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.EVENT_SERVICE_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @SubscriptionRetrofit
    @Provides
    @Singleton
    fun provideSubscriptionRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.SUBSCRIPTION_SERVICE_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @Provides
    @Singleton
    fun provideChatApi(@ChatRetrofit retrofit: Retrofit): ChatApi =
        retrofit.create(ChatApi::class.java)

    @Provides
    @Singleton
    fun provideFeedApi(@FeedRetrofit retrofit: Retrofit): FeedApi =
        retrofit.create(FeedApi::class.java)

    @Provides
    @Singleton
    fun provideProfileApi(@UserRetrofit retrofit: Retrofit): ProfileApi =
        retrofit.create(ProfileApi::class.java)

    @Provides
    @Singleton
    fun provideAnalyticsApi(@AnalyticsRetrofit retrofit: Retrofit): AnalyticsApi =
        retrofit.create(AnalyticsApi::class.java)

    @Provides
    @Singleton
    fun provideNotificationApiService(
        @NotificationRetrofit retrofit: Retrofit
    ): NotificationApiService =
        retrofit.create(NotificationApiService::class.java)

    @Provides
    @Singleton
    fun provideEventApi(@EventRetrofit retrofit: Retrofit): EventApi =
        retrofit.create(EventApi::class.java)

    @Provides
    @Singleton
    fun provideSubscriptionApi(@SubscriptionRetrofit retrofit: Retrofit): SubscriptionApi =
        retrofit.create(SubscriptionApi::class.java)

// добавить в класс NetworkModule новые аннотации и методы:

    @Qualifier
    @Retention(AnnotationRetention.BINARY)
    annotation class OrganizationRetrofit

    @OrganizationRetrofit
    @Provides
    @Singleton
    fun provideOrganizationRetrofit(
        client: OkHttpClient,
        gson: GsonConverterFactory
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(Constants.ORGANIZATION_SERVICE_URL)
            .client(client)
            .addConverterFactory(gson)
            .build()
    }

    @Provides
    @Singleton
    fun provideOrganizationApi(@OrganizationRetrofit retrofit: Retrofit): OrganizationApi =
        retrofit.create(OrganizationApi::class.java)

}