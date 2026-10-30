package ai.rastro.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.rastro.app.api.OwnexApiClient
import ai.rastro.app.model.ChatMessage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CopilotScreen(apiClient: OwnexApiClient) {
    var messages by remember { mutableStateOf(listOf(
        ChatMessage(id = "1", role = "assistant", content = "Hey! I'm MERLIN, your OWNEX copilot. Ask me anything about your opportunities, revenue, or system status.", timestamp = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()))
    )) }
    var input by remember { mutableStateOf("") }
    var isTyping by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    fun sendMessage() {
        if (input.isBlank()) return
        val userMsg = ChatMessage(
            id = UUID.randomUUID().toString(),
            role = "user",
            content = input.trim(),
            timestamp = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
        )
        messages = messages + userMsg
        val query = input.trim()
        input = ""

        scope.launch {
            isTyping = true
            val response = withContext(Dispatchers.IO) {
                // Use the chat endpoint or generate a contextual response
                val status = apiClient.getSystemStatus()
                val brief = apiClient.getDailyBrief()
                val workItems = apiClient.getWorkItems()
                val revenue = apiClient.getRevenueSummary()

                buildString {
                    appendLine("Here's your current status:")
                    appendLine()
                    appendLine("📊 System: ${status.status} | Worker: ${if (status.workerRunning) "running" else "stopped"}")
                    appendLine("💰 Revenue: earned $${String.format("%.2f", revenue.earned)}, pending $${String.format("%.2f", revenue.pending)}")
                    appendLine("📋 Active work: ${status.activeWork} items")
                    appendLine("🔔 Pending approvals: ${status.pendingApprovals}")
                    if (brief.topActions.isNotEmpty()) {
                        appendLine()
                        appendLine("🎯 Top action: ${brief.topActions.first().title}")
                        appendLine("   EV: $${String.format("%.0f", brief.topActions.first().ev)} | ${String.format("%.0f", brief.topActions.first().probability * 100)}% probability")
                    }
                    appendLine()
                    appendLine("Ask me to start work, approve items, or check specific opportunities!")
                }
            }
            val assistantMsg = ChatMessage(
                id = UUID.randomUUID().toString(),
                role = "assistant",
                content = response,
                timestamp = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
            )
            messages = messages + assistantMsg
            isTyping = false
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Header
        Surface(
            color = Color(0xFF0A0A0A),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("🤖", fontSize = 20.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text("MERLIN", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color.White)
                    Text("AI Copilot", fontSize = 10.sp, color = Color(0xFF8A8A8A))
                }
            }
        }

        // Messages
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(vertical = 12.dp)
        ) {
            items(messages) { msg ->
                MessageBubble(msg)
            }
            if (isTyping) {
                item {
                    Row(
                        modifier = Modifier.padding(start = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(12.dp),
                            strokeWidth = 1.5.dp,
                            color = Color(0xFF00D5FF)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("MERLIN is thinking...", fontSize = 11.sp, color = Color(0xFF8A8A8A))
                    }
                }
            }
        }

        // Input
        Surface(
            color = Color(0xFF0A0A0A),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("Ask MERLIN...", color = Color(0xFF8A8A8A)) },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Color(0xFF00D5FF),
                        unfocusedBorderColor = Color(0xFF1F1F1F),
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                    ),
                    shape = RoundedCornerShape(8.dp),
                    singleLine = true,
                )
                Spacer(modifier = Modifier.width(8.dp))
                IconButton(
                    onClick = { sendMessage() },
                    enabled = input.isNotBlank() && !isTyping
                ) {
                    Icon(
                        Icons.AutoMirrored.Filled.Send,
                        contentDescription = "Send",
                        tint = if (input.isNotBlank()) Color(0xFF00D5FF) else Color(0xFF8A8A8A)
                    )
                }
            }
        }
    }
}

@Composable
fun MessageBubble(msg: ChatMessage) {
    val isUser = msg.role == "user"
    val bgColor = if (isUser) Color(0xFF00D5FF).copy(alpha = 0.1f) else Color(0xFF0A0A0A)
    val alignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart

    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = alignment
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 300.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(bgColor)
                .padding(10.dp)
        ) {
            Text(
                msg.content,
                fontSize = 13.sp,
                color = Color.White,
                lineHeight = 18.sp
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                msg.timestamp,
                fontSize = 9.sp,
                color = Color(0xFF8A8A8A)
            )
        }
    }
}
