package com.example.myapplication.data.repository

import com.example.myapplication.data.api.AnalyticsApi
import com.example.myapplication.data.api.ProfileApi
import com.example.myapplication.data.models.AnalyticsResponse
import com.example.myapplication.data.models.OrgAnalytics
import com.example.myapplication.data.models.OrgStats
import com.example.myapplication.data.models.ProfileData
import com.example.myapplication.data.models.UpdateProfileRequest
import com.example.myapplication.data.models.UpdateSettingsRequest
import com.example.myapplication.data.models.UserResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.io.IOException
import com.example.myapplication.ui.viewmodels.MonthlyStat
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProfileRepository @Inject constructor(
    private val profileApi: ProfileApi,
    private val analyticsApi: AnalyticsApi
) {
    suspend fun getProfileData(userId: Long): Result<ProfileData> = withContext(Dispatchers.IO) {
        var lastException: Exception? = null
        val maxRetries = 3

        for (attempt in 1..maxRetries) {
            try {
                return@withContext coroutineScope {
                    val userDeferred = async { profileApi.getProfile(userId) }
                    val analyticsDeferred = async {
                        try {
                            analyticsApi.getUserAnalytics(userId)
                        } catch (e: Exception) {
                            null
                        }
                    }

                    val userResponse = userDeferred.await()
                    val analyticsResponse = analyticsDeferred.await()

                    when {
                        !userResponse.isSuccessful || userResponse.body() == null -> {
                            val code = userResponse.code()
                            if (code == 404) {
                                Result.success(createDefaultProfile(userId))
                            } else {
                                Result.failure(Exception("User Service error: $code"))
                            }
                        }
                        else -> {
                            val user = userResponse.body()!!
                            val analyticsData = analyticsResponse?.takeIf { it.isSuccessful }?.body()

                            val profileData = ProfileData(
                                userId = user.id,
                                userName = user.fullName.takeIf { !it.isNullOrBlank() }
                                    ?: user.email?.substringBefore("@") ?: "Пользователь",
                                totalHours = analyticsData?.totalHours?.toInt() ?: 0,
                                avatarUrl = null,
                                organizations = mapOrganizations(analyticsData?.organizations),
                                email = user.email,
                                phone = user.phone,
                                role = user.role
                            )
                            Result.success(profileData)
                        }
                    }
                }
            } catch (e: IOException) {
                lastException = e
                if (attempt < maxRetries) {
                    delay(1000L * (1L shl (attempt - 1)))
                    continue
                }
                break
            } catch (e: Exception) {
                lastException = e
                break
            }
        }
        Result.failure(lastException ?: Exception("Неизвестная ошибка при загрузке профиля"))
    }

    suspend fun updateMainOrganization(userId: Long, organizationId: Long): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val request = UpdateSettingsRequest(mainOrganizationId = organizationId)
            val response = profileApi.updateSettings(userId, request)
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Ошибка сохранения основной организации: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun createDefaultProfile(userId: Long): ProfileData = ProfileData(
        userId = userId,
        userName = "Пользователь",
        totalHours = 0,
        avatarUrl = null,
        organizations = emptyList(),
        email = null,
        phone = null,
        role = "volunteer"
    )

    suspend fun getMonthlyStats(userId: Long): Result<List<MonthlyStat>> = withContext(Dispatchers.IO) {
        try {
            val response = analyticsApi.getMonthlyAnalytics(userId, months = 12)
            if (response.isSuccessful && response.body() != null) {
                val data = response.body()!!
                val stats = data.months.map { monthData ->
                    MonthlyStat(
                        year = monthData.year,
                        month = monthData.month,
                        hours = monthData.hours_worked
                    )
                }
                Result.success(stats)
            } else {
                Result.failure(Exception("Ошибка загрузки статистики: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun mapOrganizations(analyticsOrgs: List<OrgAnalytics>?): List<OrgStats> {
        return analyticsOrgs?.mapNotNull { org ->
            org.organizationId?.let { orgId ->
                OrgStats(
                    organizationId = orgId,
                    name = org.organizationName ?: "Организация",
                    hours = org.hoursWorked?.toInt() ?: 0,
                    eventsCount = org.eventsCompleted ?: 0
                )
            }
        } ?: emptyList()
    }

    suspend fun updateProfile(userId: Long, fullName: String?, phone: String?): Result<UserResponse> =
        withContext(Dispatchers.IO) {
            try {
                val request = UpdateProfileRequest(fullName, phone)
                val response = profileApi.updateProfile(userId, request)
                if (response.isSuccessful && response.body() != null) {
                    Result.success(response.body()!!)
                } else {
                    Result.failure(Exception("Ошибка обновления профиля: ${response.code()}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    suspend fun becomeOrganizer(userId: Long): Result<UserResponse> = withContext(Dispatchers.IO) {
        try {
            val response = profileApi.becomeOrganizer(userId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Ошибка: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}