package ai.rastro.watch.ui

import ai.rastro.watch.ui.components.ApprovalsScreen
import ai.rastro.watch.ui.components.NotificationsScreen
import ai.rastro.watch.ui.components.QuickActionsScreen
import ai.rastro.watch.ui.components.StatusScreen
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Snackbar
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.livedata.observeAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
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

            error?.let { errorMsg ->
                Snackbar(
                    modifier = Modifier.padding(16.dp),
                    action = { Text("Close") },
                    dismissAction = { /* dismiss */ }
                ) {
                    Text(errorMsg)
                }
            }
        }
    }
}
