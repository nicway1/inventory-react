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
            checkoutListContent.innerHTML = this.checkoutList.map(item => {
                const isAsset = item.type === 'asset';
                return `
                    <div class="flex justify-between items-center p-4 ${isAsset ? 'bg-blue-50' : 'bg-green-50'} rounded-lg">
                        <div>
                            <div class="font-medium flex items-center">
                                <span class="inline-block w-20 text-xs ${isAsset ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'} px-2 py-1 rounded mr-2">
                                    ${isAsset ? 'Tech Asset' : 'Accessory'}
                                </span>
                                ${item.name || item.product}
                            </div>
                            <div class="text-sm text-gray-500">
                                ${isAsset ? 
                                    `Asset Tag: ${item.asset_tag || 'N/A'} | Serial: ${item.serial_num || 'N/A'}` :
                                    `Category: ${item.category || 'N/A'} | Quantity: ${item.quantity || 1}`
                                }
                            </div>
                        </div>
                        <button onclick="window.checkoutManager.removeItem(${item.id}, '${item.type}')" class="text-red-600 hover:text-red-800">
                            Remove
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

        // Initial UI update
        this.updateUI();
    }

    async processCheckout() {
        const customerSelect = document.getElementById('customerSelect');
        if (!customerSelect || !customerSelect.value) {
            showError('Please select a customer');
            return;
        }

        if (this.checkoutList.length === 0) {
            showError('No items in checkout list');
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
                    selected_asset_ids: assetIds,
                    selected_accessory_ids: accessoryItems
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to process checkout');
            }

            const result = await response.json();
            
            if (result.warnings && result.warnings.length > 0) {
                showError(result.warnings.join('\n'), false);
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
            showError(result.message || 'Checkout processed successfully', true);
            
            // Reload the page to refresh the inventory
            setTimeout(() => window.location.reload(), 1500);
        } catch (error) {
            console.error('Error processing checkout:', error);
            showError(error.message);
        }
    }
}

// Helper function to show error/success messages
function showError(message, isSuccess = false) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `fixed top-4 right-4 p-4 rounded-lg ${isSuccess ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'} z-50`;
    alertDiv.textContent = message;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 3000);
}

// Initialize the checkout manager when the script loads
window.checkoutManager = new CheckoutListManager(); 