package com.example.myapplication.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.myapplication.data.local.entities.CachedEventEntity
import com.example.myapplication.BuildConfig

@Database(
    entities = [CachedEventEntity::class],
    version = 3,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun feedDao(): FeedDao

    companion object {
        @Volatile private var INSTANCE: AppDatabase? = null

        // Вспомогательная функция для проверки существования колонки
        private fun SupportSQLiteDatabase.columnExists(tableName: String, columnName: String): Boolean {
            val cursor = query("PRAGMA table_info($tableName)")
            while (cursor.moveToNext()) {
                val nameIndex = cursor.getColumnIndex("name")
                if (nameIndex != -1 && cursor.getString(nameIndex) == columnName) {
                    cursor.close()
                    return true
                }
            }
            cursor.close()
            return false
        }

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                if (!database.columnExists("cached_events", "endTime")) {
                    database.execSQL("ALTER TABLE cached_events ADD COLUMN endTime TEXT")
                }
                if (!database.columnExists("cached_events", "locationLat")) {
                    database.execSQL("ALTER TABLE cached_events ADD COLUMN locationLat REAL")
                }
                if (!database.columnExists("cached_events", "locationLon")) {
                    database.execSQL("ALTER TABLE cached_events ADD COLUMN locationLon REAL")
                }
            }
        }

        private val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(database: SupportSQLiteDatabase) {
                if (!database.columnExists("cached_events", "organizationId")) {
                    database.execSQL("ALTER TABLE cached_events ADD COLUMN organizationId INTEGER NOT NULL DEFAULT 0")
                }
                if (!database.columnExists("cached_events", "distanceKm")) {
                    database.execSQL("ALTER TABLE cached_events ADD COLUMN distanceKm REAL")
                }
            }
        }

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "volunteer_plus_db"
                )
                    .addMigrations(MIGRATION_1_2, MIGRATION_2_3)
                    .apply {
                        if (BuildConfig.DEBUG) {
                            fallbackToDestructiveMigration()
                        }
                    }
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}