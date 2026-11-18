package com.example.myapplication.ui.fragments

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.myapplication.R
import com.example.myapplication.databinding.FragmentChatBinding
import com.example.myapplication.ui.activities.ChatActivity
import com.example.myapplication.ui.adapters.ChatListAdapter
import com.example.myapplication.ui.viewmodels.ChatUiEvent
import com.example.myapplication.ui.viewmodels.ChatUiState
import com.example.myapplication.ui.viewmodels.ChatViewModel
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class ChatFragment : Fragment(R.layout.fragment_chat) {

    private val viewModel: ChatViewModel by viewModels()
    private var _binding: FragmentChatBinding? = null
    private val binding get() = _binding!!

    private lateinit var chatAdapter: ChatListAdapter

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        _binding = FragmentChatBinding.bind(view)

        setupRecyclerView()
        observeViewModel()
        setupSwipeRefresh()
    }

    private fun setupRecyclerView() {
        chatAdapter = ChatListAdapter { chat ->
            // Открытие чата
            val intent = Intent(requireContext(), ChatActivity::class.java)
            intent.putExtra(ChatActivity.EXTRA_CHAT_ID, chat.id)
            intent.putExtra(ChatActivity.EXTRA_CHAT_TITLE, chat.title ?: "Чат")
            startActivity(intent)
        }

        binding.rvChats.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = chatAdapter
        }
    }

    private fun setupSwipeRefresh() {
        binding.swipeRefresh.setOnRefreshListener {
            viewModel.loadChats()
        }
    }

    private fun observeViewModel() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                binding.swipeRefresh.isRefreshing = false

                when (state) {
                    is ChatUiState.Loading -> {
                        binding.progressBar.visibility = View.VISIBLE
                        binding.rvChats.visibility = View.GONE
                        binding.tvEmptyState.visibility = View.GONE
                    }
                    is ChatUiState.Success -> {
                        binding.progressBar.visibility = View.GONE
                        binding.rvChats.visibility = View.VISIBLE

                        if (state.chats.isEmpty()) {
                            binding.tvEmptyState.visibility = View.VISIBLE
                            binding.tvEmptyState.text = "У вас пока нет чатов"
                        } else {
                            binding.tvEmptyState.visibility = View.GONE
                            chatAdapter.submitList(state.chats)
                        }
                    }
                    is ChatUiState.Error -> {
                        binding.progressBar.visibility = View.GONE
                        binding.tvEmptyState.visibility = View.VISIBLE
                        binding.tvEmptyState.text = "${state.message}"
                    }
                }
            }
        }

        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.events.collect { event ->
                event?.let {
                    when (it) {
                        is ChatUiEvent.ShowError -> {
                            Toast.makeText(requireContext(), it.message, Toast.LENGTH_SHORT).show()
                        }
                        else -> {}
                    }
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}