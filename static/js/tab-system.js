/**
 * Salesforce-style Tab System
 * Manages tabs across the entire application using session storage
 */

class TabSystem {
    constructor() {
        this.tabs = this.loadTabs();
        this.activeTabId = this.getActiveTabId();
        this.init();
    }

    init() {
        this.createTabBar();
        this.bindEvents();
        this.updateActiveTab();
    }

    loadTabs() {
        const saved = sessionStorage.getItem('sf-tabs');
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch (e) {
                console.error('Error loading tabs:', e);
            }
        }
        return [];
    }

    saveTabs() {
        sessionStorage.setItem('sf-tabs', JSON.stringify(this.tabs));
        sessionStorage.setItem('sf-active-tab', this.activeTabId);
    }

    getActiveTabId() {
        return sessionStorage.getItem('sf-active-tab') || null;
    }

    addTab(id, title, url, icon = null) {
        // Check if tab already exists
        const existingTab = this.tabs.find(tab => tab.id === id);
        if (existingTab) {
            this.setActiveTab(id);
            return;
        }

        // Add new tab
        const tab = {
            id: id,
            title: title,
            url: url,
            icon: icon,
            closable: id !== 'home'
        };

        this.tabs.push(tab);
        this.setActiveTab(id);
        this.saveTabs();
        this.renderTabs();
    }

    removeTab(id) {
        if (id === 'home') return; // Can't close home tab

        const tabIndex = this.tabs.findIndex(tab => tab.id === id);
        if (tabIndex === -1) return;

        this.tabs.splice(tabIndex, 1);

        // If we're closing the active tab, switch to another tab
        if (this.activeTabId === id) {
            if (this.tabs.length > 0) {
                // Switch to the previous tab or the first available tab
                const newActiveIndex = Math.max(0, tabIndex - 1);
                this.setActiveTab(this.tabs[newActiveIndex].id);
                window.location.href = this.tabs[newActiveIndex].url;
            } else {
                // No tabs left, go to home
                this.setActiveTab('home');
                window.location.href = '/tickets/';
            }
        }

        this.saveTabs();
        this.renderTabs();
    }

    setActiveTab(id) {
        this.activeTabId = id;
        this.saveTabs();
        this.updateActiveTab();
    }

    updateActiveTab() {
        const tabElements = document.querySelectorAll('.sf-tab-item');
        tabElements.forEach(tab => {
            const tabId = tab.getAttribute('data-tab-id');
            if (tabId === this.activeTabId) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
    }

    createTabBar() {
        // Check if tab bar already exists
        if (document.querySelector('.sf-tab-system')) return;

        const tabBar = document.createElement('div');
        tabBar.className = 'sf-tab-system';
        tabBar.innerHTML = `
            <div class="sf-tab-container">
                <div class="sf-tab-wrapper">
                    <div class="sf-tab-nav">
                        <div class="sf-tab-list" id="sf-tab-list">
                            <!-- Tabs will be rendered here -->
                        </div>
                        <div class="sf-tab-actions">
                            <button class="sf-tab-action-btn" title="New Tab (Ctrl+T)" onclick="tabSystem.openNewTab()">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Find the navigation bar and insert tab bar after it
        const nav = document.querySelector('nav');
        if (nav) {
            nav.parentNode.insertBefore(tabBar, nav.nextSibling);
        } else {
            // Fallback: insert at the top of the body if nav not found
            document.body.insertBefore(tabBar, document.body.firstChild);
        }
        
        // Add CSS styles
        this.addStyles();
        
        // Render tabs
        this.renderTabs();
    }

    renderTabs() {
        const tabList = document.getElementById('sf-tab-list');
        if (!tabList) return;

        // Always ensure home tab exists
        if (!this.tabs.find(tab => tab.id === 'home')) {
            this.tabs.unshift({
                id: 'home',
                title: 'Home',
                url: '/tickets/',
                icon: 'home',
                closable: false
            });
        }

        tabList.innerHTML = this.tabs.map(tab => `
            <div class="sf-tab-item ${tab.id === this.activeTabId ? 'active' : ''}" 
                 data-tab-id="${tab.id}" 
                 onclick="tabSystem.switchToTab('${tab.id}', '${tab.url}')">
                ${this.getTabIcon(tab.icon)}
                <span class="sf-tab-title">${tab.title}</span>
                ${tab.closable ? `
                    <button class="sf-tab-close" title="Close Tab (Ctrl+W)" 
                            onclick="event.stopPropagation(); tabSystem.removeTab('${tab.id}')">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                ` : ''}
            </div>
        `).join('');
    }

    getTabIcon(iconType) {
        const icons = {
            home: `<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                     <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                   </svg>`,
            ticket: `<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                     </svg>`
        };
        return icons[iconType] || icons.ticket;
    }

    switchToTab(id, url) {
        this.setActiveTab(id);
        if (window.location.href !== url) {
            window.location.href = url;
        }
    }

    openNewTab() {
        window.open('/tickets/', '_blank');
    }

    bindEvents() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey)) {
                switch (e.key) {
                    case 'w':
                        e.preventDefault();
                        if (this.activeTabId && this.activeTabId !== 'home') {
                            this.removeTab(this.activeTabId);
                        }
                        break;
                    case 't':
                        e.preventDefault();
                        this.openNewTab();
                        break;
                    case '1':
                        e.preventDefault();
                        this.switchToTab('home', '/tickets/');
                        break;
                }
            }
        });

        // Handle page navigation
        window.addEventListener('beforeunload', () => {
            this.saveTabs();
        });
    }

    addStyles() {
        if (document.getElementById('sf-tab-styles')) return;

        const style = document.createElement('style');
        style.id = 'sf-tab-styles';
        style.textContent = `
            .sf-tab-system {
                position: relative;
                z-index: 999;
                background: #f8f9fa;
                border-bottom: 1px solid #e5e7eb;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                width: 100%;
            }

            .sf-tab-container {
                background-color: #f8f9fa;
            }

            .sf-tab-wrapper {
                padding: 0 2rem;
            }

            .sf-tab-nav {
                display: flex;
                align-items: center;
                min-height: 48px;
            }

            .sf-tab-list {
                display: flex;
                align-items: center;
                overflow-x: auto;
                scrollbar-width: none;
                -ms-overflow-style: none;
                flex: 1;
            }

            .sf-tab-list::-webkit-scrollbar {
                display: none;
            }

            .sf-tab-item {
                display: flex;
                align-items: center;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                color: #6b7280;
                text-decoration: none;
                border-bottom: 2px solid transparent;
                white-space: nowrap;
                cursor: pointer;
                transition: all 0.2s ease;
                position: relative;
                min-width: 120px;
                max-width: 200px;
            }

            .sf-tab-item:hover {
                color: #374151;
                background-color: #f3f4f6;
                transform: translateY(-1px);
            }

            .sf-tab-item.active {
                color: #1d4ed8;
                background-color: #eff6ff;
                border-bottom-color: #1d4ed8;
            }

            .sf-tab-item.active::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background-color: #1d4ed8;
            }

            .sf-tab-title {
                flex: 1;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .sf-tab-close {
                margin-left: 8px;
                padding: 2px;
                border-radius: 2px;
                color: #9ca3af;
                transition: all 0.2s ease;
                background: none;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .sf-tab-close:hover {
                color: #ef4444;
                background-color: #fee2e2;
            }

            .sf-tab-actions {
                padding: 0 16px;
                display: flex;
                align-items: center;
            }

            .sf-tab-action-btn {
                padding: 6px;
                border-radius: 4px;
                color: #6b7280;
                background: none;
                border: none;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .sf-tab-action-btn:hover {
                color: #374151;
                background-color: #f3f4f6;
            }

            /* Dark mode support */
            body.dark-theme .sf-tab-system {
                background: #1f2937;
                border-bottom: 1px solid #374151;
            }

            body.dark-theme .sf-tab-container {
                background-color: #1f2937;
            }

            body.dark-theme .sf-tab-item {
                color: #9ca3af;
            }

            body.dark-theme .sf-tab-item:hover {
                color: #e5e7eb;
                background-color: #374151;
            }

            body.dark-theme .sf-tab-item.active {
                color: #60a5fa;
                background-color: #1e3a8a;
                border-bottom-color: #60a5fa;
            }

            body.dark-theme .sf-tab-item.active::before {
                background-color: #60a5fa;
            }

            body.dark-theme .sf-tab-close {
                color: #6b7280;
            }

            body.dark-theme .sf-tab-close:hover {
                color: #f87171;
                background-color: #7f1d1d;
            }

            body.dark-theme .sf-tab-action-btn {
                color: #9ca3af;
            }

            body.dark-theme .sf-tab-action-btn:hover {
                color: #e5e7eb;
                background-color: #374151;
            }

            /* Ensure proper spacing */
            .sf-tab-system {
                margin: 0;
            }
            
            .sf-tab-system + * {
                margin-top: 0;
            }

            /* Animation for tab interactions */
            @keyframes subtle-pulse {
                0%, 100% { box-shadow: 0 0 0 0 rgba(29, 78, 216, 0.1); }
                50% { box-shadow: 0 0 0 4px rgba(29, 78, 216, 0.05); }
            }

            .sf-tab-item.active {
                animation: subtle-pulse 2s infinite;
            }
        `;
        document.head.appendChild(style);
    }

    // Public methods for external use
    openTicket(ticketId, ticketSubject) {
        const tabId = `ticket-${ticketId}`;
        const title = `Case ${ticketId}`;
        const url = `/tickets/${ticketId}`;
        this.addTab(tabId, title, url, 'ticket');
    }

    getCurrentPage() {
        const path = window.location.pathname;
        if (path === '/tickets/' || path === '/tickets') {
            return 'home';
        } else if (path.match(/^\/tickets\/\d+/)) {
            const ticketId = path.match(/\/tickets\/(\d+)/)[1];
            return `ticket-${ticketId}`;
        }
        return null;
    }

    initCurrentPage() {
        const currentPage = this.getCurrentPage();
        if (currentPage) {
            this.setActiveTab(currentPage);
            
            // If this is a ticket page and the tab doesn't exist, add it
            if (currentPage.startsWith('ticket-') && !this.tabs.find(tab => tab.id === currentPage)) {
                const ticketId = currentPage.replace('ticket-', '');
                // Try to get ticket subject from the page
                const titleElement = document.querySelector('h1, .sf-card-title');
                const ticketSubject = titleElement ? titleElement.textContent.trim() : `Case ${ticketId}`;
                this.addTab(currentPage, ticketSubject, window.location.pathname, 'ticket');
            }
        }
    }
}

// Initialize tab system when DOM is loaded
let tabSystem;
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit longer to ensure navigation is fully rendered
    setTimeout(() => {
        tabSystem = new TabSystem();
        
        // Initialize current page
        setTimeout(() => {
            tabSystem.initCurrentPage();
        }, 100);
    }, 50);
});

// Make tabSystem globally available
window.tabSystem = tabSystem;