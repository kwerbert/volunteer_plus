package com.example.myapplication.ui.fragments

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.R
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.databinding.DialogEventDetailsBinding
import com.example.myapplication.ui.activities.ChatActivity
import com.example.myapplication.ui.activities.QrCodeActivity
import com.example.myapplication.ui.activities.QrScannerActivity
import com.example.myapplication.ui.viewmodels.EventDetailsViewModel
import com.example.myapplication.util.SessionManager
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import coil.load
import coil.transform.CircleCropTransformation
import javax.inject.Inject

@AndroidEntryPoint
class EventDetailsBottomSheet : BottomSheetDialogFragment() {
    private var _binding: DialogEventDetailsBinding? = null
    private val binding get() = _binding!!
    private var event: EventItem? = null
    private val viewModel: EventDetailsViewModel by viewModels()

    @Inject
    lateinit var sessionManager: SessionManager

    companion object {
        private const val ARG_EVENT = "event_parcelable"
        fun newInstance(event: EventItem): EventDetailsBottomSheet {
            return EventDetailsBottomSheet().apply {
                arguments = Bundle().apply {
                    putParcelable(ARG_EVENT, event)
                }
            }
        }
    }

    private val qrScannerLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            val data = result.data
            val eventId = data?.getIntExtra("event_id", -1) ?: -1
            val qrSecret = data?.getStringExtra("qr_secret")
            if (eventId != -1 && !qrSecret.isNullOrEmpty()) {
                viewModel.checkIn(eventId, qrSecret)
            } else {
                Toast.makeText(requireContext(), "Ошибка сканирования", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = DialogEventDetailsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        event = arguments?.let { args ->
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                args.getParcelable(ARG_EVENT, EventItem::class.java)
            } else {
                @Suppress("DEPRECATION")
                args.getParcelable<EventItem>(ARG_EVENT)
            }
        }

        setupUI()
        setupClickListeners()
        observeViewModel()
        loadSubscriptionStatus()
    }

    private fun loadSubscriptionStatus() {
        event?.let {
            viewModel.loadSubscriptionStatus(it.organization.id.toInt())
        }
    }

    override fun onStart() {
        super.onStart()
        (dialog as? BottomSheetDialog)?.let { dialog ->
            val bottomSheet = dialog.findViewById<View>(com.google.android.material.R.id.design_bottom_sheet)
            bottomSheet?.let { sheet ->
                val behavior = BottomSheetBehavior.from(sheet)
                behavior.peekHeight = resources.displayMetrics.heightPixels * 3 / 4
                behavior.state = BottomSheetBehavior.STATE_EXPANDED
                behavior.isHideable = true
            }
        }
    }

    private fun setupUI() {
        event?.let { event ->
            binding.tvEventTitle.text = event.title
            binding.tvEventDate.text = event.startTime
            binding.tvOrgName.text = event.organization.name

            binding.ivOrgAvatar.load(event.organization.logoUrl) {
                placeholder(R.drawable.ic_profile)
                error(R.drawable.ic_profile)
                transformations(CircleCropTransformation())
            }

            // Показать кнопку QR только для организаторов (роль admin)
            val userRole = sessionManager.userRole
            if (userRole == "admin") {
                binding.btnShowQr.visibility = View.VISIBLE
            } else {
                binding.btnShowQr.visibility = View.GONE
            }
        }
    }

    private fun observeViewModel() {
        lifecycleScope.launch {
            viewModel.registrationResult.collect { result ->
                result?.onSuccess {
                    Toast.makeText(requireContext(), "Успешно зарегистрированы", Toast.LENGTH_SHORT).show()
                    event?.let { event ->
                        val intent = Intent(requireContext(), ChatActivity::class.java)
                        intent.putExtra(ChatActivity.EXTRA_EVENT_ID, event.id.toInt())
                        startActivity(intent)
                        dismiss()
                    }
                }?.onFailure { error ->
                    Toast.makeText(requireContext(), "Ошибка регистрации: ${error.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        lifecycleScope.launch {
            viewModel.subscriptionStatus.collect { status ->
                status?.let {
                    updateSubscriptionButton(it.isSubscribed)
                }
            }
        }

        lifecycleScope.launch {
            viewModel.toggleSubscriptionResult.collect { result ->
                result?.onSuccess {
                    Toast.makeText(requireContext(), "Статус подписки изменён", Toast.LENGTH_SHORT).show()
                }?.onFailure { error ->
                    Toast.makeText(requireContext(), "Ошибка: ${error.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun updateSubscriptionButton(isSubscribed: Boolean) {
        binding.btnOrgSubscribe.text = if (isSubscribed) "Отписаться" else "Подписаться"
        // enabled всегда true, но можно заблокировать на время операции через StateFlow
    }

    private fun setupClickListeners() {

        binding.btnRegister.setOnClickListener {
            event?.let { currentEvent ->
                viewModel.registerForEvent(currentEvent.id.toInt())
            }
        }
        binding.btnOrgSubscribe.setOnClickListener {
            event?.let { currentEvent ->
                viewModel.subscribeToOrganization(currentEvent.organization.id.toInt())
            }
        }
        binding.btnChatOrg.setOnClickListener {
            event?.let { currentEvent ->
                val intent = Intent(requireContext(), ChatActivity::class.java)
                intent.putExtra(ChatActivity.EXTRA_ORG_ID, currentEvent.organization.id.toInt())
                startActivity(intent)
            }
            dismiss()
        }
        binding.btnShowQr.setOnClickListener {
            event?.let { currentEvent ->
                val qrSecret = currentEvent.qrSecret
                if (qrSecret.isNullOrEmpty()) {
                    Toast.makeText(requireContext(), "QR-код ещё не сгенерирован", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                val intent = Intent(requireContext(), QrCodeActivity::class.java)
                intent.putExtra("event_id", currentEvent.id.toInt())
                intent.putExtra("qr_secret", qrSecret)
                startActivity(intent)
            }
            dismiss()
        }
        binding.btnCheckIn.setOnClickListener {
            val intent = Intent(requireContext(), QrScannerActivity::class.java)
            qrScannerLauncher.launch(intent)
        }
        binding.btnOrgSubscribe.setOnClickListener {
            event?.let { currentEvent ->
                viewModel.toggleOrganizationSubscription(currentEvent.organization.id.toInt())
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}