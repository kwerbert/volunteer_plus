package com.example.myapplication.ui.fragments

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.core.view.isVisible
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.myapplication.R
import com.example.myapplication.databinding.FragmentOrganizationsBinding
import com.example.myapplication.ui.activities.ChatActivity
import com.example.myapplication.ui.adapters.OrganizationAdapter
import com.example.myapplication.ui.viewmodels.OrganizationsViewModel
import com.google.android.material.tabs.TabLayout
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class OrganizationsFragment : Fragment(R.layout.fragment_organizations) {

    private var _binding: FragmentOrganizationsBinding? = null
    private val binding get() = _binding!!
    private val viewModel: OrganizationsViewModel by viewModels()
    private lateinit var adapter: OrganizationAdapter

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        _binding = FragmentOrganizationsBinding.bind(view)
        setupRecyclerView()
        setupTabs()
        observeViewModel()
    }

    private fun setupRecyclerView() {
        adapter = OrganizationAdapter(
            onChatClick = { org ->
                val intent = Intent(requireContext(), ChatActivity::class.java)
                intent.putExtra(ChatActivity.EXTRA_ORG_ID, org.id)
                startActivity(intent)
            },
            onSubscribeClick = { org ->
                viewModel.toggleSubscription(org.id)
            }
        )
        binding.rvOrganizations.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = this@OrganizationsFragment.adapter
            setHasFixedSize(true)
        }
    }

    private fun setupTabs() {
        binding.tabLayout.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
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
                binding.progressBar.isVisible = state is OrganizationsViewModel.UiState.Loading
                binding.rvOrganizations.isVisible = state is OrganizationsViewModel.UiState.Success
                binding.tvEmptyState.isVisible = state is OrganizationsViewModel.UiState.Empty
                binding.tvErrorState.isVisible = state is OrganizationsViewModel.UiState.Error

                when (state) {
                    is OrganizationsViewModel.UiState.Success -> {
                        adapter.submitList(state.organizations)
                    }
                    is OrganizationsViewModel.UiState.Empty -> {
                        binding.tvEmptyState.text = state.message
                    }
                    is OrganizationsViewModel.UiState.Error -> {
                        binding.tvErrorState.text = state.message
                        Toast.makeText(requireContext(), state.message, Toast.LENGTH_SHORT).show()
                    }
                    else -> {}
                }
            }
        }

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