package ai.rastro.watch;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.widget.Button;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity {

    private static final String API_BASE = "http://10.0.2.2:8000";
    private static final String PREFS = "ownex_watch_prefs";
    private static final String KEY_THEME = "theme_index";

    // Acentos disponibles (Emerald, Cyan, Amber, Violet)
    private static final int[][] THEMES = {
        {Color.parseColor("#00E39A"), Color.parseColor("#00D5FF"), Color.parseColor("#FF7A1A"), Color.parseColor("#A855F7")},
    };
    private static final int[] THEME_COLORS = {
        Color.parseColor("#00E39A"),
        Color.parseColor("#00D5FF"),
        Color.parseColor("#FF7A1A"),
        Color.parseColor("#A855F7"),
    };
    private static final String[] THEME_NAMES = {"Emerald", "Cyan", "Amber", "Violet"};

    private TextView statusText;
    private TextView notificationsText;
    private TextView earningsText;
    private TextView themeLabel;
    private Button refreshButton;
    private Button approveButton;
    private Button themeButton;
    private int themeIndex = 0;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        themeIndex = prefs.getInt(KEY_THEME, 0);

        statusText = findViewById(R.id.status_text);
        notificationsText = findViewById(R.id.notifications_text);
        earningsText = findViewById(R.id.earnings_text);
        themeLabel = findViewById(R.id.theme_label);
        refreshButton = findViewById(R.id.btn_refresh);
        approveButton = findViewById(R.id.btn_approve);
        themeButton = findViewById(R.id.btn_theme);

        applyTheme();

        refreshButton.setOnClickListener(v -> refreshStatus());
        approveButton.setOnClickListener(v -> approveLatestAction());
        themeButton.setOnClickListener(v -> {
            themeIndex = (themeIndex + 1) % THEME_COLORS.length;
            prefs.edit().putInt(KEY_THEME, themeIndex).apply();
            applyTheme();
        });

        refreshStatus();
    }

    private void applyTheme() {
        int accent = THEME_COLORS[themeIndex];
        String name = THEME_NAMES[themeIndex];
        themeLabel.setText("Tema: " + name);
        themeLabel.setTextColor(accent);
        approveButton.setBackgroundColor(accent);
        themeButton.setBackgroundColor(accent);
        themeButton.setTextColor(Color.BLACK);
        statusText.setBackgroundColor(Color.parseColor("#1a1a1a"));
        notificationsText.setBackgroundColor(Color.parseColor("#1a1a1a"));
        earningsText.setBackgroundColor(Color.parseColor("#1a1a1a"));
    }

    private void refreshStatus() {
        executor.execute(() -> {
            try {
                String status = apiGet("/wear-os/status");
                String actions = apiGet("/api/notifications/pending-actions");
                String earnings = apiGet("/direct-work/max-daily-income");

                mainHandler.post(() -> {
                    statusText.setText(parseStatus(status));
                    notificationsText.setText(parseActions(actions));
                    earningsText.setText(parseEarnings(earnings));
                });
            } catch (Exception e) {
                mainHandler.post(() -> statusText.setText("Error: " + e.getMessage()));
            }
        });
    }

    private void approveLatestAction() {
        executor.execute(() -> {
            try {
                String actions = apiGet("/api/notifications/pending-actions");
                JSONObject json = new JSONObject(actions);
                JSONArray arr = json.optJSONArray("data");
                if (arr != null && arr.length() > 0) {
                    JSONObject first = arr.getJSONObject(0);
                    String actionId = first.optString("action_id", "");
                    if (!actionId.isEmpty()) {
                        apiPost("/api/notifications/actions/" + actionId + "/resolve", "{}");
                        mainHandler.post(() -> {
                            notificationsText.setText("Action resolved!");
                            refreshStatus();
                        });
                    }
                }
            } catch (Exception e) {
                mainHandler.post(() -> notificationsText.setText("Error: " + e.getMessage()));
            }
        });
    }

    private String apiGet(String path) throws Exception {
        URL url = new URL(API_BASE + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(5000);

        BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) sb.append(line);
        reader.close();
        return sb.toString();
    }

    private String apiPost(String path, String body) throws Exception {
        URL url = new URL(API_BASE + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setDoOutput(true);
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(5000);

        conn.getOutputStream().write(body.getBytes());
        BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) sb.append(line);
        reader.close();
        return sb.toString();
    }

    private String parseStatus(String json) {
        try {
            JSONObject obj = new JSONObject(json);
            JSONObject data = obj.optJSONObject("data");
            if (data == null) return "No status";
            return String.format("System: %s\nWorkflows: %d\nPending: %d\nHealth: %.0f%%",
                    data.optBoolean("system_online", false) ? "Online" : "Offline",
                    data.optInt("active_workflows", 0),
                    data.optInt("pending_approvals", 0),
                    data.optDouble("health_score", 0));
        } catch (Exception e) {
            return "Parse error";
        }
    }

    private String parseActions(String json) {
        try {
            JSONObject obj = new JSONObject(json);
            JSONArray arr = obj.optJSONArray("data");
            if (arr == null || arr.length() == 0) return "No pending actions";
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < Math.min(arr.length(), 3); i++) {
                JSONObject a = arr.getJSONObject(i);
                sb.append("- ").append(a.optString("title", "Unknown")).append("\n");
            }
            return sb.toString();
        } catch (Exception e) {
            return "No actions";
        }
    }

    private String parseEarnings(String json) {
        try {
            JSONObject obj = new JSONObject(json);
            JSONObject data = obj.optJSONObject("data");
            if (data == null) return "No data";
            return String.format("Optimistic: $%.0f\nRealistic: $%.0f\nConservative: $%.0f",
                    data.optDouble("optimistic_max_usd", 0),
                    data.optDouble("realistic_max_usd", 0),
                    data.optDouble("conservative_max_usd", 0));
        } catch (Exception e) {
            return "No data";
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdown();
    }
}
