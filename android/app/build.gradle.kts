plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("kotlin-kapt")  // ОБЯЗАТЕЛЬНО для Hilt
    id("com.google.dagger.hilt.android")  // ОБЯЗАТЕЛЬНО для Hilt
    id("kotlin-parcelize")  // Для Parcelable в EventDetailsBottomSheet
    id("com.google.gms.google-services")
}

android {
    namespace = "com.example.myapplication"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.myapplication"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }


    buildTypes {
        debug {
            isMinifyEnabled = false
            isDebuggable = true
            buildConfigField("String", "API_URL", "\"http://10.0.2.2:8001/\"")
            buildConfigField("String", "NOTIFICATION_API_URL", "\"http://10.0.2.2:8006/\"")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            buildConfigField("String", "API_URL", "\"https://api.volunteer-plus.ru/feed-service/\"")
            buildConfigField("String", "NOTIFICATION_API_URL", "\"https://api.volunteer-plus.ru/notification-service/\"")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17  // AGP 8.2 требует Java 17
        targetCompatibility = JavaVersion.VERSION_17
        isCoreLibraryDesugaringEnabled = true
    }

    kotlinOptions {
        jvmTarget = "17"  // Должно соответствовать Java версии
        freeCompilerArgs += listOf(
            "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi",
            "-opt-in=androidx.compose.material3.ExperimentalMaterial3Api"
        )
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    // Подавление предупреждений для dev-сборки
    lint {
        abortOnError = false
        checkReleaseBuilds = false
        disable += listOf("MissingTranslation", "ExtraTranslation")
    }
}

dependencies {
    // AndroidX Core
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")

    // Lifecycle & ViewModel
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-livedata-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-common-java8:2.7.0")

    // Coil – загрузка изображений
    implementation("io.coil-kt:coil:2.7.0")

    // Navigation
    implementation("androidx.navigation:navigation-fragment-ktx:2.7.7")
    implementation("androidx.navigation:navigation-ui-ktx:2.7.7")

    // Firebase BoM (управляет версиями)
    implementation(platform("com.google.firebase:firebase-bom:32.7.0"))

    // Firebase Cloud Messaging (push-уведомления)
    implementation("com.google.firebase:firebase-messaging-ktx")

    // Firebase Analytics (опционально, но рекомендуется)
    implementation("com.google.firebase:firebase-analytics-ktx")

    // Room
    val room_version = "2.7.0"
    implementation("androidx.room:room-runtime:$room_version")
    implementation("androidx.room:room-ktx:$room_version")
    kapt("androidx.room:room-compiler:$room_version")

    // Retrofit & OkHttp
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")

    // Hilt — Dependency Injection (КРИТИЧНО)
    implementation("com.google.dagger:hilt-android:2.57.2")
    kapt("com.google.dagger:hilt-compiler:2.57.2")

    // JWT Decoder (НОВЫЙ: для декодирования токенов на клиенте)
    implementation("com.auth0.android:jwtdecode:2.0.2")

    // Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")

    // Java 8+ APIs на старых Android
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")

    // CameraX
    implementation("androidx.camera:camera-camera2:1.4.0")
    implementation("androidx.camera:camera-lifecycle:1.4.0")
    implementation("androidx.camera:camera-view:1.4.0")
    // ML Kit Barcode Scanning
    implementation("com.google.mlkit:barcode-scanning:17.2.0")
    // QR code generation
    implementation("com.google.zxing:core:3.5.3")
}

// Настройка kapt для Hilt (КРИТИЧНО)
kapt {
    correctErrorTypes = true
    useBuildCache = true
    // Если возникают проблемы с генерацией классов:
    // arguments { arg("dagger.fastInit", "disabled") }
}

// Предотвращение конфликтов зависимостей
configurations.all {
    resolutionStrategy {
        force("com.google.dagger:dagger:2.57.2")
        force("com.google.dagger:dagger-lint-aar:2.57.2")
    }
}