package com.example.myapplication.ui.activities

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.databinding.ActivityChatBinding
import com.example.myapplication.ui.adapters.ChatListAdapter
import com.example.myapplication.ui.adapters.MessageListAdapter
import com.example.myapplication.ui.viewmodels.ChatUiEvent
import com.example.myapplication.ui.viewmodels.ChatUiState
import com.example.myapplication.ui.viewmodels.ChatViewModel
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class ChatActivity : AppCompatActivity() {
    companion object {
        const val EXTRA_CHAT_ID = "chat_id"
        const val EXTRA_CHAT_TITLE = "chat_title"
        const val EXTRA_ORG_ID = "org_id"
        const val EXTRA_EVENT_ID = "event_id"
        const val EXTRA_CHAT_TYPE = "chat_type"
        const val EXTRA_SHOW_ORGANIZER_CHATS = "show_organizer_chats"
    }

    private var _binding: ActivityChatBinding? = null
    private val binding get() = _binding!!

    private enum class UIMode { LIST, CHAT }

    private val viewModel: ChatViewModel by viewModels()
    private lateinit var messageAdapter: MessageListAdapter
    private lateinit var chatListAdapter: ChatListAdapter
    private var chatId: Int = -1
    private var currentMode: UIMode = UIMode.CHAT

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        _binding = ActivityChatBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupToolbar("Чаты")
        initAdapters()
        setupRecyclerView()
        setupPagination()

        val showOrganizerChats = intent.getBooleanExtra(EXTRA_SHOW_ORGANIZER_CHATS, false)
        val orgId = intent.getIntExtra(EXTRA_ORG_ID, -1)
        val eventId = intent.getIntExtra(EXTRA_EVENT_ID, -1)
        val explicitChatId = intent.getIntExtra(EXTRA_CHAT_ID, -1)
        val chatTitle = intent.getStringExtra(EXTRA_CHAT_TITLE) ?: "Чат"

        when {
            showOrganizerChats -> {
                switchToMode(UIMode.LIST)
                viewModel.loadChats()
            }
            orgId != -1 -> {
                createOrganizerChat(orgId)
            }
            eventId != -1 -> {
                viewModel.createEventChat(eventId)
                switchToMode(UIMode.CHAT)
            }
            explicitChatId != -1 -> {
                chatId = explicitChatId
                setupToolbar(chatTitle)
                switchToMode(UIMode.CHAT)
                viewModel.selectChat(chatId)
            }
            else -> {
                Toast.makeText(this, "Некорректный запрос на открытие чата", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
        observeViewModel()
        setupSendButton()
    }

    private fun initAdapters() {
        messageAdapter = MessageListAdapter()
        chatListAdapter = ChatListAdapter { chat ->
            chatId = chat.id
            viewModel.selectChat(chatId)
            setupToolbar(chat.title ?: "Чат с организатором")
            switchToMode(UIMode.CHAT)
        }
    }

    private fun setupRecyclerView() {
        binding.rvMessages.layoutManager = LinearLayoutManager(this).apply {
            stackFromEnd = true
        }
        binding.rvMessages.adapter = messageAdapter
    }

    private fun setupPagination() {
        binding.rvMessages.addOnScrollListener(object : RecyclerView.OnScrollListener() {
            override fun onScrolled(recyclerView: RecyclerView, dx: Int, dy: Int) {
                val layoutManager = recyclerView.layoutManager as LinearLayoutManager
                val firstVisiblePosition = layoutManager.findFirstVisibleItemPosition()
                // При скролле вверх и приближении к началу (1-й или 2-й элемент)
                if (firstVisiblePosition <= 1 && dy < 0) {
                    viewModel.loadMoreMessages()
                }
            }
        })
    }

    private fun switchToMode(mode: UIMode) {
        currentMode = mode
        when (mode) {
            UIMode.LIST -> {
                binding.rvMessages.layoutManager = LinearLayoutManager(this)
                binding.rvMessages.adapter = chatListAdapter
                binding.etMessage.visibility = View.GONE
                binding.btnSend.visibility = View.GONE
                binding.tvEmptyListHint?.visibility = View.VISIBLE
            }
            UIMode.CHAT -> {
                binding.rvMessages.layoutManager = LinearLayoutManager(this).apply { stackFromEnd = true }
                binding.rvMessages.adapter = messageAdapter
                binding.etMessage.visibility = View.VISIBLE
                binding.btnSend.visibility = View.VISIBLE
                binding.tvEmptyListHint?.visibility = View.GONE
            }
        }
    }

    private fun createOrganizerChat(orgId: Int) {
        switchToMode(UIMode.LIST)
        viewModel.loadChats()
        viewModel.createOrganizerChat(orgId)
    }

    private fun setupToolbar(title: String) {
        setSupportActionBar(binding.toolbar)
        supportActionBar?.apply {
            setDisplayHomeAsUpEnabled(true)
            setDisplayShowHomeEnabled(true)
            this.title = title
        }
        binding.toolbar.setNavigationOnClickListener {
            finish()
        }
    }

    private fun setupSendButton() {
        binding.btnSend.setOnClickListener {
            val content = binding.etMessage.text.toString().trim()
            if (content.isNotEmpty()) {
                viewModel.sendMessage(content)
                binding.etMessage.text?.clear()
            }
        }
    }

    private fun observeViewModel() {
        lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                when (state) {
                    is ChatUiState.Loading -> {
                        binding.progressBar.visibility = View.VISIBLE
                    }
                    is ChatUiState.Success -> {
                        binding.progressBar.visibility = View.GONE
                        when (currentMode) {
                            UIMode.LIST -> {
                                chatListAdapter.submitList(state.chats)
                                if (state.chats.isEmpty()) {
                                    binding.tvEmptyListHint?.visibility = View.VISIBLE
                                    binding.tvEmptyListHint?.text = "У вас пока нет активных чатов"
                                }
                            }
                            UIMode.CHAT -> {
                                messageAdapter.submitList(state.messages)
                                if (state.messages.isNotEmpty()) {
                                    binding.rvMessages.scrollToPosition(state.messages.size - 1)
                                }
                            }
                        }
                    }
                    is ChatUiState.Error -> {
                        binding.progressBar.visibility = View.GONE
                        Toast.makeText(this@ChatActivity, state.message, Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }

        lifecycleScope.launch {
            viewModel.events.collect { event ->
                event?.let {
                    when (it) {
                        is ChatUiEvent.MessageSent -> {
                            binding.rvMessages.post {
                                binding.rvMessages.scrollToPosition(messageAdapter.itemCount - 1)
                            }
                        }
                        is ChatUiEvent.ChatCreated -> {
                            switchToMode(UIMode.LIST)
                            viewModel.loadChats()
                        }
                        is ChatUiEvent.OrganizerChatCreated -> {
                            setupToolbar("Чат с организатором")
                            setupRecyclerView()
                            setupSendButton()
                            viewModel.selectChat(it.chatId)
                            switchToMode(UIMode.CHAT)
                        }
                        is ChatUiEvent.ShowError -> {
                            Toast.makeText(this@ChatActivity, it.message, Toast.LENGTH_SHORT).show()
                        }
                        else -> {}
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (chatId != -1 && currentMode == UIMode.CHAT) {
            viewModel.markChatAsRead(chatId)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        _binding = null
    }
}