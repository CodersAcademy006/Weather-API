/**
 * IntelliWeather - Theme Manager
 * 
 * Handles dark/light mode toggle with persistence
 */

class ThemeManager {
    constructor() {
        this.STORAGE_KEY = 'intelliweather-theme';
        this.THEMES = ['light', 'dark'];
        this.currentTheme = this.loadTheme();
        this.init();
    }
    
    init() {
        // Apply theme immediately to prevent flash
        this.applyTheme(this.currentTheme);
        
        // Listen for system preference changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.STORAGE_KEY)) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
    
    loadTheme() {
        // Check localStorage first
        const stored = localStorage.getItem(this.STORAGE_KEY);
        if (stored && this.THEMES.includes(stored)) {
            return stored;
        }
        
        // Check system preference
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        
        return 'light';
    }
    
    applyTheme(theme) {
        // Prevent transition flash on initial load
        document.documentElement.classList.add('no-transitions');
        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        
        // Update meta theme-color for mobile browsers
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.content = theme === 'dark' ? '#0f172a' : '#ffffff';
        }
        
        // Re-enable transitions after a frame
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                document.documentElement.classList.remove('no-transitions');
            });
        });
        
        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    }
    
    toggle() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        return newTheme;
    }
    
    setTheme(theme) {
        if (!this.THEMES.includes(theme)) {
            console.warn(`Invalid theme: ${theme}`);
            return;
        }
        
        localStorage.setItem(this.STORAGE_KEY, theme);
        this.applyTheme(theme);
    }
    
    getTheme() {
        return this.currentTheme;
    }
    
    isDark() {
        return this.currentTheme === 'dark';
    }
}

// Create global instance
window.themeManager = new ThemeManager();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeManager;
}
