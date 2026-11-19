package com.example.myapplication.ui.activities

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.databinding.ActivityEditProfileBinding
import com.example.myapplication.data.repository.ProfileRepository
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class EditProfileActivity : AppCompatActivity() {

    @Inject
    lateinit var profileRepository: ProfileRepository

    @Inject
    lateinit var sessionManager: SessionManager

    private lateinit var binding: ActivityEditProfileBinding
    private var originalFullName: String? = null
    private var originalPhone: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityEditProfileBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Редактирование профиля"

        originalFullName = intent.getStringExtra("full_name")
        originalPhone = intent.getStringExtra("phone")

        binding.etFullName.setText(originalFullName ?: "")
        binding.etPhone.setText(originalPhone ?: "")

        binding.btnSave.setOnClickListener {
            saveChanges()
        }
    }

    private fun saveChanges() {
        val newFullName = binding.etFullName.text.toString().trim()
        val newPhone = binding.etPhone.text.toString().trim()

        // Проверка: были ли изменения
        if (newFullName == originalFullName && newPhone == originalPhone) {
            Toast.makeText(this, "Нет изменений", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        binding.progressBar.visibility = android.view.View.VISIBLE
        binding.btnSave.isEnabled = false

        lifecycleScope.launch {
            val userId = sessionManager.getCurrentUserId()
            val result = profileRepository.updateProfile(userId, newFullName, newPhone)

            binding.progressBar.visibility = android.view.View.GONE
            binding.btnSave.isEnabled = true

            result.onSuccess { userResponse ->
                Toast.makeText(this@EditProfileActivity, "Профиль обновлён", Toast.LENGTH_SHORT).show()
                setResult(RESULT_OK)
                finish()
            }.onFailure { error ->
                Toast.makeText(
                    this@EditProfileActivity,
                    "Ошибка: ${error.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }
}