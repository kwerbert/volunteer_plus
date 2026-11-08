package com.example.myapplication

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainAppScreen(onLogoutClick: () -> Unit) {
    var selectedTab by remember { mutableIntStateOf(0) }

    Scaffold(
        bottomBar = {
            NavigationBar {
                // Используем ВАШИ иконки из drawable
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_home), contentDescription = "Главная") },
                    label = { Text("Главная") },
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_chat), contentDescription = "Чат") },
                    label = { Text("Чат") },
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_qr_code), contentDescription = "QR") },
                    label = { Text("QR") },
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_profile), contentDescription = "Профиль") },
                    label = { Text("Профиль") },
                    selected = selectedTab == 3,
                    onClick = { selectedTab = 3 }
                )
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            when (selectedTab) {
                0 -> HomeContent()
                1 -> ChatContent()
                2 -> QrContent()
                3 -> ProfileContent(onLogoutClick)
            }
        }
    }
}

@Composable
fun HomeContent() {
    val events = listOf("Эко-Движение", "Дети-Герои", "Помощь пожилым", "Защита животных")
    Column(modifier = Modifier.fillMaxSize().background(Color(0xFFF5F5F5))) {
        Text("Мои мероприятия", fontSize = 24.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(16.dp))
        LazyColumn(modifier = Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            items(events) { event ->
                Card(modifier = Modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(4.dp)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(event, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Text("Нажмите, чтобы присоединиться", fontSize = 14.sp, color = Color.Gray)
                    }
                }
            }
        }
    }
}

@Composable
fun ChatContent() {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Чат с организатором", fontSize = 20.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(16.dp))
        Box(modifier = Modifier.fillMaxWidth().weight(1f).background(Color(0xFFEEEEEE), RoundedCornerShape(8.dp)))
        OutlinedTextField(value = "", onValueChange = {}, label = { Text("Сообщение...") }, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
    }
}

@Composable
fun QrContent() {
    Column(modifier = Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Text("Ваш QR-код", fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(24.dp))
        Icon(painter = painterResource(id = R.drawable.ic_qr_code), contentDescription = "QR", modifier = Modifier.size(150.dp), tint = Color.Black)
        Spacer(modifier = Modifier.height(16.dp))
        Text("Покажите код организатору", color = Color.Gray)
    }
}

@Composable
fun ProfileContent(onLogoutClick: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Spacer(modifier = Modifier.height(32.dp))
        Icon(painter = painterResource(id = R.drawable.ic_profile), contentDescription = "Профиль", modifier = Modifier.size(100.dp), tint = Color(0xFF6200EE))
        Spacer(modifier = Modifier.height(16.dp))
        Text("Иван Волонтеров", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text("ivan@example.com", color = Color.Gray)
        Spacer(modifier = Modifier.height(32.dp))
        Button(onClick = onLogoutClick, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = Color.Red)) {
            Text("Выйти из аккаунта")
        }
    }
}