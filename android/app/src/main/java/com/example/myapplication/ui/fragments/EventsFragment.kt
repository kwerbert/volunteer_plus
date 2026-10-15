package com.example.myapplication.ui.fragments

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.core.view.isVisible
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.myapplication.R
import com.example.myapplication.databinding.FragmentEventsBinding
import com.example.myapplication.data.models.EventItem
import com.example.myapplication.ui.adapters.EventItemAdapter
import com.example.myapplication.ui.viewmodels.EventsViewModel
import com.google.android.material.tabs.TabLayout
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class EventsFragment : Fragment(R.layout.fragment_events) {

    private var _binding: FragmentEventsBinding? = null
    private val binding get() = _binding!!
    private val viewModel: EventsViewModel by viewModels()
    private lateinit var adapter: EventItemAdapter

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        _binding = FragmentEventsBinding.bind(view)
        setupRecyclerView()
        setupTabs()
        observeViewModel()
    }

    private fun setupRecyclerView() {
        adapter = EventItemAdapter { event ->
            // открыть детали как обычно
            EventDetailsBottomSheet.newInstance(event).show(
                childFragmentManager,
                "EventDetailsBottomSheet"
            )
        }
        binding.rvEvents.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = this@EventsFragment.adapter
            setHasFixedSize(true)
        }
    }

    private fun setupTabs() {
        binding.tabEvents.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
            override fun onTabSelected(tab: TabLayout.Tab?) {
                viewModel.selectTab(tab?.position ?: 0)
            }
            override fun onTabUnselected(tab: TabLayout.Tab?) {}
            override fun onTabReselected(tab: TabLayout.Tab?) {}
        })
    }

    private fun observeViewModel() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                binding.progressBar.isVisible = state is EventsViewModel.UiState.Loading
                binding.rvEvents.isVisible = state is EventsViewModel.UiState.Success
                binding.tvEmptyState.isVisible = state is EventsViewModel.UiState.Empty
                binding.tvErrorState.isVisible = state is EventsViewModel.UiState.Error

                when (state) {
                    is EventsViewModel.UiState.Success -> {
                        adapter.submitList(state.events)
                    }
                    is EventsViewModel.UiState.Empty -> {
                        binding.tvEmptyState.text = state.message
                    }
                    is EventsViewModel.UiState.Error -> {
                        binding.tvErrorState.text = state.message
                        Toast.makeText(requireContext(), state.message, Toast.LENGTH_SHORT).show()
                    }
                    else -> {}
                }
            }
        }

        // pull-to-refresh
        binding.swipeRefresh.setOnRefreshListener {
            viewModel.refresh()
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.isRefreshing.collect { refreshing ->
                binding.swipeRefresh.isRefreshing = refreshing
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}