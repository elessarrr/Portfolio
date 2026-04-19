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

    document.body.addEventListener('click', function(event) {
        const toggle = event.target.closest('[data-read-more-toggle]');
        if (!toggle) {
            return;
        }
        const targetId = toggle.getAttribute('data-read-more-toggle');
        if (!targetId) {
            return;
        }
        const description = document.getElementById(targetId);
        if (!description) {
            return;
        }

        const isCollapsed = description.classList.contains('line-clamp-3');
        if (isCollapsed) {
            description.classList.remove('line-clamp-3');
            toggle.textContent = 'Read less';
            toggle.setAttribute('aria-expanded', 'true');
        } else {
            description.classList.add('line-clamp-3');
            toggle.textContent = 'Read more';
            toggle.setAttribute('aria-expanded', 'false');
        }
    });

    const toastContainer = document.getElementById('toast-container');
    const showErrorToast = function(message) {
        if (!toastContainer) {
            return;
        }

        toastContainer.classList.remove('hidden');
        const toast = document.createElement('div');
        toast.className = 'max-w-sm rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-md';
        toast.textContent = message || 'An unexpected error occurred. Please try again.';
        toastContainer.appendChild(toast);

        window.setTimeout(function() {
            toast.remove();
            if (!toastContainer.children.length) {
                toastContainer.classList.add('hidden');
            }
        }, 4500);
    };

    document.body.addEventListener('htmx:responseError', function(evt) {
        showErrorToast('Failed to process request. Please try again.');
        console.error('HTMX responseError:', evt.detail.error);
    });

    document.body.addEventListener('htmx:sendError', function(evt) {
        showErrorToast('Network error while sending request. Please check your connection.');
        console.error('HTMX sendError:', evt.detail.error);
    });
});
