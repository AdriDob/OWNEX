package ai.rastro.watch.ui.components

import ai.rastro.watch.model.ApiModels.WearOSStatus
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material.icons.filled.Info
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.compat.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun StatusScreen(
    status: WearOSStatus?,
    isConnected: Boolean,
    isLoading: Boolean,
    error: String?,
    onRefresh: () -> Unit,
    onNavigateToNotifications: () -> Unit,
    onNavigateToApprovals: () -> Unit,
    onNavigateToActions: () -> Unit
) {
    val scrollState = remember { androidx.compose.foundation.rememberScrollState() }

    androidx.compose.material3.Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        androidx.compose.foundation.layout.Box(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
        ) {
            androidx.compose.foundation.layout.Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Header with connection status
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "OWNEX Watch",
                        fontSize = 20.sp,
                        fontWeight = androidx.compose.ui.text.font.FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .background(
                                if (isConnected) Color.Green else Color.Red,
                                RoundedCornerShape(6.dp)
                            )
                    )
                }

                // Health score card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Salud del Sistema", fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(
                                text = "${status?.healthScore ?: 0}%",
                                fontSize = 36.sp,
                                fontWeight = androidx.compose.ui.text.font.FontWeight.Bold,
                                color = when {
                                    (status?.healthScore ?: 0) >= 80 -> Color.Green
                                    (status?.healthScore ?: 0) >= 50 -> Color.Yellow
                                    else -> Color.Red
                                }
                            )
                        }
                        Icon(
                            imageVector = androidx.compose.material.icons.filled.Favorite,
                            contentDescription = "Health",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(48.dp)
                        )
                    }
                }

                // Quick stats grid
                androidx.compose.foundation.layout.Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        StatCard("Findings", "${status?.findingsTotal ?: 0}", "${status?.findingsConfirmed ?: 0} confirmados", Icons.Default.CheckCircle, Color.Green)
                        StatCard("Targets", "${status?.targetsActive ?: 0} activos", "", Icons.Default.Wifi, MaterialTheme.colorScheme.primary)
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        StatCard("Workflows", "${status?.activeWorkflows ?: 0}", "activos", Icons.Default.Sync, MaterialTheme.colorScheme.secondary)
                        StatCard("Aprobaciones", "${status?.pendingApprovals ?: 0}", "pendientes", Icons.Default.Warning, Color.Orange)
                    }
                }

                // Connection status
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isConnected) Color.Green.copy(alpha = 0.1f) else Color.Red.copy(alpha = 0.1f)
                    )
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (isConnected) Icons.Default.Wifi else Icons.Default.WifiOff,
                                contentDescription = "Connection",
                                tint = if (isConnected) Color.Green else Color.Red
                            )
                            androidx.compose.foundation.layout.Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(if (isConnected) "Conectado" else "Desconectado", fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)
                                val backendStatus = if (status?.systemOnline == true) "Online" else "Offline"
                                val schedulerStatus = if (status?.schedulerRunning == true) "Running" else "Stopped"
                                Text("Backend: $backendStatus · Scheduler: $schedulerStatus", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Refresh",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier
                                .fillMaxWidth()
                                .wrapContentSize(Alignment.CenterHorizontally)
                                .padding(16.dp)
                                .clickable { /* refresh handled by parent */ }
                        )
                    }
                }

                // Error display
                error?.let { errorMsg ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color.Red.copy(alpha = 0.1f))
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Error, contentDescription = "Error", tint = Color.Red)
                            androidx.compose.foundation.layout.Spacer(modifier = Modifier.width(8.dp))
                            Text(errorMsg, color = Color.Red, fontSize = 14.sp)
                        }
                    }
                }

                // Quick navigation buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    NavButton("Notificaciones", Icons.Default.Notifications, MaterialTheme.colorScheme.primary) { /* handled by parent */ }
                    NavButton("Aprobaciones", Icons.Default.CheckCircle, MaterialTheme.colorScheme.secondary) { /* handled by parent */ }
                    NavButton("Acciones", Icons.Default.Info, MaterialTheme.colorScheme.tertiary) { /* handled by parent */ }
                }
            }
        }
    }
}

@Composable
fun StatCard(
    title: String,
    value: String,
    subtitle: String,
    icon: ImageVector,
    iconColor: Color
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .weight(1f)
            .padding(0.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainer
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(icon, contentDescription = title, tint = iconColor, modifier = Modifier.size(24.dp))
            androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(8.dp))
            Text(value, fontSize = 24.sp, fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)
            Text(title, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (subtitle.isNotBlank()) {
                Text(subtitle, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
fun NavButton(
    label: String,
    icon: ImageVector,
    color: Color,
    onClick: () -> Unit
) {
    androidx.compose.material3.Button(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .weight(1f)
            .height(56.dp),
        colors = androidx.compose.material3.ButtonDefaults.buttonColors(
            containerColor = color.copy(alpha = 0.2f),
            contentColor = color
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Icon(icon, contentDescription = label, modifier = Modifier.size(24.dp))
            Text(label, fontSize = 12.sp, fontWeight = androidx.compose.ui.text.font.FontWeight.Medium, maxLines = 1, overflow = androidx.compose.ui.text.overflow.TextOverflow.Ellipsis)
        }
    }
}