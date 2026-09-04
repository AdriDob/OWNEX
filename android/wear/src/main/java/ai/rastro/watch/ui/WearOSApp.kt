package ai.rastro.watch.ui

import ai.rastro.watch.model.ApiModels.WearOSApproval
import ai.rastro.watch.model.ApiModels.WearOSNotification
import ai.rastro.watch.model.ApiModels.WearOSStatus
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.livedata.observeAsState
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
import androidx.lifecycle.viewmodel.compose.viewModel
import ai.rastro.watch.model.ApiModels.WearOSApproval
import ai.rastro.watch.model.ApiModels.WearOSNotification
import ai.rastro.watch.model.ApiModels.WearOSStatus
import ai.rastro.watch.ui.components.ApprovalsScreen
import ai.rastro.watch.ui.components.NotificationsScreen
import ai.rastro.watch.ui.components.QuickActionsScreen
import ai.rastro.watch.ui.components.StatusScreen
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController

@Composable
fun WearOSApp(
    viewModel: WatchViewModel = viewModel()
) {
    val navController = rememberNavController()
    val status by viewModel.status.observeAsState()
    val isConnected by viewModel.isConnected.observeAsState()
    val isLoading by viewModel.isLoading.observeAsState()
    val error by viewModel.error.observeAsState()

    MaterialTheme {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.TopCenter
        ) {
            NavHost(navController, startDestination = "status") {
                composable("status") {
                    StatusScreen(
                        status = status,
                        isConnected = isConnected,
                        isLoading = isLoading,
                        error = error,
                        onRefresh = { viewModel.syncAll() },
                        onNavigateToNotifications = { navController.navigate("notifications") },
                        onNavigateToApprovals = { navController.navigate("approvals") },
                        onNavigateToActions = { navController.navigate("actions") }
                    )
                }
                composable("notifications") {
                    NotificationsScreen(
                        notifications = viewModel.notifications.observeAsState().value ?: emptyList(),
                        isLoading = isLoading,
                        onMarkRead = { viewModel.markNotificationRead(it) },
                        onBack = { navController.popBackStack() }
                    )
                }
                composable("approvals") {
                    ApprovalsScreen(
                        approvals = viewModel.pendingApprovals.observeAsState().value ?: emptyList(),
                        isLoading = isLoading,
                        onRespond = { id, approved -> viewModel.respondToApproval(id, approved) },
                        onBack = { navController.popBackStack() }
                    )
                }
                composable("actions") {
                    QuickActionsScreen(
                        onAction = { action ->
                            when (action) {
                                "refresh" -> viewModel.syncAll()
                                "merlin" -> { /* navigate to merlin */ }
                                "dashboard" -> { /* navigate to dashboard */ }
                                "notifications" -> navController.navigate("notifications")
                            }
                        },
                        onBack = { navController.popBackStack() }
                    )
                }
            }

            // Error banner
            error?.let { errorMsg ->
                androidx.compose.material3.Snackbar(
                    modifier = Modifier.padding(16.dp),
                    action = { Text("Cerrar") },
                    dismissAction = { /* dismiss */ }
                ) {
                    Text(errorMsg)
                }
            }
        }
    }
}