package ai.rastro.watch.ui.components

import ai.rastro.watch.model.ApiModels.WearOSNotification
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun NotificationsScreen(
    notifications: List<WearOSNotification>,
    isLoading: Boolean,
    onMarkRead: (String) -> Unit,
    onBack: () -> Unit
) {
    val unreadCount = notifications.count { !it.read }

    MaterialTheme {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            TopAppBar(
                title = { Text("Notificaciones ($unreadCount no leídas)") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.Close, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.mediumTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            )

            if (isLoading) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(MaterialTheme.colorScheme.background),
                    contentAlignment = Alignment.Center
                ) {
                    androidx.compose.material3.CircularProgressIndicator()
                }
            } else if (notifications.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(MaterialTheme.colorScheme.background),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(Icons.Default.Notifications, contentDescription = "No notifications", modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Sin notificaciones", fontSize = 16.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Las notificaciones aparecerán aquí", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(notifications) { notification ->
                        NotificationCard(
                            notification = notification,
                            onClick = { onMarkRead(notification.notificationId) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun NotificationCard(
    notification: WearOSNotification,
    onClick: () -> Unit
) {
    val levelColor = when (notification.level.lowercase()) {
        "critical" -> Color.Red
        "high" -> Color.Orange
        "medium" -> MaterialTheme.colorScheme.primary
        "low" -> MaterialTheme.colorScheme.secondary
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(0.dp)
            .background(
                if (!notification.read) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
                else MaterialTheme.colorScheme.surfaceContainer
            )
            .clickable { onClick() },
        colors = CardDefaults.cardColors(
            containerColor = if (!notification.read) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
            else MaterialTheme.colorScheme.surfaceContainer
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = notification.title,
                        fontSize = 16.sp,
                        fontWeight = androidx.compose.ui.text.font.FontWeight.Bold,
                        maxLines = 2,
                        overflow = androidx.compose.ui.text.overflow.TextOverflow.Ellipsis
                    )
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = notification.message,
                        fontSize = 14.sp,
                        maxLines = 3,
                        overflow = androidx.compose.ui.text.overflow.TextOverflow.Ellipsis,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                if (!notification.read) {
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.width(8.dp))
                    androidx.compose.material3.Checkbox(
                        checked = false,
                        onCheckedChange = { /* handled by click */ },
                        modifier = Modifier
                            .size(24.dp)
                            .padding(top = 4.dp)
                    )
                }
            }
            androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    androidx.compose.material3.Badge(
                        badgeContent = {
                            Text(notification.level.uppercase(), fontSize = 10.sp, fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)
                        },
                        colors = androidx.compose.material3.BadgeDefaults.badgeColors(
                            containerColor = levelColor,
                            contentColor = Color.White
                        )
                    )
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = formatTimestamp(notification.createdAt),
                        fontSize = 10.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                if (notification.requiresAction) {
                    Icon(
                        imageVector = Icons.Default.Notifications,
                        contentDescription = "Requiere acción",
                        tint = Color.Orange,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
        }
    }
}

fun formatTimestamp(isoString: String): String {
    return try {
        val formatter = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.getDefault())
        val date = formatter.parse(isoString)
        val outputFormat = java.text.SimpleDateFormat("HH:mm dd/MM", java.util.Locale.getDefault())
        outputFormat.format(date)
    } catch (e: Exception) {
        isoString
    }
}