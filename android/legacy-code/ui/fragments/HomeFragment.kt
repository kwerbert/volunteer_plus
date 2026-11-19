package com.example.myapplication.ui.fragments

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.Toast
import androidx.core.view.isVisible
import androidx.core.view.updatePadding
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.MainActivity
import com.example.myapplication.R
import com.example.myapplication.data.models.FeedFilterParams
import com.example.myapplication.databinding.FragmentHomeBinding
import com.example.myapplication.ui.adapters.FeedSectionAdapter
import com.example.myapplication.ui.viewmodels.HomeViewModel
import com.example.myapplication.ui.viewmodels.UiState
import com.google.android.material.bottomnavigation.BottomNavigationView
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch

@AndroidEntryPoint
class HomeFragment : Fragment(R.layout.fragment_home) {
    private val viewModel: HomeViewModel by viewModels()
    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!
    private lateinit var sectionAdapter: FeedSectionAdapter
    private val sharedPool = RecyclerView.RecycledViewPool()
    private var isLoadingMore = false
    private var lastLoadedPosition = -1

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        _binding = FragmentHomeBinding.bind(view)
        setupRecyclerView()
        observeViewModel()
        setupPullToRefresh()
        setupSearch()
        setupFilterButton()
        setupBottomPadding()
    }

    private fun setupBottomPadding() {
        binding.rvFeedSections.post {
            val bottomNavHeight = (requireActivity() as? MainActivity)?.let { activity ->
                activity.findViewById<BottomNavigationView>(R.id.bottom_navigation)?.height ?: 0
            } ?: 0

            val additionalPadding = (16 * resources.displayMetrics.density).toInt()
            val totalPadding = bottomNavHeight + additionalPadding

            binding.rvFeedSections.updatePadding(bottom = totalPadding)
        }
    }

    private fun setupRecyclerView() {
        sectionAdapter = FeedSectionAdapter(sharedPool) { event ->
            EventDetailsBottomSheet.newInstance(event).show(
                childFragmentManager,
                "EventDetailsBottomSheet"
            )
        }
        binding.rvFeedSections.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = sectionAdapter
            setRecycledViewPool(sharedPool)
            clipToPadding = false
            addOnScrollListener(object : RecyclerView.OnScrollListener() {
                override fun onScrolled(rv: RecyclerView, dx: Int, dy: Int) {
                    super.onScrolled(rv, dx, dy)
                    val lm = rv.layoutManager as LinearLayoutManager
                    val totalItemCount = lm.itemCount
                    val lastVisiblePosition = lm.findLastVisibleItemPosition()
                    val threshold = 3
                    val shouldLoadMore = !isLoadingMore &&
                            lastVisiblePosition >= totalItemCount - threshold &&
                            lastVisiblePosition != lastLoadedPosition
                    if (dy > 0 && shouldLoadMore) {
                        isLoadingMore = true
                        lastLoadedPosition = lastVisiblePosition
                        viewModel.loadMore()
                    }
                }
            })
        }
    }

    private fun setupPullToRefresh() {
        binding.swipeRefresh.setOnRefreshListener {
            isLoadingMore = false
            lastLoadedPosition = -1
            viewModel.loadFeed()
        }
    }

    private fun setupSearch() {
        binding.searchView.setOnQueryTextListener(object : androidx.appcompat.widget.SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                query?.let {
                    viewModel.search(it)
                    binding.searchSuggestionsContainer.visibility = View.GONE
                }
                return true
            }

            override fun onQueryTextChange(newText: String?): Boolean {
                viewModel.search(newText ?: "")
                binding.searchSuggestionsContainer.visibility =
                    if (newText.isNullOrEmpty()) View.GONE else View.VISIBLE
                return false
            }
        })
    }

    private fun setupFilterButton() {
        binding.btnSort.setOnClickListener {
            // Пока что простой фильтр: показать только мероприятия от подписанных организаций
            val newFilters = viewModel.currentFilters.value.copy(
                showOnlySubscriptions = !(viewModel.currentFilters.value.showOnlySubscriptions ?: false)
            )
            viewModel.applyFilters(newFilters)
            Toast.makeText(
                requireContext(),
                if (newFilters.showOnlySubscriptions == true) "Показаны только подписки" else "Показаны все организации",
                Toast.LENGTH_SHORT
            ).show()
        }
    }

    private fun observeViewModel() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                binding.swipeRefresh.isRefreshing = false
                when (state) {
                    is UiState.Loading -> {
                        binding.progressBar.isVisible = sectionAdapter.itemCount == 0
                    }
                    is UiState.Success, is UiState.Cached -> {
                        val feed = if (state is UiState.Success) {
                            state.feedResponse
                        } else {
                            (state as UiState.Cached).feedResponse
                        }
                        sectionAdapter.submitList(feed.sections)
                        binding.tvErrorState.isVisible = false
                        binding.progressBar.isVisible = false
                        isLoadingMore = false
                    }
                    is UiState.Error -> {
                        binding.tvErrorState.text = "${state.message}"
                        binding.tvErrorState.isVisible = true
                        binding.progressBar.isVisible = false
                        isLoadingMore = false
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