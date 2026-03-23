/* Impact view -- high-impact commits from latest scan */

var ImpactView = {
    async render() {
        var app = document.getElementById('app');
        app.innerHTML = '<div class="loading">Loading impact data...</div>';

        try {
            var data = await coauthorApi.getImpacts();
            var commits = data.commits || [];

            if (commits.length === 0) {
                app.innerHTML = '<div class="page-header"><h2>Impact</h2></div>'
                    + '<div class="empty-state"><h3>No impact data</h3>'
                    + '<p>Run a scan first to see commit impact analysis.</p>'
                    + '<a href="#/scan" class="btn btn-primary">Run Scan</a></div>';
                return;
            }

            // Sort by impact score descending, take top 20
            commits.sort(function(a, b) {
                return (b.structural_impact || 0) - (a.structural_impact || 0);
            });
            var top = commits.slice(0, 20);

            var html = '<div class="page-header"><h2>Impact</h2>'
                + '<p>Top ' + top.length + ' commits by structural impact (of ' + commits.length + ' total)</p></div>';

            html += '<table class="data-table"><thead><tr>'
                + '<th>Hash</th>'
                + '<th>Author</th>'
                + '<th>Impact Score</th>'
                + '<th>Files Changed</th>'
                + '<th>Clusters</th>'
                + '<th>Message</th>'
                + '</tr></thead><tbody>';

            top.forEach(function(c) {
                var hash = (c.hash || '').substring(0, 8);
                var impact = (c.structural_impact || 0).toFixed(2);
                var filesChanged = c.files_changed || 0;
                var clusters = c.clusters_touched || 0;
                var msg = c.message || '';
                // Truncate long messages
                if (msg.length > 60) msg = msg.substring(0, 57) + '...';
                // Escape HTML
                msg = msg.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                var author = c.author_name || c.author_email || '-';

                // Color impact score
                var impactClass = 'healthy';
                var impactNum = parseFloat(impact);
                if (impactNum > 5) impactClass = 'critical';
                else if (impactNum > 2) impactClass = 'moderate';

                html += '<tr>';
                html += '<td><code style="font-size:0.82rem;color:var(--accent)">' + hash + '</code></td>';
                html += '<td>' + author + '</td>';
                html += '<td>' + Components.renderBadge(impact, impactClass) + '</td>';
                html += '<td>' + filesChanged + '</td>';
                html += '<td>' + clusters + '</td>';
                html += '<td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + msg + '</td>';
                html += '</tr>';
            });

            html += '</tbody></table>';
            app.innerHTML = html;
        } catch (err) {
            app.innerHTML = '<div class="page-header"><h2>Impact</h2></div>'
                + '<div class="empty-state"><h3>Error loading impact data</h3>'
                + '<p>' + err.message + '</p></div>';
        }
    }
};
