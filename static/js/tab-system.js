/**
 * Salesforce-style Tab System
 * Manages tabs across the entire application using session storage
 */

class TabSystem {
    constructor() {
        this.tabs = this.loadTabs();
        this.activeTabId = this.getActiveTabId();
        // Fix stale home tab URL if it exists
        this.fixHomeTabUrl();
        this.init();
    }

    // Ensure home tab always has the correct URL
    fixHomeTabUrl() {
        const homeTab = this.tabs.find(tab => tab.id === 'home');
        if (homeTab && homeTab.url !== '/dashboard/') {
            homeTab.url = '/dashboard/';
            this.saveTabs();
        }
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
                window.location.href = '/dashboard/';
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
                        <!-- App Launcher (9-dot waffle) -->
                        <div class="sf-app-launcher">
                            <button class="sf-app-launcher-btn" onclick="tabSystem.toggleAppMenu()" title="App Launcher">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                    <circle cx="5" cy="5" r="2"/>
                                    <circle cx="12" cy="5" r="2"/>
                                    <circle cx="19" cy="5" r="2"/>
                                    <circle cx="5" cy="12" r="2"/>
                                    <circle cx="12" cy="12" r="2"/>
                                    <circle cx="19" cy="12" r="2"/>
                                    <circle cx="5" cy="19" r="2"/>
                                    <circle cx="12" cy="19" r="2"/>
                                    <circle cx="19" cy="19" r="2"/>
                                </svg>
                            </button>
                            <div class="sf-app-menu" id="sf-app-menu">
                                <div class="sf-app-menu-header">App Launcher</div>
                                <div class="sf-app-menu-grid">
                                    <a href="/dashboard/" class="sf-app-item">
                                        <div class="sf-app-icon" style="background: #0176d3;">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                                            </svg>
                                        </div>
                                        <span>Home</span>
                                    </a>
                                    <a href="/tickets/" class="sf-app-item">
                                        <div class="sf-app-icon" style="background: #ff5d2d;">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                            </svg>
                                        </div>
                                        <span>Cases</span>
                                    </a>
                                    <a href="/inventory/sf" class="sf-app-item">
                                        <div class="sf-app-icon" style="background: #2e844a;">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                                <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
                                            </svg>
                                        </div>
                                        <span>Inventory</span>
                                    </a>
                                    <a href="/reports/" class="sf-app-item">
                                        <div class="sf-app-icon" style="background: #9050e9;">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                                <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                                            </svg>
                                        </div>
                                        <span>Reports</span>
                                    </a>
                                    <a href="/customers/" class="sf-app-item">
                                        <div class="sf-app-icon" style="background: #fe9339;">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                                            </svg>
                                        </div>
                                        <span>Customers</span>
                                    </a>
                                    <a href="/parcel-tracking/" class="sf-app-item">
                                        <div class="sf-app-icon" style="background: #00a1e0;">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                                <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
                                            </svg>
                                        </div>
                                        <span>Tracking</span>
                                    </a>
                                </div>
                            </div>
                        </div>
                        <!-- Console Label -->
                        <div class="sf-console-label">
                            <span>Service Console</span>
                        </div>
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
                url: '/dashboard/',
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
                     </svg>`,
            asset: `<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                    </svg>`,
            accessory: `<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
                        </svg>`,
            inventory: `<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/>
                        </svg>`,
            report: `<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                     </svg>`,
            dev: `<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
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
        window.open('/dashboard/', '_blank');
    }

    toggleAppMenu() {
        const menu = document.getElementById('sf-app-menu');
        if (menu) {
            menu.classList.toggle('open');

            // Close menu when clicking outside
            if (menu.classList.contains('open')) {
                setTimeout(() => {
                    document.addEventListener('click', this.closeAppMenuOnClickOutside);
                }, 0);
            }
        }
    }

    closeAppMenuOnClickOutside = (e) => {
        const menu = document.getElementById('sf-app-menu');
        const launcher = document.querySelector('.sf-app-launcher');
        if (menu && launcher && !launcher.contains(e.target)) {
            menu.classList.remove('open');
            document.removeEventListener('click', this.closeAppMenuOnClickOutside);
        }
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
                        this.switchToTab('home', '/dashboard/');
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
                background: linear-gradient(to bottom, #ffffff 0%, #f3f3f3 100%);
                border-bottom: 1px solid #dddbda;
                width: 100%;
            }

            .sf-tab-container {
                max-width: 100%;
                margin: 0 auto;
                background: transparent;
            }

            .sf-tab-wrapper {
                padding: 0 1.5rem;
            }

            .sf-tab-nav {
                display: flex;
                align-items: stretch;
                min-height: 44px;
                gap: 2px;
            }

            /* App Launcher (9-dot waffle) */
            .sf-app-launcher {
                position: relative;
                display: flex;
                align-items: center;
                padding: 0 8px;
            }

            .sf-app-launcher-btn {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 36px;
                height: 36px;
                border: none;
                background: transparent;
                border-radius: 4px;
                color: #0176d3;
                cursor: pointer;
                transition: all 0.15s ease;
            }

            .sf-app-launcher-btn:hover {
                background: rgba(1, 118, 211, 0.1);
            }

            .sf-app-menu {
                position: absolute;
                top: 100%;
                left: 0;
                margin-top: 4px;
                background: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
                min-width: 320px;
                z-index: 1000;
                display: none;
                overflow: hidden;
            }

            .sf-app-menu.open {
                display: block;
            }

            .sf-app-menu-header {
                padding: 16px 20px;
                font-size: 16px;
                font-weight: 700;
                color: #080707;
                border-bottom: 1px solid #e5e5e5;
            }

            .sf-app-menu-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 4px;
                padding: 16px;
            }

            .sf-app-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 12px 8px;
                border-radius: 8px;
                text-decoration: none;
                color: #3e3e3c;
                transition: all 0.15s ease;
            }

            .sf-app-item:hover {
                background: #f3f3f3;
            }

            .sf-app-icon {
                width: 48px;
                height: 48px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 8px;
            }

            .sf-app-item span {
                font-size: 12px;
                font-weight: 500;
                text-align: center;
            }

            /* Console Label */
            .sf-console-label {
                display: flex;
                align-items: center;
                padding: 0 12px;
                font-size: 16px;
                font-weight: 700;
                color: #0176d3;
                white-space: nowrap;
                border-right: 1px solid #dddbda;
                margin-right: 8px;
            }

            .sf-tab-list {
                display: flex;
                align-items: stretch;
                overflow-x: auto;
                scrollbar-width: none;
                -ms-overflow-style: none;
                gap: 2px;
                padding: 6px 0 0 0;
            }

            .sf-tab-list::-webkit-scrollbar {
                display: none;
            }

            .sf-tab-item {
                display: flex;
                align-items: center;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                color: #3e3e3c;
                text-decoration: none;
                white-space: nowrap;
                cursor: pointer;
                transition: all 0.15s ease;
                position: relative;
                min-width: 140px;
                max-width: 240px;
                background: #f3f3f3;
                border: 1px solid #dddbda;
                border-bottom: none;
                border-radius: 0.25rem 0.25rem 0 0;
                margin-bottom: -1px;
            }

            .sf-tab-item:hover {
                color: #0176d3;
                background: #ffffff;
            }

            .sf-tab-item.active {
                color: #0176d3;
                background: #ffffff;
                border-color: #dddbda;
                z-index: 1;
            }

            .sf-tab-item.active::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: #0176d3;
            }

            .sf-tab-title {
                flex: 1;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .sf-tab-close {
                margin-left: 10px;
                padding: 4px;
                border-radius: 4px;
                color: #706e6b;
                transition: all 0.15s ease;
                background: none;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .sf-tab-close:hover {
                color: #c23934;
                background-color: #fce4e4;
            }

            .sf-tab-actions {
                padding: 0 12px;
                display: flex;
                align-items: center;
                margin-left: auto;
            }

            .sf-tab-action-btn {
                padding: 8px;
                border-radius: 4px;
                color: #706e6b;
                background: none;
                border: 1px solid transparent;
                cursor: pointer;
                transition: all 0.15s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .sf-tab-action-btn:hover {
                color: #0176d3;
                background-color: #f3f3f3;
                border-color: #dddbda;
            }

            /* Dark mode support */
            body.dark-theme .sf-tab-system {
                background: linear-gradient(to bottom, #1f2937 0%, #111827 100%);
                border-bottom: 1px solid #374151;
            }

            body.dark-theme .sf-tab-container {
                background: transparent;
            }

            body.dark-theme .sf-tab-item {
                color: #d1d5db;
                background: #1f2937;
                border-color: #374151;
            }

            body.dark-theme .sf-tab-item:hover {
                color: #60a5fa;
                background: #374151;
            }

            body.dark-theme .sf-tab-item.active {
                color: #60a5fa;
                background: #111827;
                border-color: #374151;
            }

            body.dark-theme .sf-tab-item.active::after {
                background: #60a5fa;
            }

            body.dark-theme .sf-tab-close {
                color: #9ca3af;
            }

            body.dark-theme .sf-tab-close:hover {
                color: #f87171;
                background-color: #450a0a;
            }

            body.dark-theme .sf-tab-action-btn {
                color: #9ca3af;
            }

            body.dark-theme .sf-tab-action-btn:hover {
                color: #60a5fa;
                background-color: #374151;
                border-color: #4b5563;
            }

            /* Dark mode - App Launcher */
            body.dark-theme .sf-app-launcher-btn {
                color: #60a5fa;
            }

            body.dark-theme .sf-app-launcher-btn:hover {
                background: rgba(96, 165, 250, 0.1);
            }

            body.dark-theme .sf-app-menu {
                background: #1f2937;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
            }

            body.dark-theme .sf-app-menu-header {
                color: #f9fafb;
                border-bottom: 1px solid #374151;
            }

            body.dark-theme .sf-app-item {
                color: #d1d5db;
            }

            body.dark-theme .sf-app-item:hover {
                background: #374151;
            }

            body.dark-theme .sf-console-label {
                color: #60a5fa;
                border-right-color: #374151;
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

    openAsset(assetId, assetName) {
        const tabId = `asset-${assetId}`;
        const title = assetName || `Asset ${assetId}`;
        const url = `/inventory/view-sf/${assetId}`;
        this.addTab(tabId, title, url, 'asset');
    }

    openAccessory(accessoryId, accessoryName) {
        const tabId = `accessory-${accessoryId}`;
        const title = accessoryName || `Accessory ${accessoryId}`;
        const url = `/inventory/accessory-sf/${accessoryId}`;
        this.addTab(tabId, title, url, 'accessory');
    }

    getCurrentPage() {
        const path = window.location.pathname;

        // Home page / Dashboard
        if (path === '/' || path === '/home' || path === '/home/' || path === '/dashboard' || path === '/dashboard/') {
            return 'home';
        }

        // Development console
        if (path === '/development/dashboard' || path === '/development/dashboard/') {
            return 'dev-console';
        }

        // Action items / meetings (part of dev console, no separate tab)
        if (path.match(/^\/action-items/)) {
            return 'dev-console';
        }

        // Other development pages (features, bugs, etc.) - part of dev console
        if (path.match(/^\/development/)) {
            return 'dev-console';
        }

        // Tickets list - use ticket-home
        if (path === '/tickets/' || path === '/tickets') {
            return 'ticket-home';
        }

        // Individual ticket
        if (path.match(/^\/tickets\/\d+/)) {
            const ticketId = path.match(/\/tickets\/(\d+)/)[1];
            return `ticket-${ticketId}`;
        }

        // Inventory list
        if (path === '/inventory/' || path === '/inventory' || path === '/inventory/sf') {
            return 'inventory';
        }

        // Individual asset (SF view)
        if (path.match(/^\/inventory\/view-sf\/\d+/)) {
            const assetId = path.match(/\/inventory\/view-sf\/(\d+)/)[1];
            return `asset-${assetId}`;
        }

        // Individual accessory (SF view)
        if (path.match(/^\/inventory\/accessory-sf\/\d+/)) {
            const accessoryId = path.match(/\/inventory\/accessory-sf\/(\d+)/)[1];
            return `accessory-${accessoryId}`;
        }

        // Reports
        if (path.match(/^\/reports/)) {
            return 'reports';
        }

        return null;
    }

    initCurrentPage() {
        const currentPage = this.getCurrentPage();
        if (!currentPage) return;

        this.setActiveTab(currentPage);

        // If this tab doesn't exist, add it
        if (!this.tabs.find(tab => tab.id === currentPage)) {
            const path = window.location.pathname;
            const titleElement = document.querySelector('.sf-record-title, h1, .sf-card-title');
            const title = titleElement ? titleElement.textContent.trim().substring(0, 30) : '';

            // Home page - skip, home is always there
            if (currentPage === 'home') {
                return;
            }
            // Tickets list - ticket-home tab
            else if (currentPage === 'ticket-home') {
                this.addTab('ticket-home', 'Tickets', '/tickets/', 'ticket');
            }
            // Ticket pages
            else if (currentPage.startsWith('ticket-') && currentPage !== 'ticket-home') {
                const ticketId = currentPage.replace('ticket-', '');
                this.addTab(currentPage, title || `Case ${ticketId}`, path, 'ticket');
            }
            // Asset pages
            else if (currentPage.startsWith('asset-')) {
                const assetId = currentPage.replace('asset-', '');
                this.addTab(currentPage, title || `Asset ${assetId}`, path, 'asset');
            }
            // Accessory pages
            else if (currentPage.startsWith('accessory-')) {
                const accessoryId = currentPage.replace('accessory-', '');
                this.addTab(currentPage, title || `Accessory ${accessoryId}`, path, 'accessory');
            }
            // Inventory list
            else if (currentPage === 'inventory') {
                this.addTab('inventory', 'Inventory', '/inventory/sf', 'inventory');
            }
            // Reports
            else if (currentPage === 'reports') {
                this.addTab('reports', 'Reports', '/reports/', 'report');
            }
            // Dev Console
            else if (currentPage === 'dev-console') {
                this.addTab('dev-console', 'Dev Console', '/development/dashboard', 'dev');
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
        window.tabSystem = tabSystem;

        // Initialize current page
        setTimeout(() => {
            tabSystem.initCurrentPage();
        }, 100);
    }, 50);
});

// Reset tabs function - can be called from console to fix issues
window.resetTabs = function() {
    sessionStorage.removeItem('sf-tabs');
    sessionStorage.removeItem('sf-active-tab');
    console.log('Tabs reset. Refreshing page...');
    window.location.reload();
};