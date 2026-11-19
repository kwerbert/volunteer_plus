package com.example.myapplication.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.R
import com.example.myapplication.data.models.EventItem
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.time.OffsetDateTime
import java.time.ZoneId

class EventItemAdapter(
    private val onEventClick: (EventItem) -> Unit = {}
) : ListAdapter<EventItem, EventItemAdapter.EventViewHolder>(EventDiffCallback()) {

    companion object {
        private val INPUT_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss")
        private val OUTPUT_DATE_FORMAT = DateTimeFormatter.ofPattern("dd MMM", Locale("ru"))
        private val OUTPUT_TIME_FORMAT = DateTimeFormatter.ofPattern("HH:mm")
    }

    inner class EventViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val titleText: TextView = itemView.findViewById(R.id.tv_event_title)
        private val orgText: TextView = itemView.findViewById(R.id.tv_organization_name)
        private val timeText: TextView = itemView.findViewById(R.id.tv_event_time)

        fun bind(event: EventItem) {
            titleText.text = event.title
            orgText.text = event.organization.name

            timeText.text = try {
                val startParsed = OffsetDateTime.parse(event.startTime).atZoneSameInstant(ZoneId.systemDefault())
                val datePart = startParsed.format(DateTimeFormatter.ofPattern("dd MMM", Locale("ru")))
                val timePart = startParsed.format(DateTimeFormatter.ofPattern("HH:mm"))

                val endStr = event.endTime?.let { endRaw ->
                    try {
                        val endParsed = OffsetDateTime.parse(endRaw).atZoneSameInstant(ZoneId.systemDefault())
                        "–${endParsed.format(DateTimeFormatter.ofPattern("HH:mm"))}"
                    } catch (e: Exception) { "" }
                } ?: ""

                "$datePart • $timePart$endStr"
            } catch (e: Exception) {
                event.startTime
            }

            itemView.setOnClickListener { onEventClick(event) }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): EventViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_event, parent, false)
        return EventViewHolder(view)
    }

    override fun onBindViewHolder(holder: EventViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    class EventDiffCallback : DiffUtil.ItemCallback<EventItem>() {
        override fun areItemsTheSame(old: EventItem, new: EventItem) = old.id == new.id

        override fun areContentsTheSame(old: EventItem, new: EventItem): Boolean {
            return old.id == new.id &&
                    old.title == new.title &&
                    old.startTime == new.startTime &&
                    old.endTime == new.endTime &&
                    old.descriptionPreview == new.descriptionPreview &&
                    old.organization.id == new.organization.id &&
                    old.organization.name == new.organization.name &&
                    old.locationLat == new.locationLat &&
                    old.locationLon == new.locationLon &&
                    old.distanceKm == new.distanceKm
        }
    }
}