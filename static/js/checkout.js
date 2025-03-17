// Checkout List Management
class CheckoutListManager {
    constructor() {
        this.checkoutList = [];
        this.loadCheckoutList();
        this.initializeUI();
        
        // Add event listener for page unload to ensure data is saved
        window.addEventListener('beforeunload', () => {
            this.saveCheckoutList();
        });
    }

    loadCheckoutList() {
        const savedList = localStorage.getItem('checkoutList');
        if (savedList) {
            try {
                this.checkoutList = JSON.parse(savedList);
            } catch (e) {
                console.error('Error loading checkout list:', e);
                this.checkoutList = [];
            }
        }
        this.updateUI();
    }

    saveCheckoutList() {
        localStorage.setItem('checkoutList', JSON.stringify(this.checkoutList));
        this.updateUI();
    }

    updateUI() {
        const checkoutCount = document.getElementById('checkoutCount');
        if (checkoutCount) {
            checkoutCount.textContent = this.checkoutList.length;
        }

        const processCheckout = document.getElementById('processCheckout');
        const customerSelect = document.getElementById('customerSelect');
        if (processCheckout && customerSelect) {
            processCheckout.disabled = this.checkoutList.length === 0 || !customerSelect.value;
        }

        const checkoutListContent = document.getElementById('checkoutListContent');
        if (checkoutListContent) {
            checkoutListContent.innerHTML = this.checkoutList.map((item, index) => {
                const isAsset = item.type === 'asset';
                return `
                    <div class="flex justify-between items-center p-4 ${isAsset ? 'bg-blue-50' : 'bg-green-50'} rounded-lg mb-2">
                        <div class="flex-grow">
                            <div class="font-medium flex items-center">
                                <span class="inline-block w-20 text-xs ${isAsset ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'} px-2 py-1 rounded mr-2">
                                    ${isAsset ? 'Tech Asset' : 'Accessory'}
                                </span>
                                ${item.name || item.product}
                            </div>
                            <div class="text-sm text-gray-500">
                                ${isAsset ? 
                                    `Asset Tag: ${item.asset_tag || 'N/A'} | Serial: ${item.serial_num || 'N/A'}` :
                                    `Category: ${item.category || 'N/A'}`
                                }
                            </div>
                        </div>
                        
                        ${isAsset ? `` : `
                        <div class="mx-4 flex items-center">
                            <label for="quantity_${index}" class="text-sm font-medium text-gray-700 mr-2">Quantity:</label>
                            <input 
                                type="number" 
                                id="quantity_${index}" 
                                class="w-16 rounded border-gray-300 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50" 
                                min="1"
                                value="${item.quantity || 1}"
                                onchange="window.checkoutManager.updateQuantity(${item.id}, '${item.type}', this.value)"
                            >
                        </div>
                        `}
                        
                        <button onclick="window.checkoutManager.removeItem(${item.id}, '${item.type}')" class="text-red-600 hover:text-red-800 flex-shrink-0">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                `;
            }).join('');
        }
    }

    addItem(item) {
        // Check if item already exists
        const existingIndex = this.checkoutList.findIndex(i => i.id === item.id && i.type === item.type);
        if (existingIndex !== -1) {
            // Update quantity if it's an accessory
            if (item.type === 'accessory') {
                this.checkoutList[existingIndex].quantity = (this.checkoutList[existingIndex].quantity || 1) + (item.quantity || 1);
            }
        } else {
            this.checkoutList.push(item);
        }
        this.saveCheckoutList();
    }

    removeItem(itemId, itemType) {
        this.checkoutList = this.checkoutList.filter(item => !(item.id === itemId && item.type === itemType));
        this.saveCheckoutList();
    }

    updateQuantity(itemId, itemType, quantity) {
        // Find the item
        const existingIndex = this.checkoutList.findIndex(i => i.id === itemId && i.type === itemType);
        
        if (existingIndex !== -1 && itemType === 'accessory') {
            // Validate quantity
            const newQuantity = parseInt(quantity, 10);
            if (isNaN(newQuantity) || newQuantity < 1) {
                // Reset to 1 if invalid
                this.checkoutList[existingIndex].quantity = 1;
            } else {
                this.checkoutList[existingIndex].quantity = newQuantity;
            }
            
            this.saveCheckoutList();
        }
    }

    clearList() {
        this.checkoutList = [];
        this.saveCheckoutList();
    }

    showModal() {
        const checkoutListModal = document.getElementById('checkoutListModal');
        if (checkoutListModal) {
            checkoutListModal.classList.remove('hidden');
            this.updateUI();
        }
    }

    initializeUI() {
        const viewCheckoutList = document.getElementById('viewCheckoutList');
        const checkoutListModal = document.getElementById('checkoutListModal');
        const closeCheckoutModal = document.getElementById('closeCheckoutModal');
        const clearCheckoutList = document.getElementById('clearCheckoutList');
        const customerSelect = document.getElementById('customerSelect');
        const processCheckout = document.getElementById('processCheckout');
        const removeSerialPrefixBtn = document.getElementById('removeSerialPrefix');

        if (viewCheckoutList) {
            viewCheckoutList.addEventListener('click', () => {
                if (checkoutListModal) {
                    checkoutListModal.classList.remove('hidden');
                    this.updateUI();
                }
            });
        }

        if (closeCheckoutModal) {
            closeCheckoutModal.addEventListener('click', () => {
                if (checkoutListModal) {
                    checkoutListModal.classList.add('hidden');
                }
            });
        }

        if (clearCheckoutList) {
            clearCheckoutList.addEventListener('click', () => {
                if (confirm('Are you sure you want to clear the checkout list?')) {
                    this.clearList();
                }
            });
        }

        if (customerSelect) {
            customerSelect.addEventListener('change', () => this.updateUI());
        }

        if (processCheckout) {
            processCheckout.addEventListener('click', () => this.processCheckout());
        }

        if (removeSerialPrefixBtn) {
            removeSerialPrefixBtn.addEventListener('click', () => {
                const selectedAssets = Array.from(document.querySelectorAll('input[name="selected_assets[]"]:checked'))
                    .map(checkbox => parseInt(checkbox.value));
                
                if (selectedAssets.length === 0) {
                    showError('Please select at least one asset');
                    return;
                }
                
                if (confirm('Are you sure you want to remove the S prefix from the selected asset serial numbers?')) {
                    this.removeSerialPrefix(selectedAssets);
                }
            });
        }

        // Initial UI update
        this.updateUI();
    }

    async processCheckout() {
        const customerSelect = document.getElementById('customerSelect');
        
        if (!customerSelect || !customerSelect.value) {
            showError('Please select a customer before proceeding');
            return;
        }
        
        if (this.checkoutList.length === 0) {
            showError('Your checkout list is empty');
            return;
        }
        
        try {
            const accessoryItems = this.checkoutList
                .filter(item => item.type === 'accessory')
                .map(item => ({
                    id: item.id,
                    quantity: parseInt(item.quantity) || 1
                }));

            const assetIds = this.checkoutList
                .filter(item => item.type === 'asset')
                .map(item => item.id);

            const response = await fetch('/inventory/bulk-checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    customer_id: customerSelect.value,
                    asset_ids: assetIds,
                    accessory_ids: accessoryItems
                })
            });

            const responseData = await response.json();
            
            if (!response.ok) {
                // Handle detailed error response
                if (responseData.details && Array.isArray(responseData.details)) {
                    throw new Error(`${responseData.error}\n\n${responseData.details.join('\n')}`);
                } else {
                    throw new Error(responseData.error || 'Failed to process checkout');
                }
            }
            
            // Success path - continue with normal flow
            
            // Handle warnings
            if (responseData.warnings && responseData.warnings.length > 0) {
                showError(`Warning(s):\n${responseData.warnings.join('\n')}`, false);
            }
            
            // Clear the checkout list
            this.checkoutList = [];
            localStorage.removeItem('checkoutList');
            this.updateUI();
            
            // Close the modal
            const checkoutListModal = document.getElementById('checkoutListModal');
            if (checkoutListModal) {
                checkoutListModal.classList.add('hidden');
            }
            
            // Show success message
            showError(responseData.message || 'Checkout processed successfully', true);
            
            // Reload the page to refresh the inventory
            setTimeout(() => window.location.reload(), 2000);
        } catch (error) {
            console.error('Error processing checkout:', error);
            showError(error.message || 'An unexpected error occurred during checkout');
            // Don't reload the page on error - let user see the message
        }
    }

    async removeSerialPrefix(selectedAssetIds) {
        try {
            const response = await fetch('/inventory/remove-serial-prefix', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    asset_ids: selectedAssetIds
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to update serial numbers');
            }

            const result = await response.json();
            showError(result.message, true);
            
            // Reload the page to show updated serial numbers
            setTimeout(() => window.location.reload(), 1500);
        } catch (error) {
            console.error('Error updating serial numbers:', error);
            showError(error.message);
        }
    }
}

// Helper function to show error/success messages
function showError(message, isSuccess = false) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg ${isSuccess ? 'bg-green-100 text-green-800 border border-green-300' : 'bg-red-100 text-red-800 border border-red-300'} z-50`;
    alertDiv.style.minWidth = '300px';
    
    // Create a close button
    const closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;';
    closeButton.className = 'absolute top-1 right-2 text-lg font-bold';
    closeButton.addEventListener('click', () => alertDiv.remove());
    
    // Create message container
    const messageDiv = document.createElement('div');
    messageDiv.textContent = message;
    messageDiv.className = 'pr-4'; // Add padding for close button
    
    // Add elements to alert
    alertDiv.appendChild(closeButton);
    alertDiv.appendChild(messageDiv);
    document.body.appendChild(alertDiv);
    
    // Only set a timeout for success messages, errors stay until dismissed
    let timeoutId = null;
    if (isSuccess) {
        timeoutId = setTimeout(() => alertDiv.remove(), 3000);
        // Clear timeout if user manually closes the alert
        closeButton.addEventListener('click', () => clearTimeout(timeoutId));
    }
}

// Initialize the checkout manager when the script loads
window.addEventListener('DOMContentLoaded', () => {
    window.checkoutManager = new CheckoutListManager();
}); 