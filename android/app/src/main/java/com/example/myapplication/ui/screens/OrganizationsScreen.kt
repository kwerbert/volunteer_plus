package com.example.myapplication.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.myapplication.ui.components.OrganizationDetailsSheet
import com.example.myapplication.ui.viewmodels.OrganizationItem
import com.example.myapplication.ui.viewmodels.OrganizationViewModel

@Composable
fun OrganizationsScreen(
    onWriteClick: (String) -> Unit,
    viewModel: OrganizationViewModel = hiltViewModel()
) {
    val searchQuery by viewModel.searchQuery.collectAsState()
    val organizations by viewModel.filteredOrganizations.collectAsState()
    var selectedOrg by remember { mutableStateOf<OrganizationItem?>(null) }

    Column(modifier = Modifier.fillMaxSize().imePadding()) { // imePadding для клавиатуры
        OutlinedTextField(
            value = searchQuery,
            onValueChange = viewModel::onSearchQueryChange,
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            placeholder = { Text("Поиск организаций...") },
            singleLine = true,
            shape = MaterialTheme.shapes.medium
        )

        if (organizations.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Ничего не найдено", color = Color.Gray)
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(organizations, key = { it.id }) { org ->
                    OrganizationCard(
                        org = org,
                        onCardClick = { selectedOrg = org },
                        onSubscribeClick = { viewModel.toggleSubscription(org.id) },
                        onWriteClick = { onWriteClick(org.name) }
                    )
                }
            }
        }
    }

    if (selectedOrg != null) {
        OrganizationDetailsSheet(
            org = selectedOrg!!,
            onDismiss = { selectedOrg = null },
            onSubscribeClick = { 
                viewModel.toggleSubscription(selectedOrg!!.id) 
                selectedOrg = selectedOrg!!.copy(isSubscribed = !selectedOrg!!.isSubscribed)
            },
            onWriteClick = { 
                onWriteClick(selectedOrg!!.name)
                selectedOrg = null
            }
        )
    }
}

@Composable
fun OrganizationCard(
    org: OrganizationItem,
    onCardClick: () -> Unit,
    onSubscribeClick: () -> Unit,
    onWriteClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onCardClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = org.name, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Star, contentDescription = "Рейтинг", tint = Color(0xFFFFC107), modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(text = org.rating.toString(), fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = org.description, fontSize = 14.sp, color = Color.Gray, maxLines = 2)
            Spacer(modifier = Modifier.height(16.dp))

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = onSubscribeClick,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (org.isSubscribed) Color.LightGray else Color(0xFF6200EE),
                        contentColor = if (org.isSubscribed) Color.Black else Color.White
                    )
                ) {
                    Text(if (org.isSubscribed) "Вы подписаны" else "Подписаться")
                }

                OutlinedButton(
                    onClick = onWriteClick,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Написать")
                }
            }
        }
    }
}
