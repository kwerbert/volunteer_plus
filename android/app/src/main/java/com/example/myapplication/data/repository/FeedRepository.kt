package com.example.myapplication.data.repository

import com.example.myapplication.data.api.FeedApi
import com.example.myapplication.data.local.FeedDao
import com.example.myapplication.data.local.entities.CachedEventEntity
import com.example.myapplication.data.models.FeedResponse
import com.example.myapplication.data.models.FeedFilterParams
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.io.IOException
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.models.OrganizationInfo

class FeedRepository(
    private val api: FeedApi,
    private val dao: FeedDao
) {
    suspend fun getFeed(
        userId: Long,
        page: Int = 1,
        pageSize: Int = 20,
        filterParams: FeedFilterParams = FeedFilterParams(),
        retryCount: Int = 3
    ): Result<FeedResponse> = withContext(Dispatchers.IO) {
        var lastException: Exception? = null

        for (attempt in 1..retryCount) {
            try {
                val response = api.getFeed(
                    userId = userId,
                    page = page,
                    pageSize = pageSize,
                    searchQuery = filterParams.searchQuery,
                    locationLat = filterParams.locationLat,
                    locationLon = filterParams.locationLon,
                    radiusKm = filterParams.radiusKm,
                    categoryIds = filterParams.categoryIds?.joinToString(","),
                    showOnlySubscriptions = filterParams.showOnlySubscriptions
                )
                if (response.isSuccessful && response.body() != null) {
                    val feedResponse = response.body()!!

                    dao.deleteAllEvents()
                    val cachedEvents = feedResponse.sections.flatMap { section ->
                        section.events.map { event ->
                            CachedEventEntity(
                                id = event.id,
                                organizationId = event.organization.id,
                                organizationName = event.organization.name,
                                title = event.title,
                                startTime = event.startTime,
                                endTime = event.endTime,
                                descriptionPreview = event.descriptionPreview,
                                locationLat = event.locationLat,
                                locationLon = event.locationLon,
                                cachedAt = System.currentTimeMillis()
                            )
                        }
                    }
                    dao.insertEvents(cachedEvents)

                    return@withContext Result.success(feedResponse)
                } else {
                    return@withContext Result.failure(Exception("Ошибка сервера: ${response.code()}"))
                }
            } catch (e: Exception) {
                lastException = e
                if (e is IOException && attempt < retryCount) {
                    delay(1000L * (1L shl (attempt - 1)))
                    continue
                }
                break
            }
        }

        return@withContext Result.failure(lastException ?: Exception("Неизвестная ошибка"))
    }

    suspend fun getCachedFeed(): Result<List<CachedEventEntity>> = withContext(Dispatchers.IO) {
        try {
            val cached = dao.getAllEvents()
            if (cached.isNotEmpty()) {
                Result.success(cached)
            } else {
                Result.failure(Exception("Кэш пуст"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getEventById(eventId: Long, userId: Long): EventItem? {
        // Сначала кэш
        val cached = dao.getAllEvents()
        val cachedEvent = cached.find { it.id == eventId }
        if (cachedEvent != null) {
            return EventItem(
                id = cachedEvent.id,
                title = cachedEvent.title,
                organization = OrganizationInfo(
                    id = cachedEvent.organizationId,
                    name = cachedEvent.organizationName,
                    logoUrl = null,
                    rating = 0f,
                    verified = false,
                    categoryId = null
                ),
                startTime = cachedEvent.startTime,
                endTime = cachedEvent.endTime ?: cachedEvent.startTime,
                descriptionPreview = cachedEvent.descriptionPreview,
                locationLat = cachedEvent.locationLat,
                locationLon = cachedEvent.locationLon,
                distanceKm = cachedEvent.distanceKm,
                maxParticipants = null,
                registeredCount = null
            )
        }

        // Свежие данные через feed (с реальным userId)
        val result = getFeed(
            userId = userId,
            page = 1,
            pageSize = 100,
            filterParams = FeedFilterParams()
        )
        if (result.isSuccess) {
            val feed = result.getOrNull() ?: return null
            val allEvents = feed.sections.flatMap { it.events }
            return allEvents.find { it.id == eventId }
        }
        return null
    }


    suspend fun clearCache() {
        withContext(Dispatchers.IO) {
            dao.deleteAllEvents()
        }
    }
}