/**
 * IntelliWeather - Motion Controller
 * 
 * Advanced animation sequencing and coordination system
 * Supports cancellation, interruption, and reduced motion preferences
 */

class MotionController {
    constructor() {
        this.activeAnimations = new Map();
        this.prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        
        // Listen for motion preference changes
        window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
            this.prefersReducedMotion = e.matches;
        });
    }
    
    /**
     * Animation tokens - consistent timing across the app
     */
    static TOKENS = {
        duration: {
            instant: 100,
            fast: 150,
            normal: 300,
            slow: 500,
            slower: 800,
            slowest: 1200
        },
        easing: {
            linear: 'linear',
            easeOut: 'cubic-bezier(0.16, 1, 0.3, 1)',
            easeInOut: 'cubic-bezier(0.87, 0, 0.13, 1)',
            easeOutBack: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
            bounce: 'cubic-bezier(0.68, -0.6, 0.32, 1.6)',
            smooth: 'cubic-bezier(0.4, 0, 0.2, 1)'
        },
        stagger: {
            xs: 30,
            sm: 50,
            md: 80,
            lg: 120
        }
    };
    
    /**
     * Create a cancellable animation promise
     */
    animate(element, keyframes, options = {}) {
        if (this.prefersReducedMotion) {
            // Apply final state immediately
            if (keyframes.length > 0) {
                const finalFrame = keyframes[keyframes.length - 1];
                Object.assign(element.style, finalFrame);
            }
            return Promise.resolve();
        }
        
        const animation = element.animate(keyframes, {
            duration: options.duration || MotionController.TOKENS.duration.normal,
            easing: options.easing || MotionController.TOKENS.easing.easeOut,
            fill: 'forwards',
            ...options
        });
        
        const id = Symbol('animation');
        this.activeAnimations.set(id, animation);
        
        return new Promise((resolve, reject) => {
            animation.onfinish = () => {
                this.activeAnimations.delete(id);
                resolve();
            };
            animation.oncancel = () => {
                this.activeAnimations.delete(id);
                reject(new Error('Animation cancelled'));
            };
        });
    }
    
    /**
     * Cancel all active animations
     */
    cancelAll() {
        this.activeAnimations.forEach(animation => animation.cancel());
        this.activeAnimations.clear();
    }
    
    /**
     * Fade in animation
     */
    fadeIn(element, options = {}) {
        element.style.opacity = '0';
        return this.animate(element, [
            { opacity: 0 },
            { opacity: 1 }
        ], { duration: MotionController.TOKENS.duration.normal, ...options });
    }
    
    /**
     * Fade out animation
     */
    fadeOut(element, options = {}) {
        return this.animate(element, [
            { opacity: 1 },
            { opacity: 0 }
        ], { duration: MotionController.TOKENS.duration.fast, ...options });
    }
    
    /**
     * Slide in from direction
     */
    slideIn(element, direction = 'up', options = {}) {
        const transforms = {
            up: 'translateY(30px)',
            down: 'translateY(-30px)',
            left: 'translateX(30px)',
            right: 'translateX(-30px)'
        };
        
        element.style.opacity = '0';
        element.style.transform = transforms[direction];
        
        return this.animate(element, [
            { opacity: 0, transform: transforms[direction] },
            { opacity: 1, transform: 'translate(0)' }
        ], { duration: MotionController.TOKENS.duration.slow, ...options });
    }
    
    /**
     * Scale in with optional bounce
     */
    scaleIn(element, bounce = false, options = {}) {
        element.style.opacity = '0';
        element.style.transform = 'scale(0.9)';
        
        const keyframes = bounce ? [
            { opacity: 0, transform: 'scale(0.8)' },
            { opacity: 1, transform: 'scale(1.05)' },
            { opacity: 1, transform: 'scale(1)' }
        ] : [
            { opacity: 0, transform: 'scale(0.9)' },
            { opacity: 1, transform: 'scale(1)' }
        ];
        
        return this.animate(element, keyframes, { 
            duration: bounce ? MotionController.TOKENS.duration.slower : MotionController.TOKENS.duration.normal,
            easing: bounce ? MotionController.TOKENS.easing.bounce : MotionController.TOKENS.easing.easeOut,
            ...options 
        });
    }
    
    /**
     * Stagger animation for multiple elements
     */
    async staggerIn(elements, animation = 'fadeIn', staggerDelay = MotionController.TOKENS.stagger.sm) {
        if (this.prefersReducedMotion) {
            elements.forEach(el => el.style.opacity = '1');
            return;
        }
        
        const promises = Array.from(elements).map((element, index) => {
            return new Promise(resolve => {
                setTimeout(() => {
                    this[animation](element).then(resolve).catch(resolve);
                }, index * staggerDelay);
            });
        });
        
        return Promise.all(promises);
    }
    
    /**
     * Page transition - exit current, enter new
     */
    async pageTransition(exitElement, enterElement) {
        if (this.prefersReducedMotion) {
            if (exitElement) exitElement.style.display = 'none';
            if (enterElement) enterElement.style.display = 'block';
            return;
        }
        
        // Exit animation
        if (exitElement) {
            await this.animate(exitElement, [
                { opacity: 1, transform: 'translateY(0)' },
                { opacity: 0, transform: 'translateY(-20px)' }
            ], { duration: MotionController.TOKENS.duration.normal });
            exitElement.style.display = 'none';
        }
        
        // Enter animation
        if (enterElement) {
            enterElement.style.display = 'block';
            await this.animate(enterElement, [
                { opacity: 0, transform: 'translateY(30px)' },
                { opacity: 1, transform: 'translateY(0)' }
            ], { duration: MotionController.TOKENS.duration.slow });
        }
    }
    
    /**
     * Coordinated sequence for loading states
     * search -> loading skeleton -> results reveal
     */
    async loadingSequence(searchInput, skeletonContainer, resultsContainer, loadData) {
        // 1. Show skeleton
        if (skeletonContainer) {
            skeletonContainer.style.display = 'block';
            this.fadeIn(skeletonContainer);
        }
        
        // 2. Load data
        let data;
        try {
            data = await loadData();
        } catch (error) {
            if (skeletonContainer) {
                await this.fadeOut(skeletonContainer);
                skeletonContainer.style.display = 'none';
            }
            throw error;
        }
        
        // 3. Hide skeleton
        if (skeletonContainer) {
            await this.fadeOut(skeletonContainer);
            skeletonContainer.style.display = 'none';
        }
        
        // 4. Show results with stagger
        if (resultsContainer) {
            resultsContainer.style.display = 'block';
            const items = resultsContainer.children;
            await this.staggerIn(items, 'slideIn');
        }
        
        return data;
    }
    
    /**
     * Weather card flip transition
     */
    async cardFlip(card, updateContent) {
        if (this.prefersReducedMotion) {
            updateContent();
            return;
        }
        
        // Flip out
        await this.animate(card, [
            { transform: 'perspective(1000px) rotateY(0deg)' },
            { transform: 'perspective(1000px) rotateY(90deg)' }
        ], { duration: MotionController.TOKENS.duration.normal });
        
        // Update content at midpoint
        updateContent();
        
        // Flip in
        await this.animate(card, [
            { transform: 'perspective(1000px) rotateY(90deg)' },
            { transform: 'perspective(1000px) rotateY(0deg)' }
        ], { duration: MotionController.TOKENS.duration.normal });
    }
    
    /**
     * Shake animation for errors
     */
    shake(element) {
        return this.animate(element, [
            { transform: 'translateX(0)' },
            { transform: 'translateX(-10px)' },
            { transform: 'translateX(10px)' },
            { transform: 'translateX(-10px)' },
            { transform: 'translateX(10px)' },
            { transform: 'translateX(0)' }
        ], { duration: MotionController.TOKENS.duration.slow });
    }
    
    /**
     * Pulse animation for attention
     */
    pulse(element, count = 2) {
        const keyframes = [];
        for (let i = 0; i < count; i++) {
            keyframes.push(
                { transform: 'scale(1)', offset: i / count },
                { transform: 'scale(1.1)', offset: (i + 0.5) / count }
            );
        }
        keyframes.push({ transform: 'scale(1)' });
        
        return this.animate(element, keyframes, { 
            duration: MotionController.TOKENS.duration.slower * count 
        });
    }
}

// Create global instance
window.motionController = new MotionController();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MotionController;
}
