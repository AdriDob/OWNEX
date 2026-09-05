package ai.rastro.app.ui.theme

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Tesla-inspired: pure black, white primary, cyan accent
private val DarkColorScheme = darkColorScheme(
    primary = Color.White,
    onPrimary = Color.Black,
    secondary = Color(0xFF00D5FF),
    onSecondary = Color.Black,
    background = Color.Black,
    onBackground = Color(0xFFF5F5F5),
    surface = Color(0xFF0A0A0A),
    onSurface = Color(0xFFF5F5F5),
    surfaceVariant = Color(0xFF141414),
    onSurfaceVariant = Color(0xFF8A8A8A),
    outline = Color(0xFF1F1F1F),
    error = Color(0xFF3B82F6),
    onError = Color.White,
    errorContainer = Color(0xFF1A1A2E),
    tertiary = Color(0xFF16A34A),  // success green
    tertiaryContainer = Color(0xFF0A2E1A),
)

@Composable
fun OwnexTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = Typography(),
        content = content
    )
}
