/**
 * IntelliWeather - Search Component
 * 
 * Enhanced search with autosuggest, keyboard navigation, and animations
 */

class SearchController {
    constructor(options = {}) {
        this.input = document.querySelector(options.inputSelector || '#city-search');
        this.resultsContainer = document.querySelector(options.resultsSelector || '#search-results');
        this.apiBaseUrl = options.apiBaseUrl || window.location.origin;
        
        this.debounceTimeout = null;
        this.debounceDelay = options.debounceDelay || 300;
        this.minQueryLength = options.minQueryLength || 2;
        this.maxResults = options.maxResults || 5;
        
        this.selectedIndex = -1;
        this.results = [];
        this.isLoading = false;
        
        this.onSelect = options.onSelect || (() => {});
        
        this.init();
    }
    
    init() {
        if (!this.input || !this.resultsContainer) {
            console.warn('Search: Missing required elements');
            return;
        }
        
        // Input events
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('focus', () => this.handleFocus());
        this.input.addEventListener('blur', () => this.handleBlur());
        
        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                this.close();
            }
        });
        
        // Results container events
        this.resultsContainer.addEventListener('click', (e) => this.handleResultClick(e));
        this.resultsContainer.addEventListener('mouseenter', (e) => this.handleResultHover(e), true);
    }
    
    handleInput(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        clearTimeout(this.debounceTimeout);
        
        if (query.length < this.minQueryLength) {
            this.close();
            return;
        }
        
        // Show loading state
        this.showLoading();
        
        // Debounce the search
        this.debounceTimeout = setTimeout(() => {
            this.search(query);
        }, this.debounceDelay);
    }
    
    handleKeydown(e) {
        if (!this.results.length) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectNext();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectPrevious();
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0) {
                    this.selectResult(this.results[this.selectedIndex]);
                }
                break;
            case 'Escape':
                this.close();
                this.input.blur();
                break;
        }
    }
    
    handleFocus() {
        if (this.results.length) {
            this.renderResults();
        }
    }
    
    handleBlur() {
        // Delay to allow click events on results
        setTimeout(() => {
            if (!this.resultsContainer.matches(':hover')) {
                this.close();
            }
        }, 150);
    }
    
    handleResultClick(e) {
        const item = e.target.closest('.search-item');
        if (item && item.dataset.index !== undefined) {
            const index = parseInt(item.dataset.index);
            this.selectResult(this.results[index]);
        }
    }
    
    handleResultHover(e) {
        const item = e.target.closest('.search-item');
        if (item && item.dataset.index !== undefined) {
            this.selectedIndex = parseInt(item.dataset.index);
            this.highlightSelected();
        }
    }
    
    async search(query) {
        this.isLoading = true;
        
        try {
            // Use our geocoding endpoint if available, fallback to Open-Meteo
            const response = await fetch(
                `${this.apiBaseUrl}/geocode/search?q=${encodeURIComponent(query)}&limit=${this.maxResults}`,
                { signal: AbortSignal.timeout(5000) }
            ).catch(() => 
                fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=${this.maxResults}`,
                    { signal: AbortSignal.timeout(5000) }
                )
            );
            
            const data = await response.json();
            
            // Normalize response format
            if (data.results) {
                this.results = data.results.map(r => ({
                    name: r.name,
                    admin: r.admin1 || r.admin || '',
                    country: r.country || '',
                    lat: r.latitude || r.lat,
                    lon: r.longitude || r.lon,
                    timezone: r.timezone || ''
                }));
            } else if (Array.isArray(data)) {
                this.results = data;
            } else {
                this.results = [];
            }
            
            this.selectedIndex = -1;
            this.renderResults();
        } catch (error) {
            console.error('Search error:', error);
            this.showError();
        } finally {
            this.isLoading = false;
        }
    }
    
    showLoading() {
        this.resultsContainer.innerHTML = `
            <div class="search-loading">
                <div class="search-loading-spinner"></div>
                <span>Searching...</span>
            </div>
        `;
        this.resultsContainer.style.display = 'block';
        
        // Animate in
        if (window.motionController) {
            window.motionController.fadeIn(this.resultsContainer);
        }
    }
    
    showError() {
        this.resultsContainer.innerHTML = `
            <div class="search-item search-error">
                <span class="search-error-icon">⚠️</span>
                <span>Unable to search. Please try again.</span>
            </div>
        `;
    }
    
    renderResults() {
        if (!this.results.length) {
            this.resultsContainer.innerHTML = `
                <div class="search-item search-no-results">
                    <span class="search-icon">🔍</span>
                    <span>No locations found</span>
                </div>
            `;
            this.resultsContainer.style.display = 'block';
            return;
        }
        
        this.resultsContainer.innerHTML = this.results.map((result, index) => `
            <div class="search-item ${index === this.selectedIndex ? 'selected' : ''}" 
                 data-index="${index}"
                 role="option"
                 aria-selected="${index === this.selectedIndex}">
                <div class="search-item-icon">📍</div>
                <div class="search-item-content">
                    <div class="search-item-name">${this.escapeHtml(result.name)}</div>
                    <div class="search-item-detail">
                        ${result.admin ? this.escapeHtml(result.admin) + ', ' : ''}${this.escapeHtml(result.country)}
                    </div>
                </div>
                <div class="search-item-arrow">→</div>
            </div>
        `).join('');
        
        this.resultsContainer.style.display = 'block';
        
        // Animate items
        if (window.motionController) {
            const items = this.resultsContainer.querySelectorAll('.search-item');
            window.motionController.staggerIn(items, 'slideIn');
        }
    }
    
    selectNext() {
        if (this.selectedIndex < this.results.length - 1) {
            this.selectedIndex++;
            this.highlightSelected();
        }
    }
    
    selectPrevious() {
        if (this.selectedIndex > 0) {
            this.selectedIndex--;
            this.highlightSelected();
        }
    }
    
    highlightSelected() {
        const items = this.resultsContainer.querySelectorAll('.search-item');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedIndex);
            item.setAttribute('aria-selected', index === this.selectedIndex);
        });
        
        // Scroll into view if needed
        if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
            items[this.selectedIndex].scrollIntoView({ block: 'nearest' });
        }
    }
    
    selectResult(result) {
        if (!result) return;
        
        // Update input
        this.input.value = `${result.name}, ${result.country}`;
        
        // Close dropdown
        this.close();
        
        // Callback
        this.onSelect(result);
    }
    
    close() {
        this.resultsContainer.style.display = 'none';
        this.resultsContainer.innerHTML = '';
        this.selectedIndex = -1;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Auto-initialize if elements exist
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('#city-search');
    if (searchInput) {
        window.searchController = new SearchController({
            onSelect: (result) => {
                // Trigger weather fetch
                if (typeof fetchAllWeatherData === 'function') {
                    fetchAllWeatherData(result.lat, result.lon, `${result.name}, ${result.country}`);
                }
            }
        });
    }
});

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchController;
}
