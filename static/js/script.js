document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    const tabButtons = document.querySelectorAll('.tab-button');
    
    if (tabButtons.length > 0) {
        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Get target content id
                const targetId = this.getAttribute('data-target');
                
                // Hide all tab panes
                document.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.add('hidden');
                    pane.classList.remove('active');
                });
                
                // Remove active class from all tab buttons
                tabButtons.forEach(btn => {
                    btn.classList.remove('active');
                    btn.classList.remove('border-blue-600');
                    btn.classList.remove('text-blue-600');
                    btn.classList.add('hover:text-gray-600');
                    btn.classList.add('hover:border-gray-300');
                    btn.classList.add('border-transparent');
                });
                
                // Show target tab pane
                const targetPane = document.getElementById(targetId);
                if (targetPane) {
                    targetPane.classList.remove('hidden');
                    targetPane.classList.add('active');
                    
                    // Add active class to clicked button
                    this.classList.add('active');
                    this.classList.add('border-blue-600');
                    this.classList.add('text-blue-600');
                    this.classList.remove('hover:text-gray-600');
                    this.classList.remove('hover:border-gray-300');
                    this.classList.remove('border-transparent');
                }
            });
        });
    }
}); 