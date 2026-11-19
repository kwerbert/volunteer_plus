package com.example.myapplication

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.sp
import com.example.myapplication.ui.screens.EventsScreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainAppScreen(
    onLogoutClick: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }

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
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_home), contentDescription = null) },
                    label = { Text("Главная") }, selected = selectedTab == 0, onClick = { selectedTab = 0 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_events), contentDescription = null) },
                    label = { Text("События") }, selected = selectedTab == 1, onClick = { selectedTab = 1 }
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
                0 -> CenterText("Лента (Главная) - в разработке")
                1 -> EventsScreen() // <-- Подключили наш новый экран!
                2 -> CenterText("Профиль (в разработке)")
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
