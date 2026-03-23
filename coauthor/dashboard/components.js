/* Shared UI helper components for Coauthor dashboard */

const Components = {
    /**
     * Render an HTML table from headers and row data.
     * @param {string[]} headers - Column header labels.
     * @param {string[][]} rows - Array of row arrays (each cell is an HTML string).
     * @returns {string} HTML table string.
     */
    renderTable(headers, rows) {
        let html = '<table class="data-table"><thead><tr>';
        headers.forEach(function(h) {
            html += '<th>' + h + '</th>';
        });
        html += '</tr></thead><tbody>';
        if (rows.length === 0) {
            html += '<tr><td colspan="' + headers.length + '" style="text-align:center;color:var(--text-muted)">No data available</td></tr>';
        } else {
            rows.forEach(function(row) {
                html += '<tr>';
                row.forEach(function(cell) {
                    html += '<td>' + cell + '</td>';
                });
                html += '</tr>';
            });
        }
        html += '</tbody></table>';
        return html;
    },

    /**
     * Render a summary card.
     * @param {string} title - Card title (small label).
     * @param {string|number} value - Main value to display.
     * @param {string} [sub] - Optional subtitle text.
     * @returns {string} HTML card div.
     */
    renderCard(title, value, sub) {
        let html = '<div class="card">';
        html += '<div class="card-title">' + title + '</div>';
        html += '<div class="card-value">' + value + '</div>';
        if (sub) {
            html += '<div class="card-sub">' + sub + '</div>';
        }
        html += '</div>';
        return html;
    },

    /**
     * Render a colored badge.
     * @param {string} text - Badge label.
     * @param {string} type - Badge type: specialist, generalist, hub, peripheral, critical, moderate, healthy.
     * @returns {string} HTML badge span.
     */
    renderBadge(text, type) {
        type = type || 'peripheral';
        return '<span class="badge badge-' + type + '">' + text + '</span>';
    },
};
