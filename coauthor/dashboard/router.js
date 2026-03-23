/* Minimal hash-based SPA router for Coauthor */
const Router = {
    routes: {},
    currentRoute: null,
    _defaultRoute: '/home',

    on(path, handler) {
        this.routes[path] = handler;
    },

    navigate(path) {
        window.location.hash = path;
    },

    setDefaultRoute(path) {
        this._defaultRoute = path;
    },

    start() {
        const self = this;
        const handle = () => {
            const rawHash = window.location.hash.slice(1) || self._defaultRoute;
            const hash = rawHash.split('?')[0];
            const parts = hash.split('/').filter(Boolean);
            const route = '/' + (parts[0] || 'home');
            const params = parts.slice(1);

            // Update active nav link
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.toggle('active', link.dataset.route === parts[0]);
            });

            const handler = self.routes[route];
            if (handler) {
                self.currentRoute = route;
                try {
                    const result = handler(params);
                    if (result && typeof result.catch === 'function') {
                        result.catch(err => {
                            console.error('View error:', err);
                            const app = document.getElementById('app');
                            if (app) app.innerHTML = '<div class="empty-state"><h3>Something went wrong</h3><p>' + err.message + '</p></div>';
                        });
                    }
                } catch (err) {
                    console.error('View error:', err);
                    const app = document.getElementById('app');
                    if (app) app.innerHTML = '<div class="empty-state"><h3>Something went wrong</h3><p>' + err.message + '</p></div>';
                }
            } else if (self.routes[self._defaultRoute]) {
                self.currentRoute = self._defaultRoute;
                self.routes[self._defaultRoute]([]);
            }
        };

        window.addEventListener('hashchange', handle);
        handle();
    },

    getParams() {
        const hash = window.location.hash.slice(1) || this._defaultRoute;
        return hash.split('?')[0].split('/').filter(Boolean).slice(1);
    }
};
