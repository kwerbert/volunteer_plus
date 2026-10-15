package com.example.myapplication

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NotificationManagerCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.databinding.ActivityMainBinding
import com.example.myapplication.data.repository.FeedRepository
import com.example.myapplication.ui.activities.ChatActivity
import com.example.myapplication.ui.activities.LoginActivity
import com.example.myapplication.ui.fragments.EventDetailsBottomSheet
import com.example.myapplication.ui.fragments.EventsFragment
import com.example.myapplication.ui.fragments.HomeFragment
import com.example.myapplication.ui.fragments.OrganizationsFragment
import com.example.myapplication.ui.fragments.ProfileFragment
import com.example.myapplication.ui.viewmodels.HomeViewModel
import com.example.myapplication.ui.viewmodels.UiState
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : AppCompatActivity() {

    @Inject
    lateinit var sessionManager: SessionManager

    @Inject
    lateinit var feedRepository: FeedRepository   // Для загрузки мероприятия по ID

    private lateinit var binding: ActivityMainBinding
    private val viewModel: HomeViewModel by viewModels()
    private var hasSubscriptions = false
    private var currentFragmentTag: String? = null

    // Регистрация лаунчера для запроса разрешения на уведомления (Android 13+)
    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            Toast.makeText(this, "Уведомления включены", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "Уведомления отключены. Вы не будете получать оповещения.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (!sessionManager.isLoggedIn) {
            redirectToLogin()
            return
        }

        // Проверка валидности access токена
        if (!sessionManager.validateAccessToken()) {
            // Токен истёк или невалиден, пробуем обновить (если есть refresh)
            if (sessionManager.refreshToken != null) {
                // Можно вызвать refresh, но проще перенаправить на логин
                redirectToLogin()
                return
            } else {
                redirectToLogin()
                return
            }
        }

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Загрузка фрагментов
        if (savedInstanceState == null) {
            loadFragment(HomeFragment(), "HOME")
        } else {
            currentFragmentTag = savedInstanceState.getString("CURRENT_FRAGMENT_TAG", "HOME")
        }

        observeViewModel()
        setupNavigation()

        // Запрос разрешения на уведомления для Android 13+
        requestNotificationPermission()

        // Обработка клика по push-уведомлению (если приложение было убито)
        handleIntentExtras(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        // Приложение уже запущено, но пришло новое уведомление
        handleIntentExtras(intent)
        // Очищаем extras, чтобы при повороте экрана не открывалось повторно
        val newIntent = Intent()
        intent.extras?.let { newIntent.putExtras(it) }
        setIntent(newIntent)
    }

    /**
     * Обработка данных из уведомления:
     * - если есть chat_id → открываем ChatActivity
     * - если есть event_id → загружаем мероприятие и показываем BottomSheet
     */
    private fun handleIntentExtras(intent: Intent) {
        val chatId = intent.getIntExtra("chat_id", -1)
        val eventId = intent.getIntExtra("event_id", -1)

        when {
            chatId != -1 -> {
                val chatIntent = Intent(this, ChatActivity::class.java).apply {
                    putExtra(ChatActivity.EXTRA_CHAT_ID, chatId)
                    putExtra(ChatActivity.EXTRA_CHAT_TITLE, "Чат")
                }
                startActivity(chatIntent)
            }
            eventId != -1 -> {
                lifecycleScope.launch {
                    val userId = sessionManager.getCurrentUserId()
                    val event = feedRepository.getEventById(eventId.toLong(), userId)
                    if (event != null) {
                        EventDetailsBottomSheet.newInstance(event).show(
                            supportFragmentManager,
                            "EventDetailsBottomSheet"
                        )
                    } else {
                        Toast.makeText(
                            this@MainActivity,
                            "Не удалось загрузить мероприятие",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }
        }
    }

    /**
     * Запрос разрешения на показ уведомлений для Android 13+
     */
    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // Если уведомления уже отключены системой – запрашиваем разрешение
            if (!NotificationManagerCompat.from(this).areNotificationsEnabled()) {
                notificationPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    /**
     * Перенаправление на экран входа
     */
    private fun redirectToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putString("CURRENT_FRAGMENT_TAG", currentFragmentTag)
    }

    /**
     * Настройка нижней навигации
     */
    private fun setupNavigation() {
        binding.bottomNavigation.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> loadFragment(HomeFragment(), "HOME")
                R.id.nav_events -> loadFragment(EventsFragment(), "EVENTS")
                R.id.nav_organizations -> loadFragment(OrganizationsFragment(), "ORGANIZATIONS")
                R.id.nav_profile -> loadFragment(ProfileFragment(), "PROFILE")
            }
            true
        }
    }

    /**
     * Замена фрагмента в контейнере
     */
    private fun loadFragment(fragment: Fragment, tag: String) {
        if (currentFragmentTag == tag) return
        supportFragmentManager.beginTransaction()
            .replace(R.id.container_main, fragment, tag)
            .commitAllowingStateLoss()
        currentFragmentTag = tag
    }

    /**
     * Наблюдение за состоянием ленты (для отображения офлайн-режима)
     */
    private fun observeViewModel() {
        lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                when (state) {
                    is UiState.Success -> {
                        hasSubscriptions = state.feedResponse.totalEvents > 0
                    }
                    is UiState.Cached -> {
                        hasSubscriptions = state.feedResponse.totalEvents > 0
                        Toast.makeText(this@MainActivity, "Оффлайн режим", Toast.LENGTH_SHORT).show()
                    }
                    else -> {}
                }
            }
        }
    }

    /**
     * Выход из системы
     */
    fun logout() {
        sessionManager.clear()
        redirectToLogin()
    }
}