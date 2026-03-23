/* Settings view -- configuration display */

var SettingsView = {
    async render() {
        var app = document.getElementById('app');
        app.innerHTML = '<div class="loading">Loading settings...</div>';

        try {
            var config = await coauthorApi.getConfig();

            var html = '<div class="page-header"><h2>Settings</h2>'
                + '<p>Coauthor configuration and status.</p></div>';

            html += '<div style="max-width:500px">';

            // Version
            html += '<div class="card" style="margin-bottom:16px">'
                + '<div class="card-title">Version</div>'
                + '<div class="card-value" style="font-size:1.1rem">' + (config.version || 'unknown') + '</div>'
                + '</div>';

            // LLM status
            var llmStatus = config.llm_api_key_set
                ? '<span class="status-dot green"></span>Configured (' + (config.llm_provider || 'unknown') + ')'
                : '<span class="status-dot red"></span>Not configured';

            html += '<div class="card" style="margin-bottom:16px">'
                + '<div class="card-title">LLM API Key</div>'
                + '<div style="margin-top:8px;font-size:0.88rem">' + llmStatus + '</div>'
                + '<div class="card-sub">Set ANTHROPIC_API_KEY or OPENAI_API_KEY for semantic analysis and Alice features.</div>'
                + '</div>';

            // Data directory
            html += '<div class="card" style="margin-bottom:16px">'
                + '<div class="card-title">Data Directory</div>'
                + '<div style="margin-top:8px;font-size:0.88rem"><code>~/.coauthor/</code></div>'
                + '<div class="card-sub">Scan results are stored in scans.db within this directory.</div>'
                + '</div>';

            // Health check
            try {
                var health = await coauthorApi.getHealth();
                html += '<div class="card" style="margin-bottom:16px">'
                    + '<div class="card-title">Server Status</div>'
                    + '<div style="margin-top:8px;font-size:0.88rem"><span class="status-dot green"></span>'
                    + (health.status || 'ok') + '</div>'
                    + '</div>';
            } catch (e) {
                html += '<div class="card" style="margin-bottom:16px">'
                    + '<div class="card-title">Server Status</div>'
                    + '<div style="margin-top:8px;font-size:0.88rem"><span class="status-dot red"></span>Unreachable</div>'
                    + '</div>';
            }

            html += '</div>';
            app.innerHTML = html;
        } catch (err) {
            app.innerHTML = '<div class="page-header"><h2>Settings</h2></div>'
                + '<div class="empty-state"><h3>Error loading settings</h3>'
                + '<p>' + err.message + '</p></div>';
        }
    }
};
