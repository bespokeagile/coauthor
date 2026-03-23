/* API client for Coauthor REST endpoints */
const coauthorApi = {
    async _fetch(path, opts) {
        opts = opts || {};
        const resp = await fetch(path, opts);
        if (!resp.ok) {
            const err = new Error(resp.statusText || 'Request failed');
            err.status = resp.status;
            try {
                err.body = await resp.json();
            } catch (e) { /* ignore */ }
            throw err;
        }
        return resp.json();
    },

    getHealth() {
        return this._fetch('/health');
    },

    getConfig() {
        return this._fetch('/config');
    },

    getScans(limit) {
        limit = limit || 20;
        return this._fetch('/scans?limit=' + limit);
    },

    getScan(id) {
        return this._fetch('/scan/' + id);
    },

    getAuthors() {
        return this._fetch('/authors');
    },

    getImpacts() {
        return this._fetch('/impacts');
    },

    startScan(target, opts) {
        opts = opts || {};
        return this._fetch('/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target: target,
                max_commits: opts.max_commits || 0,
                exclude_bots: opts.exclude_bots !== false,
            }),
        });
    },

    sendAliceMessage(message) {
        return this._fetch('/alice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message }),
        });
    },
};
