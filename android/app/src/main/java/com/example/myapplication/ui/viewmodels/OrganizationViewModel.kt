package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject

data class OrganizationItem(
    val id: Long,
    val name: String,
    val description: String,
    val rating: Float,
    val isSubscribed: Boolean
)

@HiltViewModel
class OrganizationViewModel @Inject constructor() : ViewModel() {

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _allOrganizations = MutableStateFlow(
        listOf(
            OrganizationItem(1L, "Эко-Движение", "Помощь природе и городским паркам", 4.9f, true),
            OrganizationItem(2L, "Добрые руки", "Приют для бездомных животных", 4.7f, true),
            OrganizationItem(3L, "Зеленый мир", "Сбор макулатуры и переработка", 4.5f, false),
            OrganizationItem(4L, "Красный Крест", "Донорство и медицинская помощь", 5.0f, false),
            OrganizationItem(5L, "Волонтеры Победы", "Помощь ветеранам и благоустройство памятников", 4.8f, false)
        )
    )

    private val _filteredOrganizations = MutableStateFlow<List<OrganizationItem>>(emptyList())
    val filteredOrganizations: StateFlow<List<OrganizationItem>> = _filteredOrganizations.asStateFlow()

    init {
        filterOrganizations()
    }

    fun onSearchQueryChange(query: String) {
        _searchQuery.value = query
        filterOrganizations()
    }

    fun toggleSubscription(orgId: Long) {
        _allOrganizations.value = _allOrganizations.value.map { org ->
            if (org.id == orgId) org.copy(isSubscribed = !org.isSubscribed) else org
        }
        filterOrganizations()
    }

    private fun filterOrganizations() {
        val query = _searchQuery.value.trim().lowercase()
        _filteredOrganizations.value = if (query.isEmpty()) {
            _allOrganizations.value
        } else {
            _allOrganizations.value.filter { 
                it.name.lowercase().contains(query) || it.description.lowercase().contains(query) 
            }
        }
    }
}
