package com.example.myapplication.ui.activities

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.R
import com.example.myapplication.databinding.ActivityLoginBinding
import com.example.myapplication.ui.viewmodels.LoginUiEvent
import com.example.myapplication.ui.viewmodels.LoginUiState
import com.example.myapplication.ui.viewmodels.LoginViewModel
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

/**
 * Экран входа/регистрации
 * Единый экран для обоих действий с переключением через кнопки
 */
@AndroidEntryPoint
class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private val viewModel: LoginViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupObservers()
        setupClickListeners()
    }

    private fun setupObservers() {
        lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                updateUI(state)
            }
        }

        lifecycleScope.launch {
            viewModel.events.collect { event ->  // event типа LoginUiEvent?
                event?.let { handleEvent(it) }  // Безопасный вызов
            }
        }
    }

    private fun setupClickListeners() {
        // Кнопка Войти
        binding.btnLogin.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString()

            if (validateInput(email, password)) {
                viewModel.login(email, password)
            }
        }

        // Кнопка Зарегистрироваться
        binding.btnRegister.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString()

            if (validateInput(email, password)) {
                viewModel.register(email, password)
            }
        }

        // DEV-режим: быстрый вход
        binding.btnDevLogin.setOnClickListener {
            viewModel.devQuickLogin()
        }

        // Забыли пароль (заглушка)
        binding.tvForgotPassword.setOnClickListener {
            Toast.makeText(
                this,
                "Функция восстановления пароля в разработке",
                Toast.LENGTH_SHORT
            ).show()
        }
    }

    private fun updateUI(state: LoginUiState) {
        // Индикатор загрузки
        binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE

        // Блокировка кнопок во время загрузки
        binding.btnLogin.isEnabled = !state.isLoading
        binding.btnRegister.isEnabled = !state.isLoading
        binding.etEmail.isEnabled = !state.isLoading
        binding.etPassword.isEnabled = !state.isLoading

        // Сообщение об ошибке
        state.error?.let { error ->
            binding.tvError.text = error
            binding.tvError.visibility = View.VISIBLE
        } ?: run {
            binding.tvError.visibility = View.GONE
        }

        // Успешный вход/регистрация обрабатывается через events
    }

    private fun handleEvent(event: LoginUiEvent) {  // event типа LoginUiEvent (не nullable)
        when (event) {
            is LoginUiEvent.LoginSuccess -> {
                Toast.makeText(this, "Вход выполнен", Toast.LENGTH_SHORT).show()
                navigateToMain()
            }
            is LoginUiEvent.RegisterSuccess -> {
                Toast.makeText(this, "Регистрация успешна", Toast.LENGTH_SHORT).show()
                navigateToMain()
            }
            is LoginUiEvent.DevLoginSuccess -> {
                Toast.makeText(this, "⚡ DEV режим активирован", Toast.LENGTH_SHORT).show()
                navigateToMain()
            }
            is LoginUiEvent.ShowError -> {
                Toast.makeText(this, event.message, Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun validateInput(email: String, password: String): Boolean {
        when {
            email.isEmpty() -> {
                binding.tilEmail.error = "Введите email"
                return false
            }
            !android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches() -> {
                binding.tilEmail.error = "Некорректный email"
                return false
            }
            password.isEmpty() -> {
                binding.tilPassword.error = "Введите пароль"
                return false
            }
            password.length < 8 -> {
                binding.tilPassword.error = "Пароль должен содержать минимум 8 символов"
                return false
            }
            else -> {
                binding.tilEmail.error = null
                binding.tilPassword.error = null
                return true
            }
        }
    }

    private fun navigateToMain() {
        val intent = android.content.Intent(this, com.example.myapplication.MainActivity::class.java)
        intent.flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK or
                android.content.Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }

    override fun onDestroy() {
        super.onDestroy()
        // binding уже очищается автоматически при уничтожении Activity
    }
}