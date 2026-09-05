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
import ai.rastro.app.model.ApprovalItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApprovalsScreen(apiClient: OwnexApiClient) {
    var approvals by remember { mutableStateOf(listOf<ApprovalItem>()) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    fun refresh() {
        scope.launch {
            loading = true
            approvals = withContext(Dispatchers.IO) { apiClient.getPendingApprovals() }
            loading = false
        }
    }

    LaunchedEffect(Unit) { refresh() }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Approvals", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color.White)
                    Text("${approvals.size} pending", fontSize = 12.sp, color = Color(0xFF8A8A8A))
                }
                TextButton(onClick = { refresh() }) {
                    Text("Refresh", color = Color(0xFF00D5FF))
                }
            }
        }

        if (loading) {
            item {
                Box(
                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = Color(0xFF00D5FF), strokeWidth = 2.dp, modifier = Modifier.size(24.dp))
                }
            }
        }

        if (!loading && approvals.isEmpty()) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFF0A0A0A))
                        .padding(32.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF16A34A), modifier = Modifier.size(32.dp))
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("All clear!", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                        Text("No pending approvals", color = Color(0xFF8A8A8A), fontSize = 12.sp)
                    }
                }
            }
        }

        items(approvals) { item ->
            ApprovalCard(
                approval = item,
                onApprove = {
                    scope.launch {
                        withContext(Dispatchers.IO) { apiClient.approveAction(item.id) }
                        refresh()
                    }
                },
                onReject = {
                    scope.launch {
                        withContext(Dispatchers.IO) { apiClient.rejectAction(item.id) }
                        refresh()
                    }
                }
            )
        }
    }
}

@Composable
fun ApprovalCard(approval: ApprovalItem, onApprove: () -> Unit, onReject: () -> Unit) {
    val riskColor = when (approval.risk) {
        "high" -> Color(0xFF3B82F6)
        "medium" -> Color(0xFFD97706)
        else -> Color(0xFF8A8A8A)
    }

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
                Text(approval.title, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = Color.White)
                Surface(
                    color = riskColor.copy(alpha = 0.15f),
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        approval.risk.uppercase(),
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = riskColor
                    )
                }
            }
            if (approval.description.isNotEmpty()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(approval.description, fontSize = 12.sp, color = Color(0xFF8A8A8A))
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text("Type: ${approval.type} · ${approval.createdAt}", fontSize = 10.sp, color = Color(0xFF8A8A8A))
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onApprove,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF16A34A)),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Approve", fontSize = 12.sp)
                }
                OutlinedButton(
                    onClick = onReject,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF3B82F6)),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Icon(Icons.Default.Close, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Reject", fontSize = 12.sp)
                }
            }
        }
    }
}
