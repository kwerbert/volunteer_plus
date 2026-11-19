package com.example.myapplication.ui.activities

import android.graphics.Bitmap
import android.os.Bundle
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.myapplication.R
import com.example.myapplication.util.QrCodeGenerator
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class QrCodeActivity : AppCompatActivity() {

    private lateinit var qrImageView: ImageView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_qr_code)

        qrImageView = findViewById(R.id.iv_qr_code)

        val eventId = intent.getIntExtra("event_id", -1)
        val qrSecret = intent.getStringExtra("qr_secret")

        if (eventId == -1 || qrSecret.isNullOrEmpty()) {
            Toast.makeText(this, "Ошибка: данные мероприятия не найдены", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // Формат QR-данных: event_id:secret (или просто secret)
        val qrData = "$eventId:$qrSecret"
        val qrBitmap: Bitmap? = QrCodeGenerator.generateQrCode(qrData, 500, 500)
        if (qrBitmap != null) {
            qrImageView.setImageBitmap(qrBitmap)
        } else {
            Toast.makeText(this, "Ошибка генерации QR-кода", Toast.LENGTH_SHORT).show()
            finish()
        }
    }
}