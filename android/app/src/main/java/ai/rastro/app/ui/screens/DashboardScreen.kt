package ai.rastro.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(apiClient: OwnexApiClient) {
    var status by remember { mutableStateOf(SystemStatus()) }
    var brief by remember { mutableStateOf(DailyBrief()) }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        withContext(Dispatchers.IO) {
            status = apiClient.getSystemStatus()
            brief = apiClient.getDailyBrief()
            loading = false
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Header
        item {
            Text(
                text = "OWNEX",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                modifier = Modifier.padding(bottom = 4.dp)
            )
            Text(
                text = "Personal Work OS",
                fontSize = 12.sp,
                color = Color(0xFF8A8A8A),
            )
        }

        // Status bar
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0xFF0A0A0A))
                    .padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                StatusChip(
                    label = "System",
                    value = status.status,
                    color = if (status.status == "ok") Color(0xFF16A34A) else Color(0xFF3B82F6)
                )
                StatusChip(
                    label = "Worker",
                    value = if (status.workerRunning) "Running" else "Stopped",
                    color = if (status.workerRunning) Color(0xFF16A34A) else Color(0xFF8A8A8A)
                )
                StatusChip(
                    label = "Active",
                    value = "${status.activeWork}",
                    color = Color(0xFF00D5FF)
                )
            }
        }

        // Daily Brief
        item {
            Text(
                text = brief.greeting.ifEmpty { "Today" },
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                modifier = Modifier.padding(top = 8.dp)
            )
        }

        // Revenue today
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0xFF0A0A0A))
                    .padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text("Revenue Today", fontSize = 10.sp, color = Color(0xFF8A8A8A))
                    Text(
                        "$${String.format("%.2f", brief.revenueToday)}",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF16A34A)
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("Total EV", fontSize = 10.sp, color = Color(0xFF8A8A8A))
                    Text(
                        "$${String.format("%.0f", brief.totalEV)}",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF00D5FF)
                    )
                }
            }
        }

        // Top actions
        item {
            Text(
                text = "Next Actions",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                modifier = Modifier.padding(top = 8.dp)
            )
        }

        if (brief.topActions.isEmpty() && !loading) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFF0A0A0A))
                        .padding(24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text("No actions right now", color = Color(0xFF8A8A8A), fontSize = 13.sp)
                }
            }
        }

        items(brief.topActions) { action ->
            ActionCard(action = action)
        }

        // Pending approvals
        if (status.pendingApprovals > 0) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = null,
                            tint = Color(0xFFD97706),
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "${status.pendingApprovals} approval(s) pending",
                            color = Color(0xFFD97706),
                            fontSize = 13.sp
                        )
                    }
                }
            }
        }

        // Loading indicator
        if (loading) {
            item {
                Box(
                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(
                        color = Color(0xFF00D5FF),
                        strokeWidth = 2.dp,
                        modifier = Modifier.size(24.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun StatusChip(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, fontSize = 9.sp, color = Color(0xFF8A8A8A))
        Text(value, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = color)
    }
}

@Composable
fun ActionCard(action: ActionItem) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    action.title,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color.White,
                    modifier = Modifier.weight(1f)
                )
                Text(
                    "$${String.format("%.0f", action.ev)}",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF16A34A)
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    action.platform,
                    fontSize = 10.sp,
                    color = Color(0xFF8A8A8A)
                )
                Text(
                    "${String.format("%.0f", action.probability * 100)}% · ${String.format("%.1f", action.estimatedHours)}h",
                    fontSize = 10.sp,
                    color = Color(0xFF8A8A8A)
                )
            }
            if (action.nextStep.isNotEmpty()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    "→ ${action.nextStep}",
                    fontSize = 11.sp,
                    color = Color(0xFF00D5FF)
                )
            }
        }
    }
}
