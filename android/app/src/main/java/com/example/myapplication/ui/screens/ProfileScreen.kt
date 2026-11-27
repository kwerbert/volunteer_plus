package com.example.myapplication.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Star
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
import com.example.myapplication.ui.components.EventDetailsSheet
import com.example.myapplication.ui.components.OrganizationDetailsSheet
import com.example.myapplication.ui.viewmodels.OrganizationItem
import com.example.myapplication.ui.viewmodels.ProfileViewModel
import com.example.myapplication.ui.viewmodels.UserRole

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
    val mySubscriptions by viewModel.mySubscriptions.collectAsState()
    val role by viewModel.currentRole.collectAsState()

    var selectedTab by remember { mutableIntStateOf(0) }
    var selectedEvent by remember { mutableStateOf<EventItem?>(null) }
    var showSubscriptionsSheet by remember { mutableStateOf(false) }
    var selectedSubscription by remember { mutableStateOf<OrganizationItem?>(null) }
    
    var showOrganizerSheet by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // --- Шапка профиля ---
        item {
            Box(
                modifier = Modifier.size(96.dp).clip(CircleShape).background(Color(0xFFE0E0E0)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Person, contentDescription = "Аватар", modifier = Modifier.size(64.dp), tint = Color.Gray)
            }
            Spacer(modifier = Modifier.height(16.dp))
            Text(text = name, fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Text(text = email, fontSize = 14.sp, color = Color.Gray)
            
            // Бейдж роли
            if (role == UserRole.ORGANIZER) {
                Surface(
                    color = Color(0xFF6200EE),
                    shape = CircleShape,
                    modifier = Modifier.padding(top = 8.dp)
                ) {
                    Text(
                        text = "Организатор",
                        color = Color.White,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(24.dp))
        }

        // --- Кнопка стать организатором (если волонтер) ---
        if (role == UserRole.VOLUNTEER) {
            item {
                Button(
                    onClick = { showOrganizerSheet = true },
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4CAF50))
                ) {
                    Icon(Icons.Default.Star, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Стать организатором")
                }
            }
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

        // --- Заголовок и Табы мероприятий ---
        item {
            Text(
                text = "Мои мероприятия", fontSize = 18.sp, fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Start
            )
            Spacer(modifier = Modifier.height(8.dp))
            TabRow(selectedTabIndex = selectedTab, containerColor = Color.White, contentColor = Color(0xFF6200EE)) {
                Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("Записан (${registeredEvents.size})") })
                Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Прошел (${pastEvents.size})") })
            }
            Spacer(modifier = Modifier.height(8.dp))
        }

        val currentList = if (selectedTab == 0) registeredEvents else pastEvents
        
        if (currentList.isEmpty()) {
            item {
                Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                    Text("Здесь пока пусто", color = Color.Gray)
                }
            }
        } else {
            items(currentList) { event ->
                ProfileEventCard(event = event, onClick = { selectedEvent = event })
            }
        }

        // --- Настройки ---
        item {
            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = "Настройки", fontSize = 18.sp, fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Start
            )
            Spacer(modifier = Modifier.height(8.dp))
            Card(modifier = Modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)) {
                Column {
                    SettingsRow(text = "Редактировать профиль", onClick = {})
                    HorizontalDivider()
                    SettingsRow(text = "Мои подписки", onClick = { showSubscriptionsSheet = true })
                    HorizontalDivider()
                    SettingsRow(text = "Уведомления", onClick = {})
                }
            }
        }
    }

    if (selectedEvent != null) {
        val actionText = if (selectedTab == 0) "Отказаться" else null
        EventDetailsSheet(
            event = selectedEvent!!, 
            onDismiss = { selectedEvent = null },
            onWriteClick = { /* Пока пусто */ },
            actionButtonText = actionText,
            onActionClick = { /* Логика отмены */ }
        )
    }

    if (showSubscriptionsSheet) {
        MySubscriptionsSheet(
            subscriptions = mySubscriptions,
            onDismiss = { showSubscriptionsSheet = false },
            onOrgClick = { org ->
                showSubscriptionsSheet = false
                selectedSubscription = org
            }
        )
    }

    if (selectedSubscription != null) {
        OrganizationDetailsSheet(
            org = selectedSubscription!!,
            onDismiss = { selectedSubscription = null },
            onSubscribeClick = {
                viewModel.unsubscribe(selectedSubscription!!.id)
                selectedSubscription = null
            },
            onWriteClick = { selectedSubscription = null }
        )
    }
    
    // Шторка заявки на организатора
    if (showOrganizerSheet) {
        OrganizerApplicationSheet(
            onDismiss = { showOrganizerSheet = false },
            onSubmit = {
                viewModel.becomeOrganizer()
                showOrganizerSheet = false
            }
        )
    }
}

@Composable
fun ProfileEventCard(event: EventItem, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).clickable { onClick() },
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
fun SettingsRow(text: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable { onClick() }.padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = text, fontSize = 16.sp)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MySubscriptionsSheet(
    subscriptions: List<OrganizationItem>,
    onDismiss: () -> Unit,
    onOrgClick: (OrganizationItem) -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp).padding(bottom = 32.dp)) {
            Text("Мои подписки", fontSize = 22.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(16.dp))
            if (subscriptions.isEmpty()) {
                Text("Вы пока ни на кого не подписаны", color = Color.Gray)
            } else {
                subscriptions.forEach { org ->
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).clickable { onOrgClick(org) },
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFF9F9F9))
                    ) {
                        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier.size(40.dp).clip(CircleShape).background(Color(0xFF6200EE)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(org.name.take(1), color = Color.White, fontWeight = FontWeight.Bold)
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(org.name, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Star, contentDescription = null, tint = Color(0xFFFFC107), modifier = Modifier.size(12.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(org.rating.toString(), fontSize = 12.sp, color = Color.Gray)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrganizerApplicationSheet(
    onDismiss: () -> Unit,
    onSubmit: () -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(modifier = Modifier.fillMaxWidth().padding(24.dp).padding(bottom = 16.dp)) {
            Text("Стать организатором", fontSize = 22.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                "Чтобы создавать свои мероприятия и управлять волонтерами, вам нужно подать заявку. Администратор платформы рассмотрит её в ближайшее время.",
                fontSize = 15.sp,
                color = Color.DarkGray
            )
            Spacer(modifier = Modifier.height(24.dp))
            Button(
                onClick = onSubmit,
                modifier = Modifier.fillMaxWidth().height(50.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4CAF50))
            ) {
                Text("Подать заявку (имитация)")
            }
        }
    }
}
