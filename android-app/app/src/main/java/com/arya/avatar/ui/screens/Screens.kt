package com.arya.avatar.ui.screens

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.arya.avatar.BuildConfig
import com.arya.avatar.service.ConversationForegroundService
import com.arya.avatar.ui.AppViewModel
import com.arya.avatar.ui.Routes
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject

@Composable
fun SplashScreen(onDone: (String) -> Unit, viewModel: AppViewModel) {
    LaunchedEffect(Unit) {
        val dest = viewModel.resolveStartDestination()
        onDone(dest)
    }
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Arya AI", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(16.dp))
            CircularProgressIndicator()
        }
    }
}

@Composable
fun OnboardingScreen(onDone: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Talk naturally, face to face", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(12.dp))
        Text(
            "Arya is a real-time AI avatar. Speak, it listens and replies with captions.",
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Spacer(Modifier.height(24.dp))
        Button(onClick = onDone, modifier = Modifier.fillMaxWidth()) { Text("Get started") }
    }
}

@Composable
fun LoginScreen(viewModel: AppViewModel, onLoggedIn: (Boolean) -> Unit) {
    var email by remember { mutableStateOf("demo@example.com") }
    var password by remember { mutableStateOf("demo12345") }
    val loading by viewModel.loading.collectAsState()
    val error by viewModel.error.collectAsState()

    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Welcome back", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        OutlinedTextField(email, { email = it }, label = { Text("Email") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(password, { password = it }, label = { Text("Password") }, modifier = Modifier.fillMaxWidth())
        error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = MaterialTheme.colorScheme.error)
        }
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { viewModel.login(email, password, onLoggedIn) },
            enabled = !loading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (loading) "Signing in…" else "Log in")
        }
    }
}

@Composable
fun ConsentScreen(viewModel: AppViewModel, onDone: () -> Unit) {
    var understand by remember { mutableStateOf(false) }
    var voice by remember { mutableStateOf(false) }
    var store by remember { mutableStateOf(false) }
    var improve by remember { mutableStateOf(false) }
    var disclosure by remember { mutableStateOf(viewModel.disclosure) }
    val loading by viewModel.loading.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.loadDisclosure { disclosure = it }
    }

    Column(Modifier.fillMaxSize().padding(24.dp)) {
        Text("You'll talk to an AI", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(8.dp))
        Text(disclosure, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f))
        Spacer(Modifier.height(16.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(understand, { understand = it })
            Text("I understand this is an AI (required)")
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(voice, { voice = it })
            Text("Consent to voice processing (required)")
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(store, { store = it })
            Text("Store transcripts (optional)")
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(improve, { improve = it })
            Text("Improve the service (optional)")
        }
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = {
                viewModel.submitConsent(understand, voice, store, improve, onDone)
            },
            enabled = understand && voice && !loading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Agree & Continue")
        }
    }
}

@Composable
fun GalleryScreen(viewModel: AppViewModel, onAvatar: (String) -> Unit) {
    val avatars by viewModel.avatars.collectAsState()
    val user by viewModel.user.collectAsState()
    LaunchedEffect(Unit) { viewModel.loadGallery() }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Choose an avatar", style = MaterialTheme.typography.headlineSmall)
            user?.let { Text("${it.remaining_minutes} min") }
        }
        Spacer(Modifier.height(12.dp))
        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(avatars) { a ->
                Card(
                    Modifier.fillMaxWidth().clickable { onAvatar(a.id) },
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text(a.name, fontWeight = FontWeight.Bold)
                        Text(a.category, color = MaterialTheme.colorScheme.secondary)
                        Text(a.description, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f))
                    }
                }
            }
        }
    }
}

@Composable
fun AvatarDetailScreen(
    avatarId: String,
    viewModel: AppViewModel,
    onStart: (String) -> Unit,
    onBack: () -> Unit,
) {
    val avatars by viewModel.avatars.collectAsState()
    val avatar = avatars.find { it.id == avatarId }
    val loading by viewModel.loading.collectAsState()
    val error by viewModel.error.collectAsState()
    val context = LocalContext.current

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            viewModel.startSession(avatarId, onStart)
        }
    }

    fun requestMicAndStart() {
        val ok = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED
        if (ok) viewModel.startSession(avatarId, onStart)
        else permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
    }

    Column(Modifier.fillMaxSize().padding(24.dp)) {
        TextButton(onClick = onBack) { Text("Back") }
        Text(avatar?.name ?: "Avatar", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(8.dp))
        Text(avatar?.description ?: "")
        avatar?.greeting?.let {
            Spacer(Modifier.height(8.dp))
            Text("“$it”", color = MaterialTheme.colorScheme.secondary)
        }
        error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = MaterialTheme.colorScheme.error)
        }
        Spacer(Modifier.height(24.dp))
        Button(onClick = { requestMicAndStart() }, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
            Text(if (loading) "Starting…" else "Start conversation")
        }
        Text(
            "Mic is only used during a live conversation.",
            modifier = Modifier.padding(top = 8.dp),
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
        )
    }
}

@Composable
fun ConversationScreen(
    sessionId: String,
    viewModel: AppViewModel,
    onEnd: () -> Unit,
) {
    val context = LocalContext.current
    var state by remember { mutableStateOf("listening") }
    var input by remember { mutableStateOf("") }
    val captions = remember { mutableStateListOf<String>() }
    var ws by remember { mutableStateOf<WebSocket?>(null) }
    val error by viewModel.error.collectAsState()

    LaunchedEffect(sessionId) {
        context.startService(Intent(context, ConversationForegroundService::class.java))
        val client = OkHttpClient()
        val base = BuildConfig.API_BASE_URL
            .replace("http://", "ws://")
            .replace("https://", "wss://")
            .trimEnd('/')
        val token = viewModel.accessToken().orEmpty()
        val request = Request.Builder()
            .url("$base/ws/session/$sessionId?token=$token")
            .build()
        ws = client.newWebSocket(request, object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                val msg = JSONObject(text)
                when (msg.optString("type")) {
                    "state" -> state = msg.optString("state")
                    "transcript" -> {
                        val speaker = msg.optString("speaker")
                        val t = msg.optString("text")
                        val line = "${if (speaker == "user") "You" else "Avatar"}: $t"
                        if (msg.optBoolean("is_final", true)) {
                            captions.add(line)
                            if (captions.size > 30) captions.removeAt(0)
                        }
                    }
                }
            }
        })
    }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("AI · not a human", color = MaterialTheme.colorScheme.secondary)
            Text(state.replaceFirstChar { it.uppercase() }, fontWeight = FontWeight.Bold)
        }
        Box(
            Modifier
                .fillMaxWidth()
                .weight(1f)
                .padding(vertical = 24.dp),
            contentAlignment = Alignment.Center,
        ) {
            Box(
                Modifier
                    .size(160.dp)
                    .clip(CircleShape)
                    .background(
                        Brush.linearGradient(
                            listOf(
                                when (state) {
                                    "speaking" -> Color(0xFF22D3EE)
                                    "thinking" -> Color(0xFFFBBF24)
                                    else -> Color(0xFF34D399)
                                },
                                Color(0xFF7C5CFF),
                            ),
                        ),
                    ),
            )
        }
        LazyColumn(Modifier.height(120.dp)) {
            items(captions) { Text(it, style = MaterialTheme.typography.bodySmall) }
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        OutlinedTextField(
            value = input,
            onValueChange = { input = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Type message (mock STT)") },
        )
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = {
                val text = input.trim()
                if (text.isNotEmpty()) {
                    ws?.send(JSONObject().put("type", "user_text").put("text", text).toString())
                    input = ""
                }
            }) { Text("Send") }
            OutlinedButton(onClick = {
                ws?.send(JSONObject().put("type", "interrupt").toString())
            }) { Text("Interrupt") }
            Button(
                onClick = {
                    ws?.close(1000, null)
                    context.stopService(Intent(context, ConversationForegroundService::class.java))
                    viewModel.endSession(sessionId, onEnd)
                },
                colors = androidx.compose.material3.ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error,
                ),
            ) { Text("End") }
        }
    }
}

@Composable
fun SummaryScreen(onGallery: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Conversation ended", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        Button(onClick = onGallery) { Text("Back to gallery") }
    }
}
