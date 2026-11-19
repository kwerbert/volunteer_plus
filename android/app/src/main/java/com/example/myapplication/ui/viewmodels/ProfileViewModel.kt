package com.example.myapplication.ui.viewmodels

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class ProfileViewModel @Inject constructor() : ViewModel() {
    // В реальном приложении здесь будет загрузка с сервера
    val userName = MutableStateFlow("Иван Волонтеров")
    val userEmail = MutableStateFlow("ivan@example.com")
    val totalHours = MutableStateFlow("124 часа")
    val organizationsCount = MutableStateFlow(3)
}
