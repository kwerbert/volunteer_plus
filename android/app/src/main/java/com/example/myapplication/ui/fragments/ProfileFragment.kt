package com.example.myapplication.ui.fragments

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.databinding.FragmentProfileBinding
import com.example.myapplication.firebase.MyFirebaseMessagingService
import com.example.myapplication.ui.activities.EditProfileActivity
import com.example.myapplication.ui.activities.LoginActivity
import com.example.myapplication.ui.viewmodels.MonthlyStat
import com.example.myapplication.ui.viewmodels.ProfileUiState
import com.example.myapplication.ui.viewmodels.ProfileViewModel
import com.example.myapplication.util.SessionManager
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject
import android.util.Log
import com.example.myapplication.api.NotificationApiService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@AndroidEntryPoint
class ProfileFragment : Fragment(R.layout.fragment_profile) {

    @Inject
    lateinit var notificationApiService: NotificationApiService

    @Inject
    lateinit var sessionManager: SessionManager

    private val viewModel: ProfileViewModel by viewModels()
    private var _binding: FragmentProfileBinding? = null
    private val binding get() = _binding!!

    private lateinit var monthlyStatsAdapter: MonthlyStatsAdapter

    private val editProfileLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            viewModel.refreshProfileData()
            Toast.makeText(requireContext(), "Профиль обновлён", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        _binding = FragmentProfileBinding.bind(view)

        setupRecyclerView()
        setupToolbar()
        setupSpinner()
        setupSwitches()
        setupLogoutButton()
        setupBecomeOrganizerButton()
        observeViewModel()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    private fun setupRecyclerView() {
        monthlyStatsAdapter = MonthlyStatsAdapter(emptyList())
        binding.rvMonthlyStats.layoutManager = LinearLayoutManager(requireContext())
        binding.rvMonthlyStats.adapter = monthlyStatsAdapter
    }

    private fun setupToolbar() {
        binding.ivEdit.setOnClickListener {
            val currentState = viewModel.uiState.value
            if (currentState is ProfileUiState.Success) {
                val intent = Intent(requireContext(), EditProfileActivity::class.java).apply {
                    putExtra("full_name", currentState.userName)
                    putExtra("phone", currentState.phone)
                }
                editProfileLauncher.launch(intent)
            } else {
                Toast.makeText(
                    requireContext(),
                    "Загрузка данных, попробуйте позже",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
    }

    private fun setupSpinner() {
        binding.spinnerMainOrg.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(
                parent: AdapterView<*>?,
                view: View?,
                position: Int,
                id: Long
            ) {
                if (position <= 0) return
                val selectedName = parent?.getItemAtPosition(position) as? String ?: return
                if (selectedName == viewModel.getSavedOrganizationName()) return
                viewModel.selectMainOrganization(selectedName)
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }

    private fun observeViewModel() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                when (state) {
                    is ProfileUiState.Loading -> {
                        binding.progressBar.visibility = View.VISIBLE
                        binding.tvTotalHours.visibility = View.GONE
                        binding.orgStatsContainer.visibility = View.GONE
                        binding.spinnerMainOrg.visibility = View.GONE
                    }
                    is ProfileUiState.Success -> {
                        binding.progressBar.visibility = View.GONE
                        binding.tvTotalHours.visibility = View.VISIBLE
                        binding.orgStatsContainer.visibility = View.VISIBLE
                        binding.spinnerMainOrg.visibility = View.VISIBLE
                        binding.tvTotalHours.text = getString(R.string.hours_format, state.totalHours)
                        updateOrganizationsList(state.organizations)
                        updateMainOrganizationSpinner(state.organizations)
                        monthlyStatsAdapter.updateStats(state.monthlyStats)

                        if (state.role == "admin") {
                            binding.btnBecomeRepresentative.isEnabled = false
                            binding.btnBecomeRepresentative.text = "Вы организатор"
                            binding.btnBecomeRepresentative.isClickable = false
                        } else {
                            binding.btnBecomeRepresentative.isEnabled = true
                            binding.btnBecomeRepresentative.text = "Стать представителем"
                            binding.btnBecomeRepresentative.isClickable = true
                        }
                    }
                    is ProfileUiState.Error -> {
                        binding.progressBar.visibility = View.GONE
                        Toast.makeText(requireContext(), state.message, Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.errorMessage.collect { error ->
                error?.let {
                    Toast.makeText(requireContext(), it, Toast.LENGTH_SHORT).show()
                    viewModel.clearErrorMessage()
                }
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.becomeOrganizerResult.collect { result ->
                result?.let {
                    if (it.isSuccess) {
                        Toast.makeText(requireContext(), "Поздравляем! Теперь вы организатор", Toast.LENGTH_LONG).show()
                    } else {
                        val error = it.exceptionOrNull()?.message ?: "Ошибка"
                        Toast.makeText(requireContext(), "Ошибка: $error", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
    }

    private fun setupSwitches() {
        binding.switchOwnOrgsOnly.setOnCheckedChangeListener { _, isChecked ->
            viewModel.setShowOnlyOwnOrganizations(isChecked)
        }
    }

    private fun setupLogoutButton() {
        binding.buttonLogout.setOnClickListener {
            confirmLogout()
        }
    }

    private fun confirmLogout() {
        AlertDialog.Builder(requireContext())
            .setTitle("Выход из системы")
            .setMessage("Вы действительно хотите выйти?")
            .setPositiveButton("Выйти") { _, _ -> performLogout() }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun performLogout() {
        val token = sessionManager.accessToken ?: ""
        val deviceToken = sessionManager.fcmToken

        // Сначала очищаем локальную сессию
        sessionManager.clear()

        // Best-effort: сообщаем серверу, чтобы он деактивировал токен.
        // Отдельный scope — чтобы запрос дожил до конца, даже если Activity уже finish()-ится.
        if (!deviceToken.isNullOrBlank() && token.isNotBlank()) {
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val response = notificationApiService.unregisterToken(deviceToken, token)
                    if (!response.isSuccessful) {
                        Log.w("ProfileFragment", "Unregister token failed: HTTP ${response.code()}")
                    }
                } catch (e: Exception) {
                    Log.w("ProfileFragment", "Unregister token failed", e)
                }
            }
        }

        val intent = Intent(requireContext(), LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        requireActivity().finish()
        Toast.makeText(requireContext(), "Вы вышли из системы", Toast.LENGTH_SHORT).show()
    }

    private fun setupBecomeOrganizerButton() {
        binding.btnBecomeRepresentative.setOnClickListener {
            showBecomeOrganizerConfirmDialog()
        }
    }

    private fun showBecomeOrganizerConfirmDialog() {
        AlertDialog.Builder(requireContext())
            .setTitle("Стать представителем")
            .setMessage("Вы уверены, что хотите стать организатором? Это действие необратимо.")
            .setPositiveButton("Да") { _, _ -> viewModel.becomeOrganizer() }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun updateOrganizationsList(organizations: List<com.example.myapplication.data.models.OrgStats>) {
        val container = binding.orgStatsContainer
        container.removeAllViews()

        if (organizations.isEmpty()) {
            val emptyView = TextView(requireContext()).apply {
                text = "Нет данных по организациям"
                setTextColor(resources.getColor(R.color.secondary, null))
                setPadding(0, 8, 0, 8)
            }
            container.addView(emptyView)
        } else {
            for (org in organizations) {
                val orgView = TextView(requireContext()).apply {
                    text = "${org.name}: ${org.hours} часов"
                    textSize = 14f
                    setPadding(0, 4, 0, 4)
                }
                container.addView(orgView)
            }
        }
    }

    private fun updateMainOrganizationSpinner(organizations: List<com.example.myapplication.data.models.OrgStats>) {
        val orgNames = organizations.map { it.name }.toTypedArray()
        val fullList = arrayOf("Выберите основную организацию") + orgNames

        val adapter = ArrayAdapter(
            requireContext(),
            android.R.layout.simple_spinner_item,
            fullList
        )
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.spinnerMainOrg.adapter = adapter

        val savedOrg = viewModel.getSavedOrganizationName()
        if (savedOrg != null) {
            val position = fullList.indexOf(savedOrg)
            if (position > 0) {
                binding.spinnerMainOrg.setSelection(position, false)
            }
        }
    }

    // Внутренний класс адаптера (не inner!)
    private class MonthlyStatsAdapter(private var stats: List<MonthlyStat>) :
        RecyclerView.Adapter<MonthlyStatsAdapter.ViewHolder>() {

        fun updateStats(newStats: List<MonthlyStat>) {
            stats = newStats
            notifyDataSetChanged()
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(android.R.layout.simple_list_item_2, parent, false)
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val item = stats[position]
            holder.text1.text = "${item.month}.${item.year}"
            holder.text2.text = "${item.hours} ч"
        }

        override fun getItemCount() = stats.size

        class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
            val text1: TextView = itemView.findViewById(android.R.id.text1)
            val text2: TextView = itemView.findViewById(android.R.id.text2)
        }
    }
}