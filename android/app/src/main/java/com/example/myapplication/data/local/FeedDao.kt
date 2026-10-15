package com.example.myapplication.data.local

import androidx.room.*
import com.example.myapplication.data.local.entities.CachedEventEntity

@Dao
interface FeedDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertEvents(events: List<CachedEventEntity>)

    @Query("SELECT * FROM cached_events ORDER BY cachedAt DESC")
    suspend fun getAllEvents(): List<CachedEventEntity>

    @Query("DELETE FROM cached_events")
    suspend fun deleteAllEvents()
}