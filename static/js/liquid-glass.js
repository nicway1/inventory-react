/**
 * Liquid Glass Interactive Effects
 * Inspired by Apple's liquid glass design and the liquid-glass-react library
 */

class LiquidGlass {
    constructor(container) {
        this.container = container;
        this.glow = container.querySelector('.liquid-glass-glow');
        this.isHovering = false;
        this.mouseX = 0;
        this.mouseY = 0;
        this.currentX = 0;
        this.currentY = 0;
        this.ease = 0.1;
        
        this.init();
    }
    
    init() {
        this.createParticles();
        this.bindEvents();
        this.animate();
    }
    
    createParticles() {
        // Skip particle creation for logo containers
        if (this.container.querySelector('img[alt="TrueLog Logo"]')) {
            return; // Don't add particles to logo container
        }
        
        // Create floating particles for other containers
        for (let i = 0; i < 6; i++) {
            const particle = document.createElement('div');
            particle.className = 'liquid-glass-particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 6 + 's';
            this.container.appendChild(particle);
        }
    }
    
    bindEvents() {
        this.container.addEventListener('mouseenter', (e) => {
            this.isHovering = true;
            this.container.classList.add('chromatic');
        });
        
        this.container.addEventListener('mouseleave', (e) => {
            this.isHovering = false;
            this.container.classList.remove('chromatic');
        });
        
        this.container.addEventListener('mousemove', (e) => {
            if (!this.isHovering) return;
            
            const rect = this.container.getBoundingClientRect();
            this.mouseX = e.clientX - rect.left;
            this.mouseY = e.clientY - rect.top;
        });
        
        // Add button interaction
        const buttons = this.container.querySelectorAll('.liquid-glass-button');
        buttons.forEach(button => {
            button.addEventListener('mouseenter', () => {
                this.createRipple(button);
            });
        });
    }
    
    createRipple(button) {
        const ripple = document.createElement('div');
        ripple.style.position = 'absolute';
        ripple.style.width = '4px';
        ripple.style.height = '4px';
        ripple.style.background = 'rgba(255, 255, 255, 0.6)';
        ripple.style.borderRadius = '50%';
        ripple.style.transform = 'scale(0)';
        ripple.style.animation = 'rippleEffect 0.6s ease-out';
        ripple.style.left = '50%';
        ripple.style.top = '50%';
        ripple.style.pointerEvents = 'none';
        ripple.style.zIndex = '10';
        
        button.style.position = 'relative';
        button.appendChild(ripple);
        
        // Remove ripple after animation
        setTimeout(() => {
            if (ripple.parentNode) {
                ripple.parentNode.removeChild(ripple);
            }
        }, 600);
    }
    
    animate() {
        if (this.isHovering && this.glow) {
            // Smooth interpolation for glass glow position
            this.currentX += (this.mouseX - this.currentX) * this.ease;
            this.currentY += (this.mouseY - this.currentY) * this.ease;
            
            this.glow.style.left = this.currentX + 'px';
            this.glow.style.top = this.currentY + 'px';
            
            // Add subtle container transform based on mouse position
            const rect = this.container.getBoundingClientRect();
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (this.currentY - centerY) / centerY * 5;
            const rotateY = (this.currentX - centerX) / centerX * -5;
            
            this.container.style.transform = `
                translateY(-8px) 
                rotateX(${rotateX}deg) 
                rotateY(${rotateY}deg)
            `;
        }
        
        requestAnimationFrame(() => this.animate());
    }
}

// Utility function to add glass effect to inputs
function enhanceInputs() {
    const inputs = document.querySelectorAll('.liquid-glass-input');
    
    inputs.forEach(input => {
        // Add focus glow effect
        input.addEventListener('focus', function() {
            this.style.boxShadow = `
                0 0 0 3px rgba(59, 130, 246, 0.2),
                0 4px 12px rgba(0, 0, 0, 0.1),
                0 0 20px rgba(59, 130, 246, 0.1)
            `;
        });
        
        input.addEventListener('blur', function() {
            this.style.boxShadow = '';
        });
        
        // Add typing effect
        input.addEventListener('input', function() {
            if (this.value.length > 0) {
                this.style.background = 'rgba(255, 255, 255, 0.15)';
            } else {
                this.style.background = 'rgba(255, 255, 255, 0.1)';
            }
        });
    });
}

// Add ripple animation keyframes
function addRippleAnimation() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes rippleEffect {
            0% {
                transform: translate(-50%, -50%) scale(0);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -50%) scale(20);
                opacity: 0;
            }
        }
        
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        
        .liquid-glass-shimmer {
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.2),
                transparent
            );
            background-size: 200% 100%;
            animation: shimmer 2s infinite;
        }
    `;
    document.head.appendChild(style);
}

// Enhanced form validation with glass effects
function enhanceFormValidation() {
    const form = document.querySelector('form');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        const inputs = form.querySelectorAll('.liquid-glass-input');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
                input.style.borderColor = 'rgba(239, 68, 68, 0.5)';
                input.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
                
                // Shake animation
                input.style.animation = 'shake 0.5s ease-in-out';
                setTimeout(() => {
                    input.style.animation = '';
                }, 500);
            } else {
                input.style.borderColor = 'rgba(34, 197, 94, 0.5)';
                input.style.boxShadow = '0 0 0 3px rgba(34, 197, 94, 0.1)';
            }
        });
        
        if (!isValid) {
            e.preventDefault();
        }
    });
}

// Add shake animation
function addShakeAnimation() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
    `;
    document.head.appendChild(style);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add required animations
    addRippleAnimation();
    addShakeAnimation();
    
    // Initialize liquid glass containers
    const containers = document.querySelectorAll('.liquid-glass-container');
    containers.forEach(container => {
        new LiquidGlass(container);
    });
    
    // Enhance inputs and form
    enhanceInputs();
    enhanceFormValidation();
    
    // Add loading shimmer effect to form elements
    setTimeout(() => {
        document.querySelectorAll('.liquid-glass-input, .liquid-glass-button').forEach(el => {
            el.classList.add('liquid-glass-shimmer');
            setTimeout(() => {
                el.classList.remove('liquid-glass-shimmer');
            }, 2000);
        });
    }, 500);
    
    // Add smooth scroll reveal effect
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    });
    
    containers.forEach(container => {
        container.style.opacity = '0';
        container.style.transform = 'translateY(30px)';
        container.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
        observer.observe(container);
    });
});

// Export for module use if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LiquidGlass;
} 