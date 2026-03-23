/* App initialization -- route registration and global state */

const App = {
    toggleAlice() {
        if (window._alice) window._alice.toggle();
    },

    sendToAlice() {
        if (window._alice) window._alice.sendMessage();
    },

    aliceShortcut(text) {
        if (window._alice) window._alice.shortcut(text);
    },
};

(function() {
    'use strict';

    async function initApp() {
        // Fetch config and update version badge
        try {
            var config = await coauthorApi.getConfig();
            if (config && config.version) {
                var badge = document.getElementById('version-badge');
                if (badge) badge.textContent = 'v' + config.version;
            }

            // Show Alice panel if LLM key is configured
            if (config && config.llm_api_key_set) {
                var panel = document.getElementById('alice-panel');
                if (panel) {
                    panel.style.display = '';
                    if (window._alice) window._alice.init();
                }
            }
        } catch (e) {
            console.warn('Could not fetch config:', e);
        }

        // Register routes
        Router.on('/home', function() {
            if (typeof HomeView !== 'undefined') HomeView.render();
        });
        Router.on('/scan', function() {
            if (typeof ScanView !== 'undefined') ScanView.render();
        });
        Router.on('/authors', function() {
            if (typeof AuthorsView !== 'undefined') AuthorsView.render();
        });
        Router.on('/impact', function() {
            if (typeof ImpactView !== 'undefined') ImpactView.render();
        });
        Router.on('/history', function() {
            if (typeof HistoryView !== 'undefined') HistoryView.render();
        });
        Router.on('/settings', function() {
            if (typeof SettingsView !== 'undefined') SettingsView.render();
        });
    }

    // Wait for DOM, then init
    function boot() {
        initApp().then(function() {
            Router.start();
        }).catch(function(err) {
            console.error('App init failed:', err);
            Router.start();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
