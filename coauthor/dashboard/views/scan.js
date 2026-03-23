/* Scan view -- form to trigger a new authorship scan */

var ScanView = {
    _pollTimer: null,

    render() {
        var app = document.getElementById('app');

        var html = '<div class="page-header"><h2>New Scan</h2>'
            + '<p>Analyze authorship patterns in a git repository.</p></div>';

        html += '<div style="max-width:500px">';
        html += '<div class="form-group">'
            + '<label class="form-label" for="scan-target">Repository Path</label>'
            + '<input class="form-input" id="scan-target" type="text" placeholder="/path/to/your/repo">'
            + '</div>';

        html += '<div class="form-group">'
            + '<label class="form-label" for="scan-max-commits">Max Commits</label>'
            + '<input class="form-input" id="scan-max-commits" type="number" value="0" min="0" placeholder="0 = all commits">'
            + '<div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">0 means analyze all commits.</div>'
            + '</div>';

        html += '<div class="form-group">'
            + '<label class="form-check">'
            + '<input type="checkbox" id="scan-exclude-bots" checked> Exclude bot commits'
            + '</label>'
            + '</div>';

        html += '<div style="margin-top:20px">'
            + '<button class="btn btn-primary" id="scan-submit" onclick="ScanView.startScan()">Start Scan</button>'
            + '</div>';
        html += '</div>';

        html += '<div id="scan-status" style="margin-top:24px"></div>';

        app.innerHTML = html;
    },

    async startScan() {
        var target = document.getElementById('scan-target').value.trim();
        if (!target) {
            document.getElementById('scan-status').innerHTML =
                '<div style="color:var(--badge-red)">Please enter a repository path.</div>';
            return;
        }

        var maxCommits = parseInt(document.getElementById('scan-max-commits').value) || 0;
        var excludeBots = document.getElementById('scan-exclude-bots').checked;

        var submitBtn = document.getElementById('scan-submit');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Scanning...';

        var statusEl = document.getElementById('scan-status');
        statusEl.innerHTML = '<div class="scan-progress"><span class="spinner"></span> Analyzing repository...</div>';

        try {
            var result = await coauthorApi.startScan(target, {
                max_commits: maxCommits,
                exclude_bots: excludeBots,
            });

            if (result.scan_id) {
                ScanView._pollForCompletion(result.scan_id, statusEl, submitBtn);
            }
        } catch (err) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Scan';
            statusEl.innerHTML = '<div style="color:var(--badge-red)">Scan failed: '
                + (err.body && err.body.error ? err.body.error : err.message) + '</div>';
        }
    },

    _pollForCompletion(scanId, statusEl, submitBtn) {
        var attempts = 0;
        var maxAttempts = 120; // 2 minutes at 1s intervals

        function poll() {
            attempts++;
            coauthorApi.getScan(scanId).then(function(data) {
                if (data.status === 'running') {
                    if (attempts < maxAttempts) {
                        ScanView._pollTimer = setTimeout(poll, 1000);
                    } else {
                        statusEl.innerHTML = '<div style="color:var(--badge-yellow)">Scan is taking longer than expected. Check the History tab.</div>';
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Start Scan';
                    }
                } else if (data.status === 'error') {
                    statusEl.innerHTML = '<div style="color:var(--badge-red)">Scan failed: ' + (data.error || 'Unknown error') + '</div>';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Start Scan';
                } else {
                    // Complete -- navigate to authors view
                    statusEl.innerHTML = '<div style="color:var(--badge-green)">Scan complete! Redirecting...</div>';
                    setTimeout(function() {
                        window.location.hash = '#/authors';
                    }, 500);
                }
            }).catch(function() {
                if (attempts < maxAttempts) {
                    ScanView._pollTimer = setTimeout(poll, 2000);
                }
            });
        }

        poll();
    }
};
