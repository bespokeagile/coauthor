/* Home view -- summary dashboard from latest scan */

var HomeView = {
    async render() {
        var app = document.getElementById('app');
        app.innerHTML = '<div class="loading">Loading dashboard...</div>';

        try {
            var scans = await coauthorApi.getScans(1);

            if (!scans || scans.length === 0) {
                app.innerHTML = '<div class="page-header"><h2>Welcome to Coauthor</h2>'
                    + '<p>Code authorship analysis for your git repositories.</p></div>'
                    + '<div class="empty-state">'
                    + '<h3>No scans yet</h3>'
                    + '<p>Run your first scan to see authorship insights for your codebase.</p>'
                    + '<a href="#/scan" class="btn btn-primary">Run First Scan</a>'
                    + '</div>';
                return;
            }

            // Load full report from latest scan
            var latest = scans[0];
            var report = await coauthorApi.getScan(latest.id);

            if (report.status === 'running') {
                app.innerHTML = '<div class="page-header"><h2>Dashboard</h2></div>'
                    + '<div class="scan-progress"><span class="spinner"></span> Scan in progress...</div>';
                return;
            }

            var summary = report.summary || {};
            var authorship = report.authorship || {};
            var repoName = (report.target || latest.repo_path || '').split('/').pop() || 'Repository';

            // Build cards
            var html = '<div class="page-header"><h2>Dashboard</h2>'
                + '<p>Latest scan: <strong>' + repoName + '</strong>'
                + ' at ' + (report.commit_sha || '').substring(0, 8)
                + '</p></div>';

            html += '<div class="cards-grid">';
            html += Components.renderCard('Total Authors', summary.total_authors || 0);
            html += Components.renderCard('Total Commits', summary.total_commits || 0);

            // Team composition
            var comp = [];
            if (summary.specialists) comp.push(summary.specialists + ' specialist' + (summary.specialists > 1 ? 's' : ''));
            if (summary.generalists) comp.push(summary.generalists + ' generalist' + (summary.generalists > 1 ? 's' : ''));
            if (summary.hubs) comp.push(summary.hubs + ' hub' + (summary.hubs > 1 ? 's' : ''));
            var compText = comp.length ? comp.join(', ') : 'N/A';
            html += Components.renderCard('Team Composition', (summary.total_authors || 0), compText);

            html += Components.renderCard('Top Contributor', summary.top_contributor || 'N/A');
            html += '</div>';

            // Clusters summary
            var clusters = authorship.clusters || {};
            var clusterNames = Object.keys(clusters);
            if (clusterNames.length > 0) {
                html += '<div class="page-header" style="margin-top:24px"><h2>Code Clusters</h2>'
                    + '<p>' + clusterNames.length + ' cluster' + (clusterNames.length > 1 ? 's' : '') + ' detected</p></div>';

                var headers = ['Cluster', 'Files', 'Authors', 'Top Author'];
                var rows = clusterNames.slice(0, 15).map(function(name) {
                    var c = clusters[name];
                    return [name, c.files || 0, c.authors || 0, c.top_author || '-'];
                });
                html += Components.renderTable(headers, rows);
            }

            app.innerHTML = html;
        } catch (err) {
            console.error('Home view error:', err);
            app.innerHTML = '<div class="page-header"><h2>Dashboard</h2></div>'
                + '<div class="empty-state"><h3>Could not load data</h3>'
                + '<p>' + (err.message || 'Unknown error') + '</p>'
                + '<a href="#/scan" class="btn btn-primary">Run a Scan</a></div>';
        }
    }
};
