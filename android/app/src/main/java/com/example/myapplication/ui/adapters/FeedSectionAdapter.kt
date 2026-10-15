package com.example.myapplication.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.data.models.FeedSection

class FeedSectionAdapter(
    private val recyclerViewPool: RecyclerView.RecycledViewPool,
    private val onEventClick: (com.example.myapplication.data.models.EventItem) -> Unit = {}
) : ListAdapter<FeedSection, FeedSectionAdapter.SectionViewHolder>(SectionDiffCallback()) {

    inner class SectionViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val sectionTitle: TextView = itemView.findViewById(R.id.tv_section_title)
        private val eventsRecyclerView: RecyclerView = itemView.findViewById(R.id.rv_events)
        private val eventAdapter = EventItemAdapter(onEventClick)

        init {
            eventsRecyclerView.apply {
                adapter = eventAdapter
                setRecycledViewPool(recyclerViewPool)
                setHasFixedSize(true)
                isNestedScrollingEnabled = false
            }
        }

        fun bind(section: FeedSection) {
            sectionTitle.text = section.sectionTitle
            val isHorizontal = section.layout.equals("horizontal", ignoreCase = true)
            val layoutManager = eventsRecyclerView.layoutManager as? LinearLayoutManager

            if (layoutManager == null ||
                layoutManager.orientation != (if (isHorizontal) LinearLayoutManager.HORIZONTAL else LinearLayoutManager.VERTICAL)) {
                eventsRecyclerView.layoutManager = LinearLayoutManager(
                    itemView.context,
                    if (isHorizontal) LinearLayoutManager.HORIZONTAL else LinearLayoutManager.VERTICAL,
                    false
                )
            }

            eventAdapter.submitList(section.events)
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SectionViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_feed_section, parent, false)
        return SectionViewHolder(view)
    }

    override fun onBindViewHolder(holder: SectionViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    class SectionDiffCallback : DiffUtil.ItemCallback<FeedSection>() {
        override fun areItemsTheSame(oldItem: FeedSection, newItem: FeedSection): Boolean {
            return generateSectionId(oldItem) == generateSectionId(newItem)
        }

        override fun areContentsTheSame(oldItem: FeedSection, newItem: FeedSection): Boolean {
            return oldItem.sectionType == newItem.sectionType &&
                    oldItem.sectionTitle == newItem.sectionTitle &&
                    oldItem.layout == newItem.layout &&
                    oldItem.events.size == newItem.events.size &&
                    oldItem.events.zip(newItem.events).all { (old, new) ->
                        old.id == new.id && old.title == new.title && old.startTime == new.startTime
                    }
        }

        // ИСПРАВЛЕНО: используем ${} для явного разделения переменной и символа "_"
        private fun generateSectionId(section: FeedSection): String {
            val eventsHash = section.events.sumOf { it.id }.toString()
            val eventsCount = section.events.size
            // БЫЛО: "$eventsCount_$eventsHash" (компилятор ищет переменную eventsCount_)
            // СТАЛО: "${eventsCount}_$eventsHash" (явно указываем границу переменной)
            return "${section.sectionType}_${section.sectionTitle}_${eventsCount}_$eventsHash"
        }
    }
}