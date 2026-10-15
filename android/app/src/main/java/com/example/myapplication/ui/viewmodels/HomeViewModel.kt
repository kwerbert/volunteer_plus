// File: My1Application/app/src/main/java/com/example/myapplication/ui/viewmodels/HomeViewModel.kt
package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.myapplication.data.local.entities.CachedEventEntity
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.models.FeedResponse
import com.example.myapplication.data.models.FeedSection
import com.example.myapplication.data.models.FeedFilterParams
import com.example.myapplication.data.models.OrganizationInfo
import com.example.myapplication.data.repository.FeedRepository
import com.example.myapplication.util.Constants
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class UiState {
    object Loading : UiState()
    data class Success(val feedResponse: FeedResponse) : UiState()
    data class Cached(val feedResponse: FeedResponse) : UiState()
    data class Error(val message: String) : UiState()

    val hasMore: Boolean get() = when (this) {
        is Success -> feedResponse.hasMore
        is Cached -> false
        else -> false
    }
}

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repository: FeedRepository,
    private val sessionManager: SessionManager
) : ViewModel() {
    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private var currentPage = Constants.INITIAL_PAGE
    private var isLoadingMore = false
    private var currentFeed: FeedResponse? = null
    private var isFetchingFromNetwork = false
    private val loadedEventIds = mutableSetOf<Long>()

    private val _currentFilters = MutableStateFlow(FeedFilterParams())
    val currentFilters: StateFlow<FeedFilterParams> = _currentFilters.asStateFlow()

    private val _searchQuery = MutableStateFlow("")

    init {
        loadFeed()
        observeSearchQuery()
    }

    @OptIn(FlowPreview::class)
    private fun observeSearchQuery() {
        viewModelScope.launch {
            _searchQuery
                .debounce(300)
                .distinctUntilChanged()
                .collect { query ->
                    val newFilters = _currentFilters.value.copy(
                        searchQuery = query.ifEmpty { null }
                    )
                    updateFilters(newFilters)
                }
        }
    }

    fun updateFilters(newFilters: FeedFilterParams) {
        _currentFilters.value = newFilters
        loadFeed()
    }

    fun search(query: String) {
        _searchQuery.value = query
    }

    fun applyFilters(filters: FeedFilterParams) {
        updateFilters(filters)
    }

    fun loadFeed() {
        currentPage = Constants.INITIAL_PAGE
        isLoadingMore = false
        currentFeed = null
        loadedEventIds.clear()
        fetchPage(Constants.INITIAL_PAGE, isRefresh = true)
    }

    fun loadMore() {
        if (isLoadingMore || isFetchingFromNetwork) return
        val state = _uiState.value
        if (state !is UiState.Success || !state.feedResponse.hasMore) return
        isLoadingMore = true
        fetchPage(currentPage + 1, isRefresh = false)
    }

    private fun fetchPage(page: Int, isRefresh: Boolean) {
        if (isFetchingFromNetwork && !isRefresh) return

        viewModelScope.launch {
            isFetchingFromNetwork = true
            val userId = sessionManager.getCurrentUserId()
            val filters = _currentFilters.value
            repository.getFeed(
                userId = userId,
                page = page,
                pageSize = Constants.DEFAULT_PAGE_SIZE,
                filterParams = filters
            ).onSuccess { newResponse ->
                val merged = if (isRefresh) {
                    newResponse
                } else {
                    mergeSections(newResponse)
                }
                if (!isRefresh) currentPage = page
                currentFeed = merged
                _uiState.value = UiState.Success(merged)
            }.onFailure { error ->
                isLoadingMore = false
                repository.getCachedFeed()
                    .onSuccess { entities ->
                        val cachedFeed = entities.toFeedResponse()
                        currentFeed = cachedFeed
                        _uiState.value = UiState.Cached(cachedFeed)
                    }
                    .onFailure {
                        _uiState.value = UiState.Error(error.message ?: "Ошибка загрузки")
                    }
            }.also {
                isFetchingFromNetwork = false
                isLoadingMore = false
            }
        }
    }

    private fun mergeSections(new: FeedResponse): FeedResponse {
        val current = currentFeed ?: return new
        val newUniqueSections = new.sections.map { section ->
            section.copy(
                events = section.events.filter { event ->
                    if (event.id in loadedEventIds) false
                    else { loadedEventIds.add(event.id); true }
                }
            )
        }.filter { it.events.isNotEmpty() }

        return current.copy(
            sections = current.sections + newUniqueSections,
            totalEvents = current.totalEvents + newUniqueSections.sumOf { it.events.size },
            hasMore = new.hasMore
        )
    }

    private fun List<CachedEventEntity>.toFeedResponse(): FeedResponse {
        val events = map { e ->
            EventItem(
                id = e.id,
                title = e.title,
                organization = OrganizationInfo(
                    id = e.organizationId,   //исправлено: берём реальный ID
                    name = e.organizationName,
                    logoUrl = null,
                    rating = 0f,
                    verified = false,
                    categoryId = null
                ),
                startTime = e.startTime,
                endTime = e.endTime ?: e.startTime,
                descriptionPreview = e.descriptionPreview,
                locationLat = e.locationLat,
                locationLon = e.locationLon,
                distanceKm = e.distanceKm,
                qrSecret = null
            )
        }
        return FeedResponse(
            userId = sessionManager.getCurrentUserId(),
            generatedAt = System.currentTimeMillis().toString(),
            filtersApplied = emptyMap(),
            sections = listOf(FeedSection("cached", "📦 Оффлайн-кэш", events, "vertical")),
            totalEvents = events.size,
            hasMore = false
        )
    }
}