package ai.rastro.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
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
import ai.rastro.app.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HealthScreen(apiClient: OwnexApiClient) {
    var status by remember { mutableStateOf(SystemStatus()) }
    var health by remember { mutableStateOf(HealthCheck()) }
    var revenue by remember { mutableStateOf(RevenueSummary()) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    fun refresh() {
        scope.launch {
            loading = true
            val (s, h, r) = withContext(Dispatchers.IO) {
                Triple(apiClient.getSystemStatus(), apiClient.getHealth(), apiClient.getRevenueSummary())
            }
            status = s; health = h; revenue = r
            loading = false
        }
    }

    LaunchedEffect(Unit) { refresh() }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("System", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color.White)
                TextButton(onClick = { refresh() }) { Text("Refresh", color = Color(0xFF00D5FF)) }
            }
        }

        // Health score
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A)),
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier.size(48.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            "${health.score}",
                            fontSize = 24.sp,
                            fontWeight = FontWeight.Bold,
                            color = when {
                                health.score >= 80 -> Color(0xFF16A34A)
                                health.score >= 50 -> Color(0xFFD97706)
                                else -> Color(0xFF3B82F6)
                            }
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text("System Health", fontSize = 14.sp, fontWeight = FontWeight.Medium, color = Color.White)
                        Text(
                            if (health.healthy) "All systems operational" else "Issues detected",
                            fontSize = 12.sp,
                            color = if (health.healthy) Color(0xFF16A34A) else Color(0xFF3B82F6)
                        )
                    }
                }
            }
        }

        // Worker controls
        item {
            Text("Worker", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
        }
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A)),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            if (status.workerRunning) "🟢 Running" else "⚪ Stopped",
                            fontSize = 13.sp,
                            color = Color.White
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (!status.workerRunning) {
                            Button(
                                onClick = { scope.launch { withContext(Dispatchers.IO) { apiClient.startWorker() }; refresh() } },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF16A34A)),
                                shape = RoundedCornerShape(6.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Start", fontSize = 11.sp)
                            }
                        } else {
                            OutlinedButton(
                                onClick = { scope.launch { withContext(Dispatchers.IO) { apiClient.stopWorker() }; refresh() } },
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF3B82F6)),
                                shape = RoundedCornerShape(6.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Icon(Icons.Default.Stop, contentDescription = null, modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Stop", fontSize = 11.sp)
                            }
                            OutlinedButton(
                                onClick = { scope.launch { withContext(Dispatchers.IO) { apiClient.pauseWorker() }; refresh() } },
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFD97706)),
                                shape = RoundedCornerShape(6.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Icon(Icons.Default.Pause, contentDescription = null, modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Pause", fontSize = 11.sp)
                            }
                        }
                    }
                }
            }
        }

        // Revenue
        item {
            Text("Revenue", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
        }
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A)),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    RevenueRow("Expected", revenue.expected, Color(0xFF00D5FF))
                    RevenueRow("Earned", revenue.earned, Color(0xFF16A34A))
                    RevenueRow("Pending", revenue.pending, Color(0xFFD97706))
                    RevenueRow("Net", revenue.net, Color.White)
                }
            }
        }

        // Info
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A)),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    InfoRow("Version", status.version)
                    InfoRow("Uptime", status.uptime.ifEmpty { "—" })
                    InfoRow("Active Work", "${status.activeWork}")
                    InfoRow("Today Actions", "${status.todayActions}")
                }
            }
        }
    }
}

@Composable
fun RevenueRow(label: String, amount: Double, color: Color) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, fontSize = 12.sp, color = Color(0xFF8A8A8A))
        Text("$${String.format("%.2f", amount)}", fontSize = 12.sp, fontWeight = FontWeight.Medium, color = color)
    }
}

@Composable
fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, fontSize = 12.sp, color = Color(0xFF8A8A8A))
        Text(value, fontSize = 12.sp, color = Color.White)
    }
}
