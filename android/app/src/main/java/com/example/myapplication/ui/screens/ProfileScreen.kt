package com.example.myapplication.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.ui.viewmodels.ProfileViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    viewModel: ProfileViewModel = hiltViewModel()
) {
    val name by viewModel.userName.collectAsState()
    val email by viewModel.userEmail.collectAsState()
    val hours by viewModel.totalHours.collectAsState()
    val orgs by viewModel.organizationsCount.collectAsState()
    val registeredEvents by viewModel.registeredEvents.collectAsState()
    val pastEvents by viewModel.pastEvents.collectAsState()

    var selectedTab by remember { mutableIntStateOf(0) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // --- Шапка профиля ---
        item {
            Box(
                modifier = Modifier
                    .size(96.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFE0E0E0)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Person, contentDescription = "Аватар", modifier = Modifier.size(64.dp), tint = Color.Gray)
            }
            Spacer(modifier = Modifier.height(16.dp))
            Text(text = name, fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Text(text = email, fontSize = 14.sp, color = Color.Gray)
            Spacer(modifier = Modifier.height(24.dp))
        }

        // --- Статистика ---
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Моя статистика", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(16.dp))
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(text = hours, fontSize = 24.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6200EE))
                            Text(text = "Всего часов", fontSize = 12.sp, color = Color.Gray)
                        }
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(text = orgs.toString(), fontSize = 24.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6200EE))
                            Text(text = "Организаций", fontSize = 12.sp, color = Color.Gray)
                        }
                    }
                }
            }
            Spacer(modifier = Modifier.height(24.dp))
        }

        // --- Заголовок и Табы ---
        item {
            Text(
                text = "Мои мероприятия",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Start
            )
            Spacer(modifier = Modifier.height(8.dp))
            TabRow(
                selectedTabIndex = selectedTab,
                containerColor = Color.White,
                contentColor = Color(0xFF6200EE)
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = { Text("Записан (${registeredEvents.size})") }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = { Text("Прошел (${pastEvents.size})") }
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
        }

        // --- Список мероприятий ---
        val currentList = if (selectedTab == 0) registeredEvents else pastEvents
        
        if (currentList.isEmpty()) {
            item {
                Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                    Text("Здесь пока пусто", color = Color.Gray)
                }
            }
        } else {
            items(currentList) { event ->
                ProfileEventCard(event)
            }
        }

        // --- Настройки ---
        item {
            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = "Настройки",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Start
            )
            Spacer(modifier = Modifier.height(8.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column {
                    SettingsRow(text = "Редактировать профиль")
                    HorizontalDivider()
                    SettingsRow(text = "Мои подписки")
                    HorizontalDivider()
                    SettingsRow(text = "Уведомления")
                }
            }
        }
    }
}

@Composable
fun ProfileEventCard(event: EventItem) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(text = event.title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            Text(text = event.startTime, fontSize = 12.sp, color = Color(0xFF6200EE))
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = event.descriptionPreview ?: "", fontSize = 13.sp, color = Color.Gray, maxLines = 2)
        }
    }
}

@Composable
fun SettingsRow(text: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = text, fontSize = 16.sp)
    }
}
