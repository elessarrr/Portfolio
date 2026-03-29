document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }

    const sidebar = document.getElementById('app-sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebarToggleLabel = document.getElementById('sidebar-toggle-label');
    const enableSidebar = !!document.querySelector('[data-enable-sidebar="true"]');
    if (enableSidebar && sidebar && sidebarToggleBtn && sidebarToggleLabel) {
        sidebar.classList.remove('hidden');
        sidebarToggleBtn.classList.remove('hidden');
        let collapsed = window.innerWidth < 1024;
        const applySidebarState = () => {
            if (collapsed) {
                sidebar.classList.add('hidden');
                sidebarToggleLabel.textContent = 'Show Filters';
            } else {
                sidebar.classList.remove('hidden');
                sidebarToggleLabel.textContent = 'Hide Filters';
            }
        };
        applySidebarState();
        sidebarToggleBtn.addEventListener('click', function() {
            collapsed = !collapsed;
            applySidebarState();
        });
    }

    const queryInput = document.getElementById('search-query-input');
    document.querySelectorAll('[data-query-shortcut]').forEach(function(button) {
        button.addEventListener('click', function() {
            if (!queryInput) {
                return;
            }
            queryInput.value = button.getAttribute('data-query-shortcut') || '';
            queryInput.dispatchEvent(new Event('keyup', { bubbles: true }));
        });
    });

    const filterForm = document.getElementById('incident-filter-form');
    const exportLink = document.getElementById('incident-export-link');
    const syncExportLink = () => {
        if (!filterForm || !exportLink) {
            return;
        }
        const url = new URL(exportLink.href, window.location.origin);
        url.search = '';
        const formData = new FormData(filterForm);
        formData.forEach((value, key) => {
            if (value) {
                url.searchParams.append(key, value.toString());
            }
        });
        exportLink.href = `${url.pathname}${url.search}`;
    };
    if (filterForm) {
        filterForm.addEventListener('change', syncExportLink);
        syncExportLink();
        document.body.addEventListener('htmx:afterSwap', function(event) {
            if (event.target && event.target.id === 'incident-list') {
                syncExportLink();
            }
        });
    }

    const analysisButton = document.getElementById('run-report-analysis');
    const analysisOutput = document.getElementById('analysis-output');
    if (analysisButton && analysisOutput) {
        analysisButton.addEventListener('click', async function() {
            const reportText = document.getElementById('analysis-report-text')?.value || '';
            const reportUrl = document.getElementById('analysis-report-url')?.value || '';
            const model = document.getElementById('analysis-model')?.value || 'gemini';
            analysisButton.disabled = true;
            analysisOutput.classList.remove('hidden');
            analysisOutput.textContent = 'Analyzing report...';
            try {
                const response = await fetch('/api/analyze-report', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        report_text: reportText,
                        report_url: reportUrl,
                        model: model
                    })
                });
                const data = await response.json();
                if (!response.ok) {
                    analysisOutput.textContent = data.details || data.error || 'Analysis failed.';
                    return;
                }
                const factors = Array.isArray(data.contributing_factors) ? data.contributing_factors.join(', ') : '';
                while (analysisOutput.firstChild) {
                    analysisOutput.removeChild(analysisOutput.firstChild);
                }

                const addRow = (label, value, className) => {
                    const row = document.createElement('div');
                    if (className) {
                        row.className = className;
                    }
                    const strong = document.createElement('strong');
                    strong.textContent = `${label}: `;
                    row.appendChild(strong);
                    row.appendChild(document.createTextNode(value));
                    analysisOutput.appendChild(row);
                };

                addRow('Root Cause', String(data.root_cause || 'Unavailable'), '');
                addRow('Contributing Factors', factors || 'None listed', 'mt-2');
                addRow('Summary', String(data.summary || ''), 'mt-2');

                const modelDiv = document.createElement('div');
                modelDiv.className = 'mt-2 text-xs text-gray-500';
                modelDiv.textContent = `Model: ${data.ai_model || 'unknown'}${data.cached ? ' (cached)' : ''}`;
                analysisOutput.appendChild(modelDiv);
            } catch (error) {
                analysisOutput.textContent = 'Analysis failed. Please try again.';
            } finally {
                analysisButton.disabled = false;
            }
        });
    }

    document.body.addEventListener('htmx:responseError', function(evt) {
        alert('An error occurred while processing your request. Please try again.');
        console.error('HTMX Error:', evt.detail.error);
    });
});
