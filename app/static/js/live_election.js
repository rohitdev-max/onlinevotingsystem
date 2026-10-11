document.addEventListener('DOMContentLoaded', () => {
    const electionPanels = Array.from(document.querySelectorAll('[data-live-election]'));
    const numberFormat = new Intl.NumberFormat();

    const animateNumber = (element, targetValue) => {
        const startValue = Number(element.dataset.currentValue || 0);
        const endValue = Number(targetValue);
        element.dataset.currentValue = String(endValue);
        if (startValue === endValue) {
            element.textContent = numberFormat.format(endValue);
            return;
        }

        const startedAt = performance.now();
        const duration = 350;
        const animate = (now) => {
            const progress = Math.min((now - startedAt) / duration, 1);
            const value = Math.round(startValue + (endValue - startValue) * progress);
            element.textContent = numberFormat.format(value);
            if (progress < 1) window.requestAnimationFrame(animate);
        };
        window.requestAnimationFrame(animate);
    };

    const renderParticipation = (panel, entries) => {
        const graph = panel.querySelector('[data-live-graph]');
        if (!graph || !Array.isArray(entries)) return;

        const maxVotes = Math.max(1, ...entries.map((entry) => Number(entry.votes) || 0));
        const columns = entries.map((entry, index) => {
            const column = document.createElement('div');
            column.className = 'live-graph-column';
            column.title = `${entry.label}: ${numberFormat.format(entry.votes)} votes`;
            column.setAttribute('aria-label', column.title);

            const bar = document.createElement('span');
            bar.className = 'live-graph-bar';
            const votes = Number(entry.votes) || 0;
            bar.style.height = `${votes ? Math.max(4, votes / maxVotes * 100) : 0}%`;
            column.append(bar);

            if (index === 0 || index === Math.floor(entries.length / 2) || index === entries.length - 1) {
                const label = document.createElement('span');
                label.className = 'live-graph-label';
                label.textContent = entry.label;
                column.append(label);
            }
            return column;
        });
        graph.replaceChildren(...columns);
    };

    const updatePanel = async (panel) => {
        if (document.hidden || panel.dataset.loading === 'true') return;
        panel.dataset.loading = 'true';
        try {
            const response = await fetch(panel.dataset.liveUrl, {
                headers: { Accept: 'application/json' },
                cache: 'no-store',
                credentials: 'same-origin',
            });
            if (!response.ok) throw new Error('Live election data is unavailable.');
            const stats = await response.json();

            ['totalVerifiedVoters', 'votesCast', 'remainingVoters', 'auditedVotes'].forEach((key) => {
                panel.querySelectorAll(`[data-live-stat="${key}"]`).forEach((element) => {
                    animateNumber(element, stats[key] || 0);
                });
            });
            const turnout = Math.max(0, Math.min(100, Number(stats.turnoutPercentage) || 0));
            panel.querySelectorAll('[data-live-stat="turnoutPercentage"]').forEach((element) => {
                element.textContent = turnout.toFixed(1);
            });

            const status = panel.querySelector('[data-live-stat="electionStatus"]');
            if (status) {
                status.textContent = stats.electionStatus;
                status.classList.remove('status-open', 'status-scheduled', 'status-closed', 'status-results-published', 'status-live', 'status-upcoming', 'status-ended');
                status.classList.add(`status-${stats.electionStatus.toLowerCase()}`);
            }
            const progressTrack = panel.querySelector('[data-live-progress-track]');
            if (progressTrack) progressTrack.setAttribute('aria-valuenow', turnout.toFixed(1));
            const progress = panel.querySelector('[data-live-progress]');
            if (progress) progress.style.width = `${turnout}%`;

            const updated = panel.querySelector('[data-live-stat="lastUpdated"]');
            if (updated) updated.textContent = new Date(stats.lastUpdated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const auditStatus = panel.querySelector('[data-live-stat="auditStatus"]');
            if (auditStatus) auditStatus.textContent = stats.auditStatus;
            renderParticipation(panel, stats.participation);
            panel.dataset.lastError = '';
        } catch (error) {
            panel.dataset.lastError = error.message;
            const updated = panel.querySelector('[data-live-stat="lastUpdated"]');
            if (updated) updated.textContent = 'Live update unavailable; retrying';
        } finally {
            panel.dataset.loading = 'false';
        }
    };

    const refreshAll = () => electionPanels.forEach(updatePanel);
    refreshAll();
    window.setInterval(refreshAll, 5000);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) refreshAll();
    });
});