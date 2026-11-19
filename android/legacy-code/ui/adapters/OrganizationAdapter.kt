package com.example.myapplication.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import coil.transform.CircleCropTransformation
import com.example.myapplication.R
import com.example.myapplication.ui.viewmodels.OrganizationDisplayItem
import com.google.android.material.imageview.ShapeableImageView

class OrganizationAdapter(
    private val onChatClick: (OrganizationDisplayItem) -> Unit,
    private val onSubscribeClick: (OrganizationDisplayItem) -> Unit
) : ListAdapter<OrganizationDisplayItem, OrganizationAdapter.ViewHolder>(DiffCallback()) {

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val avatarImage: ShapeableImageView = itemView.findViewById(R.id.iv_org_avatar)
        val nameText: TextView = itemView.findViewById(R.id.tv_org_name)
        val descriptionText: TextView = itemView.findViewById(R.id.tv_org_description)
        val ratingText: TextView = itemView.findViewById(R.id.tv_org_rating)
        val subscribeButton: Button = itemView.findViewById(R.id.btn_subscribe)
        val chatButton: Button = itemView.findViewById(R.id.btn_chat)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_organization, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val org = getItem(position)
        holder.nameText.text = org.name
        holder.descriptionText.text = org.description
        holder.ratingText.text = "★ ${org.rating}"
        holder.subscribeButton.apply {
            isEnabled = !org.isSubscribed
            text = if (org.isSubscribed) "Вы подписаны" else "Подписаться"
        }
        holder.subscribeButton.setOnClickListener { onSubscribeClick(org) }
        holder.chatButton.setOnClickListener { onChatClick(org) }

        // Загрузка аватарки
        holder.avatarImage.load(org.avatarUrl) {
            placeholder(R.drawable.ic_profile)    // показывается во время загрузки
            error(R.drawable.ic_profile)          // если URL недействителен или ошибка
            transformations(CircleCropTransformation())
        }
    }

    class DiffCallback : DiffUtil.ItemCallback<OrganizationDisplayItem>() {
        override fun areItemsTheSame(oldItem: OrganizationDisplayItem, newItem: OrganizationDisplayItem) =
            oldItem.id == newItem.id

        override fun areContentsTheSame(oldItem: OrganizationDisplayItem, newItem: OrganizationDisplayItem) =
            oldItem == newItem
    }
}