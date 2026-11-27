package com.example.myapplication.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.data.models.OrganizationInfo
import com.example.myapplication.ui.viewmodels.ProfileViewModel

// Обновленная модель участника (добавили флаг, проставлены ли часы)
data class Participant(
    val id: Long,
    val name: String,
    val role: String,
    val phone: String,
    val email: String,
    val status: String,
    val totalHours: Int,
    val isHoursAssigned: Boolean = false // <-- Новое поле
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrganizerEventsScreen(
    viewModel: ProfileViewModel = hiltViewModel()
) {
    val events by viewModel.organizedEvents.collectAsState()
    val orgName by viewModel.myOrganizationName.collectAsState()
    
    var selectedTab by remember { mutableIntStateOf(0) }
    var showParticipantsFor by remember { mutableStateOf<EventItem?>(null) }
    
    var detailsEvent by remember { mutableStateOf<EventItem?>(null) }
    var editEvent by remember { mutableStateOf<EventItem?>(null) }
    var isCreatingEvent by remember { mutableStateOf(false) }

    val participants = remember {
        mutableStateListOf(
            Participant(1, "Анна Смирнова", "Волонтер", "+7 (999) 123-45-67", "anna@example.com", "Подтвержден", 124, false),
            Participant(2, "Петр Иванов", "Фотограф", "+7 (999) 765-43-21", "petr@example.com", "Подтвержден", 87, false),
            Participant(3, "Мария Сидорова", "Волонтер", "+7 (999) 111-22-33", "maria@example.com", "Ожидает", 15, false)
        )
    }

    // ФИЛЬТРАЦИЯ ПО ВКЛАДКАМ
    val currentEvents = events.filter {
        if (selectedTab == 0) !it.isPast else it.isPast
    }

    if (isCreatingEvent || editEvent != null) {
        EditEventScreen(
            event = editEvent,
            orgName = orgName,
            onBackClick = { 
                viewModel.isOrganizerSubScreenOpen.value = false
                isCreatingEvent = false
                editEvent = null 
            },
            onSaveClick = { updatedEvent ->
                if (isCreatingEvent) {
                    viewModel.addEvent(updatedEvent)
                    isCreatingEvent = false
                    viewModel.isOrganizerSubScreenOpen.value = false
                } else {
                    viewModel.updateEvent(updatedEvent)
                    editEvent = null
                    detailsEvent = updatedEvent
                }
            }
        )
    } else if (detailsEvent != null) {
        OrganizerEventDetailsPage(
            event = detailsEvent!!,
            onBackClick = { 
                viewModel.isOrganizerSubScreenOpen.value = false
                detailsEvent = null 
            },
            onEditClick = { 
                viewModel.isOrganizerSubScreenOpen.value = true
                editEvent = detailsEvent 
            }
        )
    } else {
        Box(modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.fillMaxSize()) {
                TabRow(
                    selectedTabIndex = selectedTab,
                    containerColor = Color.White,
                    contentColor = Color(0xFF6200EE)
                ) {
                    Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("Предстоящие") })
                    Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Прошедшие") })
                }

                if (currentEvents.isEmpty()) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(
                            text = if (selectedTab == 0) "У вас пока нет предстоящих мероприятий" else "У вас пока нет прошедших мероприятий", 
                            color = Color.Gray
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(16.dp, bottom = 88.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(currentEvents) { event ->
                            OrganizerEventCard(
                                event = event,
                                confirmedCount = participants.count { it.status == "Подтвержден" },
                                pendingCount = participants.count { it.status == "Ожидает" },
                                onDetailsClick = { 
                                    viewModel.isOrganizerSubScreenOpen.value = true
                                    detailsEvent = event 
                                },
                                onParticipantsClick = { showParticipantsFor = event }
                            )
                        }
                    }
                }
            }

            if (selectedTab == 0) {
                FloatingActionButton(
                    onClick = { 
                        viewModel.isOrganizerSubScreenOpen.value = true
                        isCreatingEvent = true 
                    },
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(16.dp),
                    containerColor = Color(0xFF6200EE)
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Создать мероприятие", tint = Color.White)
                }
            }
        }
    }

    if (showParticipantsFor != null) {
        ParticipantsSheet(
            event = showParticipantsFor!!,
            participants = participants,
            onDismiss = { showParticipantsFor = null }
        )
    }
}

@Composable
fun OrganizerEventCard(
    event: EventItem,
    confirmedCount: Int,
    pendingCount: Int,
    onDetailsClick: () -> Unit,
    onParticipantsClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = event.title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Text(text = event.startTime, fontSize = 14.sp, color = Color(0xFF6200EE))
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = event.descriptionPreview ?: "", fontSize = 14.sp, color = Color.Gray, maxLines = 2)
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = onDetailsClick,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Подробнее")
                }
                Button(
                    onClick = onParticipantsClick,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6200EE))
                ) {
                    Text("Участники ($confirmedCount/${event.requiredVolunteers ?: 0})")
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                // Если мероприятие прошедшее, не показываем "Ожидают"
                if (!event.isPast) {
                    Text(
                        text = "Ожидают: $pendingCount",
                        fontSize = 12.sp,
                        color = Color(0xFFFFA000),
                        fontWeight = FontWeight.Medium
                    )
                } else {
                    Text(
                        text = "Мероприятие завершено",
                        fontSize = 12.sp,
                        color = Color.Gray,
                        fontWeight = FontWeight.Medium
                    )
                }
                Text(
                    text = "Нужно: ${event.requiredVolunteers ?: 0}",
                    fontSize = 12.sp,
                    color = Color.Gray
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrganizerEventDetailsPage(
    event: EventItem,
    onBackClick: () -> Unit,
    onEditClick: () -> Unit
) {
    Column(modifier = Modifier.fillMaxSize().background(Color.White)) {
        TopAppBar(
            title = { Text("Детали мероприятия", color = Color.White) },
            navigationIcon = {
                IconButton(onClick = onBackClick) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад", tint = Color.White)
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF6200EE))
        )

        Column(modifier = Modifier.padding(24.dp).weight(1f).verticalScroll(rememberScrollState())) {
            Text(text = event.title, fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = "📅 ${event.startTime}", fontSize = 16.sp, color = Color(0xFF6200EE), fontWeight = FontWeight.Medium)
            
            Spacer(modifier = Modifier.height(24.dp))
            
            Text("Что нужно делать", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = event.whatToDo ?: "Информация не указана", fontSize = 15.sp, color = Color.DarkGray)
            
            Spacer(modifier = Modifier.height(20.dp))

            Text("Требования к волонтерам", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = event.volunteerRequirements ?: "Особых требований нет", fontSize = 15.sp, color = Color.DarkGray)

            Spacer(modifier = Modifier.height(20.dp))

            Text("Необходимо человек", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = "${event.requiredVolunteers ?: 0} человек", fontSize = 15.sp, color = Color.DarkGray)

            Spacer(modifier = Modifier.height(20.dp))

            Text("Волонтерские часы", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = "${event.hoursReward ?: 0} ч. за участие", fontSize = 15.sp, color = Color(0xFF4CAF50), fontWeight = FontWeight.Bold)

            Spacer(modifier = Modifier.height(20.dp))

            Text("Дополнительная информация", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = event.additionalInfo ?: "Нет дополнительной информации", fontSize = 15.sp, color = Color.DarkGray)

            Spacer(modifier = Modifier.height(20.dp))
            
            Text("Настройки", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Проверка по QR-коду: Включена", fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text("Роли: Волонтер (4 часа), Фотограф (3 часа)", fontSize = 14.sp)
                }
            }
        }

        Button(
            onClick = onEditClick,
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp)
                .height(56.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6200EE))
        ) {
            Text("Редактировать мероприятие", fontSize = 18.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditEventScreen(
    event: EventItem?,
    orgName: String,
    onBackClick: () -> Unit,
    onSaveClick: (EventItem) -> Unit
) {
    var title by remember { mutableStateOf(event?.title ?: "") }
    var startTime by remember { mutableStateOf(event?.startTime ?: "") }
    var whatToDo by remember { mutableStateOf(event?.whatToDo ?: "") }
    var requirements by remember { mutableStateOf(event?.volunteerRequirements ?: "") }
    var volunteersCount by remember { mutableStateOf(event?.requiredVolunteers?.toString() ?: "") }
    var additionalInfo by remember { mutableStateOf(event?.additionalInfo ?: "") }
    var hoursReward by remember { mutableStateOf(event?.hoursReward?.toString() ?: "") }

    val focusRequester = remember { FocusRequester() }
    val keyboardController = LocalSoftwareKeyboardController.current

    LaunchedEffect(Unit) {
        focusRequester.requestFocus()
        keyboardController?.show()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .imePadding()
    ) {
        TopAppBar(
            title = { Text(if (event == null) "Создание мероприятия" else "Редактирование", color = Color.White) },
            navigationIcon = {
                IconButton(onClick = onBackClick) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад", tint = Color.White)
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF6200EE))
        )

        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(24.dp)
        ) {
            OutlinedTextField(
                value = title,
                onValueChange = { title = it },
                label = { Text("Название мероприятия") },
                modifier = Modifier.fillMaxWidth().focusRequester(focusRequester),
                singleLine = true
            )
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = startTime,
                onValueChange = { startTime = it },
                label = { Text("Дата и время (например, 15 мая 2026, 10:00)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = whatToDo,
                onValueChange = { whatToDo = it },
                label = { Text("Что нужно делать") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 3
            )
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = requirements,
                onValueChange = { requirements = it },
                label = { Text("Требования к волонтерам") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 2
            )
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = volunteersCount,
                onValueChange = { volunteersCount = it },
                label = { Text("Необходимо человек") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = hoursReward,
                onValueChange = { hoursReward = it },
                label = { Text("Волонтерские часы (сколько дадут)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = additionalInfo,
                onValueChange = { additionalInfo = it },
                label = { Text("Дополнительная информация") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 3
            )
        }

        Button(
            onClick = {
                val newEvent = event?.copy(
                    title = title,
                    startTime = startTime,
                    whatToDo = whatToDo,
                    volunteerRequirements = requirements,
                    requiredVolunteers = volunteersCount.toIntOrNull() ?: 0,
                    additionalInfo = additionalInfo,
                    hoursReward = hoursReward.toIntOrNull() ?: 0
                ) ?: EventItem(
                    id = System.currentTimeMillis(),
                    title = title,
                    organization = OrganizationInfo(1L, orgName),
                    startTime = startTime,
                    descriptionPreview = "Новое мероприятие",
                    whatToDo = whatToDo,
                    volunteerRequirements = requirements,
                    requiredVolunteers = volunteersCount.toIntOrNull() ?: 0,
                    additionalInfo = additionalInfo,
                    hoursReward = hoursReward.toIntOrNull() ?: 0,
                    isPast = false
                )
                onSaveClick(newEvent)
            },
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp)
                .height(56.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4CAF50))
        ) {
            Text(if (event == null) "Создать мероприятие" else "Сохранить изменения", fontSize = 18.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ParticipantsSheet(
    event: EventItem,
    participants: SnapshotStateList<Participant>,
    onDismiss: () -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var selectedParticipant by remember { mutableStateOf<Participant?>(null) }

    // В прошедших мероприятиях показываем ТОЛЬКО подтвержденных
    val displayParticipants = if (event.isPast) {
        participants.filter { it.status == "Подтвержден" }
    } else {
        participants
    }

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp).padding(bottom = 32.dp)) {
            
            if (selectedParticipant == null) {
                // ЭКРАН СПИСКА
                Text("Участники: ${event.title}", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(8.dp))
                
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Нужно: ${event.requiredVolunteers ?: 0}", fontSize = 14.sp, color = Color.Gray, fontWeight = FontWeight.Medium)
                    Text("Подтверждено: ${displayParticipants.size}", fontSize = 14.sp, color = Color(0xFF4CAF50), fontWeight = FontWeight.Bold)
                    
                    // Если предстоящее - показываем ожидающих
                    if (!event.isPast) {
                        Text("Ожидает: ${participants.count { it.status == "Ожидает" }}", fontSize = 14.sp, color = Color(0xFFFFA000), fontWeight = FontWeight.Bold)
                    }
                }
                
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                // Кнопка "Проставить часы всем" (только для прошедших)
                if (event.isPast) {
                    Button(
                        onClick = {
                            for (i in participants.indices) {
                                if (participants[i].status == "Подтвержден") {
                                    participants[i] = participants[i].copy(isHoursAssigned = true)
                                }
                            }
                        },
                        modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4CAF50))
                    ) {
                        Icon(Icons.Default.Check, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Проставить часы всем участникам", fontWeight = FontWeight.Bold)
                    }
                }

                displayParticipants.forEach { participant ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                            .clickable { selectedParticipant = participant },
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFF9F9F9))
                    ) {
                        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier.size(40.dp).background(Color(0xFFE0E0E0), shape = RoundedCornerShape(20.dp)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.Person, contentDescription = null, tint = Color.Gray)
                            }
                            Spacer(modifier = Modifier.width(16.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(text = participant.name, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                Text(text = "Роль: ${participant.role}", fontSize = 13.sp, color = Color.Gray)
                            }
                            
                            // Для прошедших: кнопка "Проставить" (если не проставлены)
                            if (event.isPast) {
                                Button(
                                    onClick = {
                                        val index = participants.indexOfFirst { it.id == participant.id }
                                        if (index != -1) {
                                            participants[index] = participants[index].copy(isHoursAssigned = true)
                                        }
                                    },
                                    enabled = !participant.isHoursAssigned,
                                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                                    modifier = Modifier.height(36.dp),
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = if (participant.isHoursAssigned) Color.LightGray else Color(0xFF6200EE),
                                        contentColor = if (participant.isHoursAssigned) Color.Gray else Color.White
                                    )
                                ) {
                                    Text(if (participant.isHoursAssigned) "Часы есть" else "Часы", fontSize = 12.sp)
                                }
                            } else {
                                // Для предстоящих: показываем статус
                                Text(
                                    text = participant.status,
                                    fontSize = 12.sp,
                                    color = if (participant.status == "Подтвержден") Color(0xFF4CAF50) else Color(0xFFFFA000),
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                }
            } else {
                // ЭКРАН ДЕТАЛЕЙ УЧАСТНИКА
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = { selectedParticipant = null }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Назад", tint = Color(0xFF6200EE))
                    }
                    Text("Информация об участнике", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6200EE))
                }
                Spacer(modifier = Modifier.height(16.dp))

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(text = selectedParticipant!!.name, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        Text(text = "Роль на мероприятии:", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Text(text = selectedParticipant!!.role, fontSize = 16.sp, color = Color.DarkGray)
                        Spacer(modifier = Modifier.height(12.dp))

                        Text(text = "Телефон:", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Text(text = selectedParticipant!!.phone, fontSize = 16.sp, color = Color.DarkGray)
                        Spacer(modifier = Modifier.height(12.dp))

                        Text(text = "Email:", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Text(text = selectedParticipant!!.email, fontSize = 16.sp, color = Color.DarkGray)
                        Spacer(modifier = Modifier.height(12.dp))

                        Text(text = "Общий стаж (всего часов):", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Text(text = "${selectedParticipant!!.totalHours} ч.", fontSize = 16.sp, color = Color(0xFF4CAF50), fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(12.dp))

                        Text(text = "Статус:", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        Text(
                            text = selectedParticipant!!.status, 
                            fontSize = 16.sp, 
                            color = if (selectedParticipant!!.status == "Подтвержден") Color(0xFF4CAF50) else Color(0xFFFFA000)
                        )

                        // Кнопка подтверждения (если ожидает)
                        if (selectedParticipant!!.status == "Ожидает") {
                            Spacer(modifier = Modifier.height(24.dp))
                            Button(
                                onClick = {
                                    val index = participants.indexOfFirst { it.id == selectedParticipant!!.id }
                                    if (index != -1) {
                                        val updated = participants[index].copy(status = "Подтвержден")
                                        participants[index] = updated
                                        selectedParticipant = updated
                                    }
                                },
                                modifier = Modifier.fillMaxWidth().height(50.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4CAF50))
                            ) {
                                Text("Подтвердить участие", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                            }
                        }

                        // Кнопка проставления часов (если мероприятие прошедшее)
                        if (event.isPast && !selectedParticipant!!.isHoursAssigned) {
                            Spacer(modifier = Modifier.height(24.dp))
                            Button(
                                onClick = {
                                    val index = participants.indexOfFirst { it.id == selectedParticipant!!.id }
                                    if (index != -1) {
                                        val updated = participants[index].copy(isHoursAssigned = true)
                                        participants[index] = updated
                                        selectedParticipant = updated
                                    }
                                },
                                modifier = Modifier.fillMaxWidth().height(50.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6200EE))
                            ) {
                                Text("Проставить часы", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                            }
                        } else if (event.isPast && selectedParticipant!!.isHoursAssigned) {
                            Spacer(modifier = Modifier.height(24.dp))
                            Text(
                                text = "✅ Часы уже проставлены",
                                color = Color(0xFF4CAF50),
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                                modifier = Modifier.fillMaxWidth(),
                                textAlign = androidx.compose.ui.text.style.TextAlign.Center
                            )
                        }
                    }
                }
            }
        }
    }
}
