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
    const debounce = function(callback, delayMs) {
        let timeoutId = null;
        return function(...args) {
            if (timeoutId) {
                window.clearTimeout(timeoutId);
            }
            timeoutId = window.setTimeout(() => callback.apply(this, args), delayMs);
        };
    };
    if (queryInput) {
        let autocompleteResults = [];
        const autocompleteContainer = queryInput.closest('.relative') || queryInput.parentElement;
        const autocompleteDropdown = document.createElement('ul');
        autocompleteDropdown.id = 'search-autocomplete-dropdown';
        autocompleteDropdown.className = 'search-autocomplete-dropdown hidden';
        if (autocompleteContainer) {
            autocompleteContainer.appendChild(autocompleteDropdown);
        }

        const closeAutocompleteDropdown = function() {
            autocompleteDropdown.classList.add('hidden');
        };

        const renderAutocompleteDropdown = function(results) {
            autocompleteDropdown.innerHTML = '';
            if (!results.length) {
                closeAutocompleteDropdown();
                return;
            }

            results.forEach(function(result) {
                const item = document.createElement('li');
                item.className = 'search-autocomplete-item';
                item.setAttribute('data-aircraft-id', String(result.id || ''));
                item.textContent = result.make_model || result.full_name || 'Unknown aircraft';
                autocompleteDropdown.appendChild(item);
            });

            autocompleteDropdown.classList.remove('hidden');
        };

        autocompleteDropdown.addEventListener('click', function(event) {
            const item = event.target.closest('[data-aircraft-id]');
            if (!item) {
                return;
            }
            const aircraftId = item.getAttribute('data-aircraft-id');
            if (!aircraftId) {
                return;
            }
            closeAutocompleteDropdown();
            window.location.assign(`/aircraft/${encodeURIComponent(aircraftId)}`);
        });

        const fetchAutocompleteResults = async function(query) {
            const response = await window.fetch(`/api/search/autocomplete?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`Autocomplete request failed: ${response.status}`);
            }
            const payload = await response.json();
            return Array.isArray(payload.results) ? payload.results : [];
        };

        const handleAutocompleteInput = debounce(async function(event) {
            const currentQuery = event.target.value || '';
            if (currentQuery.length < 2) {
                autocompleteResults = [];
                renderAutocompleteDropdown([]);
                return;
            }

            try {
                autocompleteResults = await fetchAutocompleteResults(currentQuery);
            } catch (error) {
                autocompleteResults = [];
                console.error('Autocomplete fetch failed:', error);
            }

            renderAutocompleteDropdown(autocompleteResults);
        }, 200);
        queryInput.addEventListener('input', handleAutocompleteInput);

        queryInput.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeAutocompleteDropdown();
            }
        });
        queryInput.addEventListener('blur', function() {
            // Delay to allow dropdown item clicks to process first.
            window.setTimeout(closeAutocompleteDropdown, 120);
        });
        document.addEventListener('click', function(event) {
            const clickInsideAutocomplete = autocompleteContainer && autocompleteContainer.contains(event.target);
            if (!clickInsideAutocomplete) {
                closeAutocompleteDropdown();
            }
        });
    }
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
