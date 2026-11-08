package com.example.myapplication

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.*

class ComposeTestActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            // Переменная для переключения между экранами
            var currentScreen by remember { mutableStateOf("login") }

            if (currentScreen == "login") {
                LoginScreen(onLoginClick = { currentScreen = "home" })
            } else {
                MainAppScreen(onLogoutClick = { currentScreen = "login" })
            }
        }
    }
}