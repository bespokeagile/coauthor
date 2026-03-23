/* Authors view -- author table from latest scan */

var AuthorsView = {
    _data: null,
    _sortCol: 'commit_count',
    _sortAsc: false,

    async render() {
        var app = document.getElementById('app');
        app.innerHTML = '<div class="loading">Loading authors...</div>';

        try {
            var data = await coauthorApi.getAuthors();
            AuthorsView._data = data;

            if (!data.authors || data.authors.length === 0) {
                app.innerHTML = '<div class="page-header"><h2>Authors</h2></div>'
                    + '<div class="empty-state"><h3>No author data</h3>'
                    + '<p>Run a scan first to see authorship analysis.</p>'
                    + '<a href="#/scan" class="btn btn-primary">Run Scan</a></div>';
                return;
            }

            AuthorsView._renderTable(app, data.authors);
        } catch (err) {
            app.innerHTML = '<div class="page-header"><h2>Authors</h2></div>'
                + '<div class="empty-state"><h3>Error loading authors</h3>'
                + '<p>' + err.message + '</p></div>';
        }
    },

    _renderTable(app, authors) {
        var sorted = AuthorsView._sortAuthors(authors);

        var html = '<div class="page-header"><h2>Authors</h2>'
            + '<p>' + authors.length + ' author' + (authors.length !== 1 ? 's' : '') + ' found</p></div>';

        // Build table with sortable headers
        html += '<table class="data-table"><thead><tr>';
        var cols = [
            { key: 'name', label: 'Name' },
            { key: 'email', label: 'Email' },
            { key: 'pattern', label: 'Pattern' },
            { key: 'commit_count', label: 'Commits' },
            { key: 'files_touched', label: 'Files' },
            { key: 'clusters', label: 'Clusters' },
            { key: 'primary_cluster', label: 'Primary Cluster' },
        ];

        cols.forEach(function(col) {
            var arrow = '';
            if (AuthorsView._sortCol === col.key) {
                arrow = AuthorsView._sortAsc ? ' \u25B2' : ' \u25BC';
            }
            html += '<th onclick="AuthorsView.sort(\'' + col.key + '\')">' + col.label + arrow + '</th>';
        });
        html += '</tr></thead><tbody>';

        sorted.forEach(function(author) {
            var patternBadge = Components.renderBadge(author.pattern || 'unknown', author.pattern || 'peripheral');
            var numClusters = author.clusters ? Object.keys(author.clusters).length : 0;

            html += '<tr>';
            html += '<td>' + (author.name || '-') + '</td>';
            html += '<td style="font-size:0.8rem;color:var(--text-secondary)">' + (author.email || '-') + '</td>';
            html += '<td>' + patternBadge + '</td>';
            html += '<td>' + (author.commit_count || 0) + '</td>';
            html += '<td>' + (author.files_touched || 0) + '</td>';
            html += '<td>' + numClusters + '</td>';
            html += '<td>' + (author.primary_cluster || '-') + '</td>';
            html += '</tr>';
        });

        html += '</tbody></table>';
        app.innerHTML = html;
    },

    sort(column) {
        if (AuthorsView._sortCol === column) {
            AuthorsView._sortAsc = !AuthorsView._sortAsc;
        } else {
            AuthorsView._sortCol = column;
            AuthorsView._sortAsc = true;
        }

        if (AuthorsView._data && AuthorsView._data.authors) {
            var app = document.getElementById('app');
            AuthorsView._renderTable(app, AuthorsView._data.authors);
        }
    },

    _sortAuthors(authors) {
        var col = AuthorsView._sortCol;
        var asc = AuthorsView._sortAsc;

        return authors.slice().sort(function(a, b) {
            var va = a[col];
            var vb = b[col];

            // Handle cluster count specially
            if (col === 'clusters') {
                va = a.clusters ? Object.keys(a.clusters).length : 0;
                vb = b.clusters ? Object.keys(b.clusters).length : 0;
            }

            if (va == null) va = '';
            if (vb == null) vb = '';

            if (typeof va === 'number' && typeof vb === 'number') {
                return asc ? va - vb : vb - va;
            }

            va = String(va).toLowerCase();
            vb = String(vb).toLowerCase();
            if (va < vb) return asc ? -1 : 1;
            if (va > vb) return asc ? 1 : -1;
            return 0;
        });
    }
};
