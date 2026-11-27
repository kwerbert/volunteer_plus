package com.example.myapplication.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
    val mySubscriptions by viewModel.mySubscriptions.collectAsState()
    val role by viewModel.currentRole.collectAsState()
    val myOrgName by viewModel.myOrganizationName.collectAsState()
    val myOrgDesc by viewModel.myOrganizationDesc.collectAsState()

    var showSubscriptionsSheet by remember { mutableStateOf(false) }
    var selectedSubscription by remember { mutableStateOf<OrganizationItem?>(null) }

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
            
            Spacer(modifier = Modifier.height(24.dp))

            // КРАСИВЫЙ ПЕРЕКЛЮЧАТЕЛЬ РОЛИ
            SingleChoiceSegmentedButtonRow(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)
            ) {
                SegmentedButton(
                    selected = role == UserRole.VOLUNTEER,
                    onClick = { viewModel.switchRole(UserRole.VOLUNTEER) },
                    shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2),
                    colors = SegmentedButtonDefaults.colors(
                        activeContainerColor = Color(0xFF6200EE),
                        activeContentColor = Color.White
                    )
                ) {
                    Text("Волонтер")
                }
                SegmentedButton(
                    selected = role == UserRole.ORGANIZER,
                    onClick = { viewModel.switchRole(UserRole.ORGANIZER) },
                    shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2),
                    colors = SegmentedButtonDefaults.colors(
                        activeContainerColor = Color(0xFF6200EE),
                        activeContentColor = Color.White
                    )
                ) {
                    Text("Организатор")
                }
            }
            Spacer(modifier = Modifier.height(24.dp))
        }

        // --- Блок для ОРГАНИЗАТОРА ---
        if (role == UserRole.ORGANIZER) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF3E5F5))
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Моя организация", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6200EE))
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = myOrgName, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        Text(text = myOrgDesc, fontSize = 14.sp, color = Color.DarkGray)
                    }
                }
            }
        } else {
            // --- Статистика для ВОЛОНТЕРА ---
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
        }

        // --- Настройки ---
        item {
            Text(
                text = "Настройки", fontSize = 18.sp, fontWeight = FontWeight.Bold,
                modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Start
            )
            Spacer(modifier = Modifier.height(8.dp))
            Card(modifier = Modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)) {
                Column {
                    SettingsRow(text = "Редактировать профиль", onClick = {})
                    HorizontalDivider()
                    if (role == UserRole.VOLUNTEER) {
                        SettingsRow(text = "Мои подписки", onClick = { showSubscriptionsSheet = true })
                        HorizontalDivider()
                    }
                    SettingsRow(text = "Уведомления", onClick = {})
                }
            }
        }
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
