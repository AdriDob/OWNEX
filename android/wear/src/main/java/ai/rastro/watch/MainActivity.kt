package ai.rastro.watch

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.lifecycle.viewmodel.compose.viewModel
import ai.rastro.watch.ui.WearOSApp
import ai.rastro.watch.ui.WatchViewModel
import ai.rastro.watch.preferences.PreferencesManager

class MainActivity : ComponentActivity() {

    private val preferencesManager: PreferencesManager by lazy {
        PreferencesManager().also { it.initialize(this) }
    }

    private val viewModel: WatchViewModel by viewModel { WatchViewModel(preferencesManager) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(
                    modifier = androidx.compose.ui.Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    WearOSApp(viewModel = viewModel)
                }
            }
        }
    }
}