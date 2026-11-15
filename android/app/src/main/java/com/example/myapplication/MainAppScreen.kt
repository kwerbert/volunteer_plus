package com.example.myapplication

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.models.OrganizationInfo

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainAppScreen(onLogoutClick: () -> Unit) {
    var selectedTab by remember { mutableIntStateOf(0) }

    // Ваши реальные данные для демонстрации
    val fakeEvents = listOf(
        EventItem(1, "Уборка парка", OrganizationInfo(1, "Эко-Движение", null, 4.9f, true), "15 мая", descriptionPreview = "Поможем природе"),
        EventItem(2, "Приют для животных", OrganizationInfo(2, "Добрые руки", null, 4.8f, true), "18 мая", descriptionPreview = "Погуляем с собаками")
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Волонтер+", color = Color.White) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF6200EE)),
                actions = {
                    IconButton(onClick = onLogoutClick) {
                        Icon(Icons.Default.ExitToApp, contentDescription = "Выйти", tint = Color.White)
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar {
                // Используем ВАШИ иконки из drawable!
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_home), contentDescription = null) },
                    label = { Text("Главная") }, selected = selectedTab == 0, onClick = { selectedTab = 0 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_chat), contentDescription = null) },
                    label = { Text("Чат") }, selected = selectedTab == 1, onClick = { selectedTab = 1 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_profile), contentDescription = null) },
                    label = { Text("Профиль") }, selected = selectedTab == 2, onClick = { selectedTab = 2 }
                )
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            when (selectedTab) {
                0 -> HomeFeed(fakeEvents)
                1 -> CenterText("Чат (в разработке)")
                2 -> CenterText("Профиль (в разработке)")
            }
        }
    }
}

@Composable
fun HomeFeed(events: List<EventItem>) {
    Column(modifier = Modifier.fillMaxSize().background(Color(0xFFF5F5F5))) {
        Text("Мероприятия", fontSize = 24.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(16.dp))
        LazyColumn(modifier = Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            items(events) { event ->
                Card(modifier = Modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(event.title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(event.organization.name, fontSize = 14.sp, color = Color(0xFF6200EE))
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(event.descriptionPreview ?: "Описание отсутствует", fontSize = 14.sp, color = Color.Gray)
                    }
                }
            }
        }
    }
}

@Composable
fun CenterText(text: String) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text(text, fontSize = 20.sp, color = Color.Gray)
    }
}