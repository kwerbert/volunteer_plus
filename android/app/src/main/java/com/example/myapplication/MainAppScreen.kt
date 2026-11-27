package com.example.myapplication

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.myapplication.ui.screens.*

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
                        Icon(Icons.AutoMirrored.Filled.ExitToApp, contentDescription = "Выйти", tint = Color.White)
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_home), contentDescription = null, modifier = Modifier.size(24.dp)) },
                    label = { Text("Главная", fontSize = 10.sp) }, selected = selectedTab == 0, onClick = { selectedTab = 0 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_organizations), contentDescription = null, modifier = Modifier.size(24.dp)) },
                    label = { Text("Организации", fontSize = 10.sp) }, selected = selectedTab == 1, onClick = { selectedTab = 1 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_chat), contentDescription = null, modifier = Modifier.size(24.dp)) },
                    label = { Text("Чаты", fontSize = 10.sp) }, selected = selectedTab == 2, onClick = { selectedTab = 2 }
                )
                NavigationBarItem(
                    icon = { Icon(painterResource(id = R.drawable.ic_profile), contentDescription = null, modifier = Modifier.size(24.dp)) },
                    label = { Text("Профиль", fontSize = 10.sp) }, selected = selectedTab == 3, onClick = { selectedTab = 3 }
                )
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            when (selectedTab) {
                0 -> HomeScreen()
                1 -> OrganizationsScreen()
                2 -> ChatListScreen()
                3 -> ProfileScreen()
            }
        }
    }
}
