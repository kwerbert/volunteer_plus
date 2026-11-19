package com.example.myapplication.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.ui.components.EventDetailsSheet
import com.example.myapplication.ui.viewmodels.EventsViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EventsScreen(
    viewModel: EventsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) }
    var selectedEvent by remember { mutableStateOf<EventItem?>(null) }

    Column(modifier = Modifier.fillMaxSize()) {
        TabRow(
            selectedTabIndex = selectedTab,
            containerColor = Color.White,
            contentColor = Color(0xFF6200EE)
        ) {
            Tab(selected = selectedTab == 0, onClick = { selectedTab = 0; viewModel.selectTab(0) }, text = { Text("Предстоящие") })
            Tab(selected = selectedTab == 1, onClick = { selectedTab = 1; viewModel.selectTab(1) }, text = { Text("Прошедшие") })
        }

        when (val state = uiState) {
            is EventsViewModel.UiState.Loading -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = Color(0xFF6200EE)) }
            }
            is EventsViewModel.UiState.Error -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text("Ошибка: ${state.message}", color = Color.Red) }
            }
            is EventsViewModel.UiState.Empty -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text(state.message, color = Color.Gray) }
            }
            is EventsViewModel.UiState.Success -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(state.events) { event ->
                        EventCard(event = event, onClick = { selectedEvent = event })
                    }
                }
            }
        }
    }

    if (selectedEvent != null) {
        EventDetailsSheet(
            event = selectedEvent!!,
            onDismiss = { selectedEvent = null }
        )
    }
}

@Composable
fun EventCard(event: EventItem, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = event.title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = event.organization.name, fontSize = 14.sp, color = Color(0xFF6200EE))
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = event.descriptionPreview ?: "Описание отсутствует", fontSize = 14.sp, color = Color.Gray, maxLines = 2)
        }
    }
}
