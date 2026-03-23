/* History view -- list of past scans */

var HistoryView = {
    async render() {
        var app = document.getElementById('app');
        app.innerHTML = '<div class="loading">Loading scan history...</div>';

        try {
            var scans = await coauthorApi.getScans(50);

            var html = '<div class="page-header"><h2>Scan History</h2>'
                + '<p>' + (scans.length || 0) + ' scan' + (scans.length !== 1 ? 's' : '') + ' recorded</p></div>';

            if (!scans || scans.length === 0) {
                html += '<div class="empty-state"><h3>No scans yet</h3>'
                    + '<p>Run your first scan to start tracking authorship patterns.</p>'
                    + '<a href="#/scan" class="btn btn-primary">Run Scan</a></div>';
                app.innerHTML = html;
                return;
            }

            html += '<table class="data-table"><thead><tr>'
                + '<th>ID</th>'
                + '<th>Repository</th>'
                + '<th>Commit</th>'
                + '<th>Date</th>'
                + '</tr></thead><tbody>';

            scans.forEach(function(scan) {
                var repoName = (scan.repo_path || '').split('/').pop() || scan.repo_path || '-';
                var sha = (scan.commit_sha || '').substring(0, 8);
                var date = scan.created_at || '-';
                // Format date if ISO
                try {
                    if (date !== '-') {
                        var d = new Date(date);
                        date = d.toLocaleDateString() + ' ' + d.toLocaleTimeString();
                    }
                } catch (e) { /* keep raw */ }

                html += '<tr style="cursor:pointer" onclick="HistoryView.loadScan(\'' + scan.id + '\')">';
                html += '<td><code style="font-size:0.82rem;color:var(--accent)">' + scan.id + '</code></td>';
                html += '<td>' + repoName + '</td>';
                html += '<td><code style="font-size:0.82rem">' + sha + '</code></td>';
                html += '<td style="color:var(--text-secondary)">' + date + '</td>';
                html += '</tr>';
            });

            html += '</tbody></table>';
            app.innerHTML = html;
        } catch (err) {
            app.innerHTML = '<div class="page-header"><h2>Scan History</h2></div>'
                + '<div class="empty-state"><h3>Error loading history</h3>'
                + '<p>' + err.message + '</p></div>';
        }
    },

    async loadScan(scanId) {
        // Navigate to a scan detail -- for now, show authors from that scan
        var app = document.getElementById('app');
        app.innerHTML = '<div class="loading">Loading scan...</div>';

        try {
            var report = await coauthorApi.getScan(scanId);
            var authorship = report.authorship || {};
            var authors = authorship.authors || [];
            var summary = report.summary || {};
            var repoName = (report.target || '').split('/').pop() || 'Repository';

            var html = '<div class="page-header"><h2>Scan: ' + repoName + '</h2>'
                + '<p>Commit: ' + (report.commit_sha || '').substring(0, 8)
                + ' | Authors: ' + (summary.total_authors || 0)
                + ' | Commits: ' + (summary.total_commits || 0) + '</p></div>';

            html += '<div style="margin-bottom:16px"><a href="#/history" class="btn btn-secondary">Back to History</a></div>';

            if (authors.length > 0) {
                var headers = ['Name', 'Email', 'Pattern', 'Commits', 'Files', 'Primary Cluster'];
                var rows = authors.map(function(a) {
                    return [
                        a.name || '-',
                        a.email || '-',
                        Components.renderBadge(a.pattern || 'unknown', a.pattern || 'peripheral'),
                        a.commit_count || 0,
                        a.files_touched || 0,
                        a.primary_cluster || '-',
                    ];
                });
                html += Components.renderTable(headers, rows);
            } else {
                html += '<div class="empty-state"><p>No author data in this scan.</p></div>';
            }

            app.innerHTML = html;
        } catch (err) {
            app.innerHTML = '<div class="page-header"><h2>Scan Detail</h2></div>'
                + '<div class="empty-state"><h3>Error loading scan</h3>'
                + '<p>' + err.message + '</p></div>';
        }
    }
};
