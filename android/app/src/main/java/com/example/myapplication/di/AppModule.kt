package com.example.myapplication.di

import android.content.Context
import com.example.myapplication.data.api.AuthApi
import com.example.myapplication.data.api.FeedApi
import com.example.myapplication.data.api.ProfileApi
import com.example.myapplication.data.api.AnalyticsApi
import com.example.myapplication.data.api.ChatApi
import com.example.myapplication.data.api.EventApi
import com.example.myapplication.data.api.SubscriptionApi
import com.example.myapplication.data.local.AppDatabase
import com.example.myapplication.data.local.FeedDao
import com.example.myapplication.data.repository.AuthRepository
import com.example.myapplication.data.repository.FeedRepository
import com.example.myapplication.data.repository.ProfileRepository
import com.example.myapplication.data.repository.ChatRepository
import com.example.myapplication.data.repository.EventRepository
import com.example.myapplication.data.repository.SubscriptionRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import com.example.myapplication.data.api.OrganizationApi
import com.example.myapplication.data.repository.OrganizationRepository

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideAppDatabase(@ApplicationContext context: Context): AppDatabase =
        AppDatabase.getDatabase(context)

    @Provides
    @Singleton
    fun provideFeedDao(database: AppDatabase): FeedDao =
        database.feedDao()

    @Provides
    @Singleton
    fun provideFeedRepository(api: FeedApi, dao: FeedDao): FeedRepository =
        FeedRepository(api, dao)

    @Provides
    @Singleton
    fun provideProfileRepository(
        profileApi: ProfileApi,
        analyticsApi: AnalyticsApi
    ): ProfileRepository =
        ProfileRepository(profileApi, analyticsApi)

    @Provides
    @Singleton
    fun provideAuthRepository(authApi: AuthApi): AuthRepository =
        AuthRepository(authApi)

    @Provides
    @Singleton
    fun provideChatRepository(chatApi: ChatApi): ChatRepository =
        ChatRepository(chatApi)

    @Provides
    @Singleton
    fun provideEventRepository(eventApi: EventApi): EventRepository =
        EventRepository(eventApi)

    @Provides
    @Singleton
    fun provideSubscriptionRepository(subscriptionApi: SubscriptionApi): SubscriptionRepository =
        SubscriptionRepository(subscriptionApi)

    @Provides
    @Singleton
    fun provideOrganizationRepository(api: OrganizationApi): OrganizationRepository =
        OrganizationRepository(api)

}