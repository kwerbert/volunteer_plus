package com.example.myapplication

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.myapplication.ui.screens.*
import com.example.myapplication.ui.viewmodels.ChatItem
import com.example.myapplication.ui.viewmodels.ChatViewModel
import com.example.myapplication.ui.viewmodels.ProfileViewModel
import com.example.myapplication.ui.viewmodels.UserRole

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainAppScreen(
    onLogoutClick: () -> Unit,
    chatViewModel: ChatViewModel = hiltViewModel(),
    profileViewModel: ProfileViewModel = hiltViewModel()
) {
    val role by profileViewModel.currentRole.collectAsState()
    val isSubScreenOpen by profileViewModel.isOrganizerSubScreenOpen.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) }
    var activeChat by remember { mutableStateOf<ChatItem?>(null) }

    LaunchedEffect(role) {
        selectedTab = 0
    }

    val topBarTitle = when {
        activeChat != null -> activeChat!!.title
        selectedTab == 0 -> if (role == UserRole.ORGANIZER) "Мои события" else "Главная"
        selectedTab == 1 -> if (role == UserRole.ORGANIZER) "Чаты" else "Организации"
        selectedTab == 2 -> if (role == UserRole.ORGANIZER) "Профиль" else "Чаты"
        selectedTab == 3 -> "Профиль"
        else -> "Волонтер+"
    }

    val openChatWithOrg = { orgName: String ->
        val newChat = chatViewModel.createChat(orgName)
        activeChat = newChat
        selectedTab = if (role == UserRole.ORGANIZER) 1 else 2
    }

    Scaffold(
        topBar = {
            if (activeChat != null) {
                TopAppBar(
                    title = { Text(topBarTitle, color = Color.White) },
                    navigationIcon = {
                        IconButton(onClick = { activeChat = null }) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад", tint = Color.White)
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF6200EE))
                )
            } else if (!isSubScreenOpen) {
                TopAppBar(
                    title = { Text(topBarTitle, color = Color.White) },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF6200EE)),
                    actions = {
                        IconButton(onClick = onLogoutClick) {
                            Icon(Icons.AutoMirrored.Filled.ExitToApp, contentDescription = "Выйти", tint = Color.White)
                        }
                    }
                )
            }
        },
        bottomBar = {
            if (activeChat == null && !isSubScreenOpen) {
                NavigationBar {
                    if (role == UserRole.ORGANIZER) {
                        NavigationBarItem(
                            icon = { Icon(painterResource(id = R.drawable.ic_events), contentDescription = null, modifier = Modifier.size(24.dp)) },
                            label = { Text("События", fontSize = 10.sp) }, selected = selectedTab == 0, onClick = { selectedTab = 0 }
                        )
                        NavigationBarItem(
                            icon = { Icon(painterResource(id = R.drawable.ic_chat), contentDescription = null, modifier = Modifier.size(24.dp)) },
                            label = { Text("Чаты", fontSize = 10.sp) }, selected = selectedTab == 1, onClick = { selectedTab = 1 }
                        )
                        NavigationBarItem(
                            icon = { Icon(painterResource(id = R.drawable.ic_profile), contentDescription = null, modifier = Modifier.size(24.dp)) },
                            label = { Text("Профиль", fontSize = 10.sp) }, selected = selectedTab == 2, onClick = { selectedTab = 2 }
                        )
                    } else {
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
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            if (activeChat != null) {
                ChatDetailScreen()
            } else {
                if (role == UserRole.ORGANIZER) {
                    when (selectedTab) {
                        0 -> OrganizerEventsScreen(viewModel = profileViewModel)
                        1 -> ChatListScreen(viewModel = chatViewModel, onChatClick = { activeChat = it })
                        2 -> ProfileScreen(viewModel = profileViewModel)
                    }
                } else {
                    when (selectedTab) {
                        0 -> HomeScreen(onWriteClick = openChatWithOrg)
                        1 -> OrganizationsScreen(onWriteClick = openChatWithOrg)
                        2 -> ChatListScreen(viewModel = chatViewModel, onChatClick = { activeChat = it })
                        3 -> ProfileScreen(viewModel = profileViewModel)
                    }
                }
            }
        }
    }
}
