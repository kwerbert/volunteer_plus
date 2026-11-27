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
import com.example.myapplication.ui.viewmodels.HomeViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onWriteClick: (String) -> Unit, // <-- Добавили параметр
    viewModel: HomeViewModel = hiltViewModel()
) {
    val events by viewModel.events.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    var selectedEvent by remember { mutableStateOf<EventItem?>(null) }

    LaunchedEffect(Unit) {
        viewModel.loadFeed(1L)
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            text = "Рекомендации для вас",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 16.dp)
        )

        if (isLoading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Color(0xFF6200EE))
            }
        } else if (error != null) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Ошибка: $error", color = Color.Red)
            }
        } else if (events.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Пока нет рекомендаций", color = Color.Gray)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(events) { event ->
                    HomeEventCard(event = event, onClick = { selectedEvent = event })
                }
            }
        }
    }

    if (selectedEvent != null) {
        EventDetailsSheet(
            event = selectedEvent!!,
            onDismiss = { selectedEvent = null },
            onWriteClick = { orgName ->
                selectedEvent = null // Закрываем карточку
                onWriteClick(orgName) // Переходим в чат
            }
        )
    }
}

@Composable
fun HomeEventCard(event: EventItem, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
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
