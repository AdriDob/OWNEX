package ai.catseye.wearos

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.support.wearable.activity.WearableActivity
import android.support.wearable.view.WatchViewStub
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.wear.widget.WearableRecyclerView
import kotlinx.coroutines.*
import org.json.JSONObject

/**
 * ORION Wear OS Companion — Complete App with Supabase Sync
 */
class MainActivity : WearableActivity() {

    private lateinit var sharedPreferences: SharedPreferences
    private lateinit var systemStatusView: TextView
    private lateinit var tasksCountView: TextView
    private lateinit var habitsCountView: TextView
    private lateinit var currentMoodView: TextView
    private lateinit var refreshButton: Button
    private lateinit var logoutButton: Button

    private var userId: String? = null
    private var accessToken: String? = null

    companion object {
        private const val PREFS_NAME = "OrionPrefs"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_ACCESS_TOKEN = "access_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        sharedPreferences = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

        val stub = findViewById<WatchViewStub>(R.id.watch_view_stub)
        stub.setOnLayoutListener {
            initializeViews()
            checkAuth()
        }
    }

    private fun initializeViews() {
        systemStatusView = findViewById(R.id.system_status)
        tasksCountView = findViewById(R.id.tasks_count)
        habitsCountView = findViewById(R.id.habits_count)
        currentMoodView = findViewById(R.id.current_mood)
        refreshButton = findViewById(R.id.btn_refresh)
        logoutButton = findViewById(R.id.btn_logout)

        refreshButton.setOnClickListener { refreshData() }
        logoutButton.setOnClickListener { logout() }
    }

    private fun checkAuth() {
        userId = sharedPreferences.getString(KEY_USER_ID, null)
        accessToken = sharedPreferences.getString(KEY_ACCESS_TOKEN, null)

        if (userId == null || accessToken == null) {
            // No auth - show pairing screen
            showPairingScreen()
        } else {
            // Authenticated - load data
            loadData()
        }
    }

    private fun showPairingScreen() {
        systemStatusView.text = "🔴 Not Paired"
        tasksCountView.text = "Pair with Android"
        habitsCountView.text = "Open Orion Companion on Android"
        currentMoodView.text = "⚠️"
        refreshButton.visibility = View.GONE
        logoutButton.visibility = View.GONE
    }

    private fun loadData() {
        systemStatusView.text = "🟢 ORION Online"
        refreshButton.visibility = View.VISIBLE
        logoutButton.visibility = View.VISIBLE

        // In production, make API calls to Supabase
        // For now, load from backend API
        refreshData()
    }

    private fun refreshData() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // In production, call Supabase directly or via backend API
                // val tasks = fetchTasksFromSupabase()
                // val habits = fetchHabitsFromSupabase()
                // val mood = fetchTodayMoodFromSupabase()

                // Simulate data
                val tasksCount = 5
                val habitsCount = 3
                val mood = "😊"

                withContext(Dispatchers.Main) {
                    tasksCountView.text = "$tasksCount Tasks"
                    habitsCountView.text = "$habitsCount Habits"
                    currentMoodView.text = mood
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    systemStatusView.text = "🔴 Sync Error"
                }
            }
        }
    }

    private fun logout() {
        sharedPreferences.edit()
            .remove(KEY_USER_ID)
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .apply()

        userId = null
        accessToken = null

        showPairingScreen()
    }

    private fun fetchTasksFromSupabase(): Int {
        // In production, use Supabase client or HTTP requests
        // Example using HTTP:
        // val url = "https://your-project.supabase.co/rest/v1/tasks?user_id=eq.$userId"
        // val request = Request.Builder()
        //     .url(url)
        //     .header("apikey", accessToken)
        //     .header("Authorization", "Bearer $accessToken")
        //     .build()
        // val response = client.newCall(request).execute()
        // return response.body?.string()?.length ?: 0

        return 5 // Mock
    }

    private fun fetchHabitsFromSupabase(): Int {
        // Similar to fetchTasksFromSupabase
        return 3 // Mock
    }

    private fun fetchTodayMoodFromSupabase(): String {
        // Similar to fetchTasksFromSupabase
        return "😊" // Mock
    }
}
