/**
 * Queue Manager - iOS Home Screen Style
 * Handles queue and folder management with jiggle mode, drag-drop, and folder expansion
 */

const QueueManager = {
    // State
    isOpen: false,
    isEditMode: false,
    queues: [],
    folders: [],
    expandedFolderId: null,
    pendingDelete: null,
    draggedItem: null,
    csrfToken: null,

    // Initialize
    init(csrfToken) {
        console.log('[QueueManager] Initializing with CSRF token');
        this.csrfToken = csrfToken;
        this.bindEvents();
        console.log('[QueueManager] Initialized successfully');
    },

    bindEvents() {
        // Keyboard events
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (document.getElementById('deleteConfirmModal')?.classList.contains('hidden') === false) {
                    this.hideDeleteConfirm();
                } else if (document.getElementById('addQueueModal')?.classList.contains('hidden') === false) {
                    this.hideAddQueue();
                } else if (document.getElementById('addFolderModal')?.classList.contains('hidden') === false) {
                    this.hideAddFolder();
                } else if (this.expandedFolderId) {
                    this.closeExpandedFolder();
                } else if (this.isOpen) {
                    this.close();
                }
            }
        });

        // Folder color selection
        document.querySelectorAll('.folder-color-option input').forEach(input => {
            input.addEventListener('change', () => {
                document.querySelectorAll('.folder-color-option span').forEach(span => {
                    span.style.boxShadow = '';
                });
            });
        });
    },

    // Open queue manager modal
    async open() {
        console.log('[QueueManager] open() called');
        const modal = document.getElementById('queueManagerModal');
        console.log('[QueueManager] Modal element:', modal);
        if (!modal) {
            console.error('[QueueManager] Modal element not found!');
            return;
        }

        this.isOpen = true;
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        await this.loadQueues();
    },

    // Close queue manager modal
    close() {
        const modal = document.getElementById('queueManagerModal');
        if (!modal) return;

        this.isOpen = false;
        this.isEditMode = false;
        this.expandedFolderId = null;
        modal.classList.add('hidden');
        document.body.style.overflow = '';

        // Reset edit mode button
        const editBtn = document.getElementById('toggleEditModeBtn');
        if (editBtn) {
            editBtn.textContent = 'Edit';
            editBtn.classList.remove('active');
        }

        // Hide expanded folder
        document.getElementById('expandedFolderOverlay')?.classList.add('hidden');

        // Refresh queue dropdowns on page
        this.refreshQueueDropdowns();
    },

    // Load queues from API
    async loadQueues() {
        const grid = document.getElementById('queueGrid');
        const loading = document.getElementById('queueGridLoading');

        console.log('[QueueManager] loadQueues called');
        console.log('[QueueManager] grid element:', grid);
        console.log('[QueueManager] loading element:', loading);

        try {
            const response = await fetch('/tickets/queues/api/list');
            console.log('[QueueManager] API response status:', response.status);
            const data = await response.json();
            console.log('[QueueManager] API data:', data);

            if (data.success) {
                this.queues = data.queues || [];
                this.folders = data.folders || [];
                console.log('[QueueManager] Loaded queues:', this.queues.length);
                console.log('[QueueManager] Loaded folders:', this.folders.length);
                this.renderGrid();
            } else {
                console.error('[QueueManager] API returned error:', data.error);
                this.showToast('Failed to load queues', 'error');
            }
        } catch (error) {
            console.error('[QueueManager] Error loading queues:', error);
            this.showToast('Error loading queues', 'error');
        } finally {
            loading?.classList.add('hidden');
            grid?.classList.remove('hidden');
        }
    },

    // Render the queue grid
    renderGrid() {
        console.log('[QueueManager] renderGrid called');
        const grid = document.getElementById('queueGrid');
        if (!grid) {
            console.error('[QueueManager] Grid element not found!');
            return;
        }

        grid.innerHTML = '';

        // Separate queues into folders and unfiled
        const folderQueues = {};
        const unfiledQueues = [];

        this.queues.forEach(queue => {
            if (queue.folder_id) {
                if (!folderQueues[queue.folder_id]) {
                    folderQueues[queue.folder_id] = [];
                }
                folderQueues[queue.folder_id].push(queue);
            } else {
                unfiledQueues.push(queue);
            }
        });

        console.log('[QueueManager] Folders to render:', this.folders.length);
        console.log('[QueueManager] Unfiled queues to render:', unfiledQueues.length);

        // Render folders
        this.folders.forEach(folder => {
            const folderEl = this.createFolderElement(folder, folderQueues[folder.id] || []);
            if (folderEl) {
                grid.appendChild(folderEl);
            }
        });

        // Render unfiled queues
        unfiledQueues.forEach(queue => {
            const queueEl = this.createQueueElement(queue);
            if (queueEl) {
                grid.appendChild(queueEl);
            }
        });

        // Apply edit mode if active
        if (this.isEditMode) {
            grid.classList.add('edit-mode');
        } else {
            grid.classList.remove('edit-mode');
        }

        // Empty state
        if (this.folders.length === 0 && unfiledQueues.length === 0) {
            grid.innerHTML = `
                <div class="queue-grid-empty col-span-full">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                    </svg>
                    <p>No queues yet</p>
                    <span>Click "Add Queue" to create your first queue</span>
                </div>
            `;
        }

        // Setup drag and drop
        this.setupDragDrop();
    },

    // Create queue element
    createQueueElement(queue, inFolder = false) {
        const template = document.getElementById('queueItemTemplate');
        if (!template) {
            console.error('[QueueManager] queueItemTemplate not found!');
            return null;
        }

        const el = template.content.cloneNode(true).querySelector('.queue-item');
        if (!el) {
            console.error('[QueueManager] Could not clone queue-item from template');
            return null;
        }

        el.dataset.queueId = queue.id;
        el.querySelector('.queue-name').textContent = queue.name;

        // Click handler (when not in edit mode)
        el.addEventListener('click', (e) => {
            if (!this.isEditMode && !e.target.closest('.delete-btn')) {
                // Could select queue or do nothing
            }
        });

        return el;
    },

    // Create folder element
    createFolderElement(folder, queues) {
        const template = document.getElementById('folderItemTemplate');
        if (!template) {
            console.error('[QueueManager] folderItemTemplate not found!');
            return null;
        }

        const el = template.content.cloneNode(true).querySelector('.folder-item');
        if (!el) {
            console.error('[QueueManager] Could not clone folder-item from template');
            return null;
        }

        el.dataset.folderId = folder.id;
        el.dataset.color = folder.color || 'blue';
        el.querySelector('.folder-name').textContent = folder.name;

        // Render mini queue previews (up to 4)
        const preview = el.querySelector('.folder-preview');
        queues.slice(0, 4).forEach(() => {
            const miniIcon = document.createElement('div');
            miniIcon.className = 'folder-preview-item';
            preview.appendChild(miniIcon);
        });

        return el;
    },

    // Toggle edit mode (jiggle)
    toggleEditMode() {
        this.isEditMode = !this.isEditMode;

        const grid = document.getElementById('queueGrid');
        const editBtn = document.getElementById('toggleEditModeBtn');

        if (this.isEditMode) {
            grid?.classList.add('edit-mode');
            if (editBtn) {
                editBtn.textContent = 'Done';
                editBtn.classList.add('active');
            }
        } else {
            grid?.classList.remove('edit-mode');
            if (editBtn) {
                editBtn.textContent = 'Edit';
                editBtn.classList.remove('active');
            }
        }
    },

    // Expand folder
    expandFolder(folderId) {
        // Allow opening folder in edit mode to enable drag-drop into it

        const folder = this.folders.find(f => f.id == folderId);
        if (!folder) return;

        this.expandedFolderId = folderId;

        const overlay = document.getElementById('expandedFolderOverlay');
        const nameInput = document.getElementById('expandedFolderName');
        const grid = document.getElementById('expandedFolderGrid');

        if (nameInput) nameInput.value = folder.name;

        // Render queues in folder
        if (grid) {
            grid.innerHTML = '';
            const folderQueues = this.queues.filter(q => q.folder_id == folderId);

            if (folderQueues.length === 0) {
                const editModeText = this.isEditMode
                    ? 'Drag queues here from the grid below'
                    : 'Click "Edit" then drag queues here';
                grid.innerHTML = `
                    <div class="expanded-folder-empty col-span-3 text-center text-white/70 py-8">
                        <p>No queues in this folder</p>
                        <p class="text-sm mt-1">${editModeText}</p>
                    </div>
                `;
            } else {
                folderQueues.forEach(queue => {
                    const queueEl = this.createQueueElement(queue, true);
                    grid.appendChild(queueEl);
                });
            }

            // Setup drag-drop for expanded folder grid
            this.setupExpandedFolderDragDrop(grid);
        }

        overlay?.classList.remove('hidden');
    },

    // Setup drag-drop handlers for expanded folder grid
    setupExpandedFolderDragDrop(grid) {
        // Make the grid a drop zone
        grid.addEventListener('dragover', (e) => {
            if (this.draggedItem && this.isEditMode) {
                e.preventDefault();
                grid.classList.add('drag-over');
            }
        });

        grid.addEventListener('dragleave', (e) => {
            // Only remove class if leaving the grid entirely
            if (!grid.contains(e.relatedTarget)) {
                grid.classList.remove('drag-over');
            }
        });

        grid.addEventListener('drop', async (e) => {
            e.preventDefault();
            grid.classList.remove('drag-over');

            if (this.draggedItem && this.expandedFolderId) {
                const queueId = this.draggedItem.dataset.queueId;
                await this.moveQueueToFolder(queueId, this.expandedFolderId);

                // Refresh the expanded folder view
                this.expandFolder(this.expandedFolderId);
            }
        });

        // Setup drag handlers for queues inside expanded folder
        grid.querySelectorAll('.queue-item').forEach(item => {
            item.addEventListener('dragstart', (e) => this.handleDragStart(e));
            item.addEventListener('dragend', (e) => this.handleDragEnd(e));
        });
    },

    // Close expanded folder
    closeExpandedFolder() {
        this.expandedFolderId = null;
        document.getElementById('expandedFolderOverlay')?.classList.add('hidden');
    },

    // Update folder name
    async updateFolderName(newName) {
        if (!this.expandedFolderId || !newName.trim()) return;

        try {
            const response = await fetch(`/tickets/queues/folders/${this.expandedFolderId}/edit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ name: newName.trim() })
            });

            const data = await response.json();
            if (data.success) {
                // Update local state
                const folder = this.folders.find(f => f.id == this.expandedFolderId);
                if (folder) folder.name = newName.trim();
                this.renderGrid();
                this.showToast('Folder renamed', 'success');
            } else {
                this.showToast(data.error || 'Failed to rename folder', 'error');
            }
        } catch (error) {
            console.error('Error updating folder:', error);
            this.showToast('Error updating folder', 'error');
        }
    },

    // Setup drag and drop
    setupDragDrop() {
        const grid = document.getElementById('queueGrid');
        if (!grid) return;

        // Queue items
        grid.querySelectorAll('.queue-item').forEach(item => {
            item.addEventListener('dragstart', (e) => this.handleDragStart(e));
            item.addEventListener('dragend', (e) => this.handleDragEnd(e));
        });

        // Folder items (drop targets)
        grid.querySelectorAll('.folder-item').forEach(item => {
            item.addEventListener('dragover', (e) => this.handleDragOver(e));
            item.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            item.addEventListener('drop', (e) => this.handleDrop(e));
        });

        // Grid itself (for removing from folder)
        grid.addEventListener('dragover', (e) => {
            if (this.draggedItem && e.target === grid) {
                e.preventDefault();
            }
        });

        grid.addEventListener('drop', async (e) => {
            if (this.draggedItem && e.target === grid) {
                e.preventDefault();
                const queueId = this.draggedItem.dataset.queueId;
                await this.moveQueueToFolder(queueId, null);
            }
        });
    },

    handleDragStart(e) {
        if (!this.isEditMode) {
            e.preventDefault();
            return;
        }

        this.draggedItem = e.target.closest('.queue-item');
        if (this.draggedItem) {
            this.draggedItem.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', this.draggedItem.dataset.queueId);
        }
    },

    handleDragEnd(e) {
        if (this.draggedItem) {
            this.draggedItem.classList.remove('dragging');
            this.draggedItem = null;
        }

        document.querySelectorAll('.folder-item').forEach(f => {
            f.classList.remove('drag-over');
        });
    },

    handleDragOver(e) {
        if (!this.isEditMode || !this.draggedItem) return;

        e.preventDefault();
        const folderItem = e.target.closest('.folder-item');
        if (folderItem) {
            folderItem.classList.add('drag-over');
        }
    },

    handleDragLeave(e) {
        const folderItem = e.target.closest('.folder-item');
        if (folderItem) {
            folderItem.classList.remove('drag-over');
        }
    },

    async handleDrop(e) {
        e.preventDefault();
        const folderItem = e.target.closest('.folder-item');

        if (folderItem && this.draggedItem) {
            folderItem.classList.remove('drag-over');

            const queueId = this.draggedItem.dataset.queueId;
            const folderId = folderItem.dataset.folderId;

            await this.moveQueueToFolder(queueId, folderId);
        }
    },

    // Move queue to folder
    async moveQueueToFolder(queueId, folderId) {
        try {
            const response = await fetch('/tickets/queues/api/move-to-folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    queue_id: parseInt(queueId),
                    folder_id: folderId ? parseInt(folderId) : null
                })
            });

            const data = await response.json();
            if (data.success) {
                // Update local state
                const queue = this.queues.find(q => q.id == queueId);
                if (queue) {
                    queue.folder_id = folderId ? parseInt(folderId) : null;
                }
                this.renderGrid();
                this.showToast(folderId ? 'Queue moved to folder' : 'Queue removed from folder', 'success');
            } else {
                this.showToast(data.error || 'Failed to move queue', 'error');
            }
        } catch (error) {
            console.error('Error moving queue:', error);
            this.showToast('Error moving queue', 'error');
        }
    },

    // Show add queue modal
    showAddQueue() {
        document.getElementById('addQueueModal')?.classList.remove('hidden');
        document.getElementById('newQueueName')?.focus();
    },

    // Hide add queue modal
    hideAddQueue() {
        document.getElementById('addQueueModal')?.classList.add('hidden');
        document.getElementById('addQueueForm')?.reset();
    },

    // Create queue
    async createQueue(e) {
        e.preventDefault();

        const name = document.getElementById('newQueueName')?.value?.trim();
        const description = document.getElementById('newQueueDescription')?.value?.trim();

        if (!name) {
            this.showToast('Please enter a queue name', 'error');
            return;
        }

        try {
            const response = await fetch('/tickets/queues/api/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ name, description })
            });

            const data = await response.json();
            if (data.success) {
                this.queues.push(data.queue);
                this.renderGrid();
                this.hideAddQueue();
                this.showToast('Queue created', 'success');
            } else {
                this.showToast(data.error || 'Failed to create queue', 'error');
            }
        } catch (error) {
            console.error('Error creating queue:', error);
            this.showToast('Error creating queue', 'error');
        }
    },

    // Show add folder modal
    showAddFolder() {
        document.getElementById('addFolderModal')?.classList.remove('hidden');
        document.getElementById('newFolderName')?.focus();
    },

    // Hide add folder modal
    hideAddFolder() {
        document.getElementById('addFolderModal')?.classList.add('hidden');
        document.getElementById('addFolderForm')?.reset();
    },

    // Create folder
    async createFolder(e) {
        e.preventDefault();

        const name = document.getElementById('newFolderName')?.value?.trim();
        const colorInput = document.querySelector('input[name="folderColor"]:checked');
        const color = colorInput?.value || 'blue';

        if (!name) {
            this.showToast('Please enter a folder name', 'error');
            return;
        }

        try {
            const response = await fetch('/tickets/queues/folders/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ name, color })
            });

            const data = await response.json();
            if (data.success) {
                this.folders.push(data.folder);
                this.renderGrid();
                this.hideAddFolder();
                this.showToast('Folder created', 'success');
            } else {
                this.showToast(data.error || 'Failed to create folder', 'error');
            }
        } catch (error) {
            console.error('Error creating folder:', error);
            this.showToast('Error creating folder', 'error');
        }
    },

    // Prompt delete queue
    promptDeleteQueue(queueId) {
        const queue = this.queues.find(q => q.id == queueId);
        if (!queue) return;

        this.pendingDelete = { type: 'queue', id: queueId };

        const titleEl = document.getElementById('deleteConfirmTitle');
        const msgEl = document.getElementById('deleteConfirmMessage');

        if (titleEl) titleEl.textContent = 'Delete Queue?';
        if (msgEl) msgEl.textContent = `Are you sure you want to delete "${queue.name}"? This action cannot be undone.`;

        document.getElementById('deleteConfirmModal')?.classList.remove('hidden');
    },

    // Prompt delete folder
    promptDeleteFolder(folderId) {
        const folder = this.folders.find(f => f.id == folderId);
        if (!folder) return;

        const folderQueues = this.queues.filter(q => q.folder_id == folderId);

        this.pendingDelete = { type: 'folder', id: folderId };

        const titleEl = document.getElementById('deleteConfirmTitle');
        const msgEl = document.getElementById('deleteConfirmMessage');

        if (titleEl) titleEl.textContent = 'Delete Folder?';
        if (msgEl) {
            if (folderQueues.length > 0) {
                msgEl.textContent = `Are you sure you want to delete "${folder.name}"? The ${folderQueues.length} queue(s) inside will be moved out of the folder.`;
            } else {
                msgEl.textContent = `Are you sure you want to delete "${folder.name}"?`;
            }
        }

        document.getElementById('deleteConfirmModal')?.classList.remove('hidden');
    },

    // Hide delete confirmation
    hideDeleteConfirm() {
        this.pendingDelete = null;
        document.getElementById('deleteConfirmModal')?.classList.add('hidden');
    },

    // Confirm delete
    async confirmDelete() {
        if (!this.pendingDelete) return;

        const { type, id } = this.pendingDelete;

        try {
            let url, method;
            if (type === 'queue') {
                url = `/tickets/queues/api/delete/${id}`;
                method = 'DELETE';
            } else {
                url = `/tickets/queues/folders/${id}/delete`;
                method = 'DELETE';
            }

            const response = await fetch(url, {
                method,
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            const data = await response.json();
            if (data.success) {
                if (type === 'queue') {
                    this.queues = this.queues.filter(q => q.id != id);
                } else {
                    // Move queues out of folder
                    this.queues.forEach(q => {
                        if (q.folder_id == id) q.folder_id = null;
                    });
                    this.folders = this.folders.filter(f => f.id != id);
                }

                this.renderGrid();
                this.hideDeleteConfirm();
                this.showToast(`${type === 'queue' ? 'Queue' : 'Folder'} deleted`, 'success');
            } else {
                this.showToast(data.error || `Failed to delete ${type}`, 'error');
            }
        } catch (error) {
            console.error(`Error deleting ${type}:`, error);
            this.showToast(`Error deleting ${type}`, 'error');
        }
    },

    // Refresh queue dropdowns and tabs on the page
    refreshQueueDropdowns() {
        // Fetch fresh queue list
        fetch('/tickets/queues/api/list')
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;

                const queues = data.queues || [];

                // Refresh dropdowns (for create ticket page)
                const dropdowns = document.querySelectorAll('select[name="queue_id"]');
                dropdowns.forEach(dropdown => {
                    const currentValue = dropdown.value;
                    const placeholder = dropdown.querySelector('option[value=""]');

                    // Clear and rebuild options
                    dropdown.innerHTML = '';
                    if (placeholder) {
                        dropdown.appendChild(placeholder.cloneNode(true));
                    } else {
                        const opt = document.createElement('option');
                        opt.value = '';
                        opt.textContent = '-- Select a Queue --';
                        dropdown.appendChild(opt);
                    }

                    queues.forEach(queue => {
                        const opt = document.createElement('option');
                        opt.value = queue.id;
                        opt.textContent = queue.name;
                        if (queue.id == currentValue) {
                            opt.selected = true;
                        }
                        dropdown.appendChild(opt);
                    });
                });

                // Refresh queue tabs (for ticket list page)
                const queueTabs = document.getElementById('queueTabs');
                if (queueTabs) {
                    // Keep "All Queues" tab and active state
                    const activeQueue = queueTabs.querySelector('.sf-queue-tab.active')?.dataset?.queue;
                    const allQueuesTab = queueTabs.querySelector('.sf-queue-tab[data-queue="all"]');

                    // Clear existing tabs except "All Queues"
                    queueTabs.querySelectorAll('.sf-queue-tab:not([data-queue="all"])').forEach(tab => tab.remove());

                    // Add queue tabs
                    queues.forEach(queue => {
                        const tab = document.createElement('button');
                        tab.className = 'sf-queue-tab';
                        tab.dataset.queue = queue.name;
                        tab.onclick = function() { filterByQueue(queue.name, this); };
                        tab.innerHTML = `
                            <span class="queue-name">${queue.name}</span>
                            <span class="queue-count">
                                <span class="open-count">${queue.ticket_count || 0}</span>
                            </span>
                        `;

                        // Restore active state
                        if (queue.name === activeQueue) {
                            tab.classList.add('active');
                        }

                        queueTabs.appendChild(tab);
                    });

                    // If active queue was deleted, activate "All Queues"
                    if (activeQueue && activeQueue !== 'all' && !queues.find(q => q.name === activeQueue)) {
                        queueTabs.querySelectorAll('.sf-queue-tab').forEach(t => t.classList.remove('active'));
                        allQueuesTab?.classList.add('active');
                        if (typeof filterByQueue === 'function') {
                            filterByQueue('all', allQueuesTab);
                        }
                    }
                }
            })
            .catch(err => console.error('Error refreshing queues:', err));
    },

    // Show toast notification
    showToast(message, type = 'info') {
        // Remove existing toast
        document.querySelector('.queue-toast')?.remove();

        const toast = document.createElement('div');
        toast.className = `queue-toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Remove after delay
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

// Export for use
window.QueueManager = QueueManager;
