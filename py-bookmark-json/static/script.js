// Global variables
let bookmarksData = {};
let selectedSections = ['all'];

// Icon mappings
const categoryIcons = {
    'development': 'fas fa-code',
    'tools': 'fas fa-wrench',
    'learning': 'fas fa-graduation-cap',
    'design': 'fas fa-paint-brush',
    'api': 'fas fa-plug',
    'database': 'fas fa-database',
    'cloud': 'fas fa-cloud',
    'security': 'fas fa-shield-alt',
    'infrastructure': 'fas fa-server',
    'monitoring': 'fas fa-chart-line',
    'support': 'fas fa-headset',
    'documentation': 'fas fa-book',
    'default': 'fas fa-bookmark'
};

const sectionIcons = {
    'common': 'fas fa-star',
    'application': 'fas fa-desktop',
    'app': 'fas fa-mobile-alt',
    'links': 'fas fa-link',
    'default': 'fas fa-layer-group'
};

// Enhanced preferences management
const PREFERENCES_KEY = 'bookmarks-preferences';

function getDefaultPreferences() {
    return {
        theme: window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark',
        selectedSections: ['all'],
        lastVisited: new Date().toISOString(),
        openCount: 0,
        favoriteFilters: [],
        windowSize: {
            width: window.innerWidth,
            height: window.innerHeight
        }
    };
}

function loadPreferences() {
    try {
        const saved = localStorage.getItem(PREFERENCES_KEY);
        if (saved) {
            const preferences = JSON.parse(saved);
            // Merge with defaults to handle new preference keys
            return { ...getDefaultPreferences(), ...preferences };
        }
    } catch (error) {
        console.warn('Failed to load preferences:', error);
    }
    return getDefaultPreferences();
}

function savePreferences(updates = {}) {
    try {
        const current = loadPreferences();
        const updated = {
            ...current,
            ...updates,
            lastVisited: new Date().toISOString()
        };
        
        localStorage.setItem(PREFERENCES_KEY, JSON.stringify(updated));
        
        // Also save to cookies as backup
        const expiry = new Date();
        expiry.setFullYear(expiry.getFullYear() + 1);
        document.cookie = `${PREFERENCES_KEY}=${JSON.stringify(updated)}; expires=${expiry.toUTCString()}; path=/`;
        
        console.log('Preferences saved:', updated);
    } catch (error) {
        console.warn('Failed to save preferences:', error);
    }
}

function restorePreferences() {
    const preferences = loadPreferences();
    
    // Restore theme
    setTheme(preferences.theme);
    updateThemeToggleIcon(preferences.theme);
    
    // Restore selected sections (will be applied when data loads)
    selectedSections = preferences.selectedSections || ['all'];
    
    // Update open count
    savePreferences({ openCount: (preferences.openCount || 0) + 1 });
    
    console.log('Preferences restored:', preferences);
    showToast(`Welcome back! Settings restored.`, 'success');
}

// Enhanced theme management
function initializeTheme() {
    const preferences = loadPreferences();
    setTheme(preferences.theme);
    updateThemeToggleIcon(preferences.theme);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    savePreferences({ theme: theme });
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    updateThemeToggleIcon(newTheme);
    showToast(`Switched to ${newTheme} theme`);
}

function updateThemeToggleIcon(theme) {
    const themeToggle = document.getElementById('themeToggle');
    if (!themeToggle) return;
    
    const icon = themeToggle.querySelector('i');
    if (icon) {
        icon.className = theme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
        themeToggle.title = theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme';
    }
}

// Icon selection
function getIconForCategory(category) {
    const categoryLower = category.toLowerCase();
    for (const key in categoryIcons) {
        if (categoryLower.includes(key)) {
            return categoryIcons[key];
        }
    }
    return categoryIcons.default;
}

function getIconForSection(section) {
    const sectionLower = section.toLowerCase();
    for (const key in sectionIcons) {
        if (sectionLower.includes(key)) {
            return sectionIcons[key];
        }
    }
    return sectionIcons.default;
}

// Load bookmarks from API
async function loadBookmarks() {
    try {
        const response = await fetch('/api/bookmarks');
        if (!response.ok) throw new Error('Failed to load bookmarks');
        
        bookmarksData = await response.json();
        console.log('Loaded bookmarks:', bookmarksData);
        
        renderSections();
        restoreSelectedSections(); // Apply saved section preferences
        renderBookmarks();
        updateBulkOpenButton();
    } catch (error) {
        console.error('Error loading bookmarks:', error);
        showToast('Error loading bookmarks', 'error');
    }
}

// Render section filter buttons
function renderSections() {
    const sectionContainer = document.getElementById('sectionContainer');
    if (!sectionContainer) return;
    
    // Remove existing buttons except "All Sections"
    const existingBtns = sectionContainer.querySelectorAll('[data-section]:not([data-section="all"])');
    existingBtns.forEach(btn => btn.remove());
    
    // Add section buttons
    Object.keys(bookmarksData).forEach(section => {
        const btn = document.createElement('button');
        btn.className = 'section-btn';
        btn.dataset.section = section;
        
        const displayName = section.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        btn.innerHTML = `<i class="${getIconForSection(section)}"></i> ${displayName}`;
        btn.addEventListener('click', () => toggleSection(section));
        sectionContainer.appendChild(btn);
    });
}

// Restore selected sections from preferences
function restoreSelectedSections() {
    const preferences = loadPreferences();
    selectedSections = preferences.selectedSections || ['all'];
    
    // Update button states
    document.querySelectorAll('.section-btn').forEach(btn => {
        const section = btn.dataset.section;
        if (selectedSections.includes(section) || (selectedSections.includes('all') && section === 'all')) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    console.log('Restored selected sections:', selectedSections);
}

// Enhanced section toggle with preferences saving
function toggleSection(section) {
    const btn = document.querySelector(`[data-section="${section}"]`);
    const allBtn = document.querySelector('[data-section="all"]');
    
    if (!btn || !allBtn) return;
    
    if (section === 'all') {
        selectedSections = ['all'];
        document.querySelectorAll('.section-btn').forEach(b => b.classList.remove('active'));
        allBtn.classList.add('active');
    } else {
        if (selectedSections.includes('all')) {
            selectedSections = [];
            allBtn.classList.remove('active');
        }
        
        if (selectedSections.includes(section)) {
            selectedSections = selectedSections.filter(s => s !== section);
            btn.classList.remove('active');
        } else {
            selectedSections.push(section);
            btn.classList.add('active');
        }
        
        if (selectedSections.length === 0) {
            selectedSections = ['all'];
            allBtn.classList.add('active');
        }
    }
    
    // Save section preferences
    savePreferences({ selectedSections: selectedSections });
    
    renderBookmarks();
    updateBulkOpenButton();
}

// Render bookmarks in section columns
function renderBookmarks() {
    const container = document.getElementById('mainContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    Object.entries(bookmarksData).forEach(([sectionName, sectionData]) => {
        if (!selectedSections.includes('all') && !selectedSections.includes(sectionName)) {
            return;
        }
        
        if (!sectionData || typeof sectionData !== 'object') return;
        
        // Create section column
        const sectionColumn = document.createElement('div');
        sectionColumn.className = 'section-column';
        
        // Section header with bulk open button
        const sectionHeader = document.createElement('div');
        sectionHeader.className = 'section-header';
        const displayName = sectionName.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        // Count total bookmarks in this section
        const sectionBookmarkCount = Object.values(sectionData).reduce((total, links) => {
            return total + (links && typeof links === 'object' ? Object.keys(links).length : 0);
        }, 0);
        
        sectionHeader.innerHTML = `
            <h2><i class="${getIconForSection(sectionName)}"></i> ${displayName}</h2>
            <button class="section-bulk-btn" onclick="openSectionBookmarks(this, '${sectionName}')" title="Open all bookmarks in this section">
                <i class="fas fa-external-link-alt"></i> Open Section (${sectionBookmarkCount})
            </button>
        `;
        sectionColumn.appendChild(sectionHeader);
        
        // Add categories
        Object.entries(sectionData).forEach(([categoryName, links]) => {
            if (!links || typeof links !== 'object') return;
            
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'category';
            
            // Category header with title and bulk open button
            const categoryHeader = document.createElement('div');
            categoryHeader.className = 'category-header';
            
            const categoryTitle = document.createElement('div');
            categoryTitle.className = 'category-title';
            categoryTitle.innerHTML = `<i class="${getIconForCategory(categoryName)}"></i> ${categoryName}`;
            
            const categoryBulkBtn = document.createElement('button');
            categoryBulkBtn.className = 'category-bulk-btn';
            categoryBulkBtn.innerHTML = `<i class="fas fa-external-link-alt"></i> Open (${Object.keys(links).length})`;
            categoryBulkBtn.title = 'Open all bookmarks in this category';
            categoryBulkBtn.addEventListener('click', () => openCategoryBookmarks(sectionName, categoryName));
            
            categoryHeader.appendChild(categoryTitle);
            categoryHeader.appendChild(categoryBulkBtn);
            categoryDiv.appendChild(categoryHeader);
            
            // Add bookmarks
            Object.entries(links).forEach(([linkName, url]) => {
                if (typeof url !== 'string') return;
                
                const bookmarkItem = document.createElement('div');
                bookmarkItem.className = 'bookmark-item';
                
                const link = document.createElement('a');
                link.className = 'bookmark-link';
                link.href = url;
                link.target = '_blank';
                link.innerHTML = `<i class="fas fa-external-link-alt"></i> ${linkName}`;
                link.dataset.url = url;
                link.dataset.section = sectionName;
                link.dataset.category = categoryName;
                
                const actions = document.createElement('div');
                actions.className = 'bookmark-actions';
                
                const copyBtn = document.createElement('button');
                copyBtn.className = 'action-btn';
                copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                copyBtn.title = 'Copy link';
                copyBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    copyToClipboard(url);
                });
                
                actions.appendChild(copyBtn);
                bookmarkItem.appendChild(link);
                bookmarkItem.appendChild(actions);
                categoryDiv.appendChild(bookmarkItem);
            });
            
            if (categoryDiv.children.length > 1) {
                sectionColumn.appendChild(categoryDiv);
            }
        });
        
        if (sectionColumn.children.length > 1) {
            container.appendChild(sectionColumn);
        }
    });
}

// Update bulk open button
function updateBulkOpenButton() {
    const bulkOpenBtn = document.getElementById('bulkOpenBtn');
    if (!bulkOpenBtn) return;
    
    const visibleLinks = document.querySelectorAll('.bookmark-link');
    
    if (visibleLinks.length > 1) {
        bulkOpenBtn.style.display = 'flex';
        bulkOpenBtn.innerHTML = `<i class="fas fa-external-link-alt"></i> Open All (${visibleLinks.length})`;
    } else {
        bulkOpenBtn.style.display = 'none';
    }
}

// Open all bookmarks
function openAllBookmarks() {
    const visibleLinks = document.querySelectorAll('.bookmark-link');
    const urls = Array.from(visibleLinks)
        .map(link => link.dataset.url)
        .filter(url => url && typeof url === 'string');
    
    if (urls.length === 0) {
        showToast('No bookmarks to open', 'error');
        return;
    }
    
    if (urls.length > 10) {
        const confirmed = confirm(`This will open ${urls.length} tabs. Continue?`);
        if (!confirmed) return;
    }
    
    urls.forEach((url, index) => {
        setTimeout(() => window.open(url, '_blank'), index * 100);
    });
    
    // Update usage statistics
    const preferences = loadPreferences();
    savePreferences({ 
        lastBulkOpen: new Date().toISOString(),
        totalBookmarksOpened: (preferences.totalBookmarksOpened || 0) + urls.length
    });
    
    showToast(`Opened ${urls.length} bookmarks!`);
}

// Open all bookmarks in a specific section
function openSectionBookmarks(buttonElement, sectionName) {
    const sectionLinks = document.querySelectorAll(`[data-section="${sectionName}"]`);
    const urls = Array.from(sectionLinks)
        .map(link => link.dataset.url)
        .filter(url => url && typeof url === 'string');
    
    if (urls.length === 0) {
        showToast('No bookmarks found in this section', 'error');
        return;
    }
    
    if (urls.length > 10) {
        const confirmed = confirm(`This will open ${urls.length} tabs from "${sectionName}". Continue?`);
        if (!confirmed) return;
    }
    
    urls.forEach((url, index) => {
        setTimeout(() => window.open(url, '_blank'), index * 100);
    });
    
    // Update usage statistics
    const preferences = loadPreferences();
    savePreferences({ 
        lastSectionOpened: sectionName,
        totalBookmarksOpened: (preferences.totalBookmarksOpened || 0) + urls.length
    });
    
    const displayName = sectionName.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    showToast(`Opened ${urls.length} bookmarks from ${displayName}!`);
}

// Open all bookmarks in a specific category
function openCategoryBookmarks(sectionName, categoryName) {
    const categoryLinks = document.querySelectorAll(`[data-section="${sectionName}"][data-category="${categoryName}"]`);
    const urls = Array.from(categoryLinks)
        .map(link => link.dataset.url)
        .filter(url => url && typeof url === 'string');
    
    if (urls.length === 0) {
        showToast('No bookmarks found in this category', 'error');
        return;
    }
    
    if (urls.length > 10) {
        const confirmed = confirm(`This will open ${urls.length} tabs from "${categoryName}". Continue?`);
        if (!confirmed) return;
    }
    
    urls.forEach((url, index) => {
        setTimeout(() => window.open(url, '_blank'), index * 100);
    });
    
    // Update usage statistics
    const preferences = loadPreferences();
    savePreferences({ 
        lastCategoryOpened: `${sectionName} > ${categoryName}`,
        totalBookmarksOpened: (preferences.totalBookmarksOpened || 0) + urls.length
    });
    
    showToast(`Opened ${urls.length} bookmarks from ${categoryName}!`);
}

// Copy to clipboard
function copyToClipboard(text) {
    if (!text) return;
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text)
            .then(() => showToast('Link copied!'))
            .catch(() => fallbackCopyTextToClipboard(text));
    } else {
        fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        showToast(successful ? 'Link copied!' : 'Failed to copy link', successful ? 'success' : 'error');
    } catch (err) {
        showToast('Failed to copy link', 'error');
    }
    
    document.body.removeChild(textArea);
}

// Enhanced toast with preferences tracking
function showToast(message = 'Link copied!', type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = 'toast';
    
    if (type === 'error') {
        toast.style.background = '#dc3545';
        toast.style.color = '#ffffff';
    } else {
        toast.style.background = 'var(--toast-bg)';
        toast.style.color = 'var(--toast-text)';
    }
    
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
    
    // Track toast usage
    const preferences = loadPreferences();
    savePreferences({ 
        lastToastMessage: message,
        toastCount: (preferences.toastCount || 0) + 1
    });
}

// Window size tracking
function trackWindowResize() {
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            savePreferences({
                windowSize: {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            });
        }, 500);
    });
}

// Enhanced initialization with comprehensive preference restoration and Gist import
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing bookmark application with preferences...');
    
    // Initialize theme and restore preferences
    initializeTheme();
    restorePreferences();
    
    // Load bookmarks (will apply saved section preferences)
    loadBookmarks();
    
    // Track window resizing
    trackWindowResize();
    
    // Event listeners
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
        console.log('Theme toggle event listener added');
    }
    
    const bulkOpenBtn = document.getElementById('bulkOpenBtn');
    if (bulkOpenBtn) {
        bulkOpenBtn.addEventListener('click', openAllBookmarks);
        console.log('Bulk open event listener added');
    }
    
    // Import functionality
    const importBtn = document.getElementById('importBtn');
    if (importBtn) {
        importBtn.addEventListener('click', showImportModal);
        console.log('Import button event listener added');
    } else {
        console.warn('Import button not found');
    }
    
    const importModal = document.getElementById('importModal');
    const modalClose = document.getElementById('modalClose');
    const cancelImport = document.getElementById('cancelImport');
    const confirmImport = document.getElementById('confirmImport');
    
    if (modalClose) {
        modalClose.addEventListener('click', hideImportModal);
        console.log('Modal close event listener added');
    }
    
    if (cancelImport) {
        cancelImport.addEventListener('click', hideImportModal);
        console.log('Cancel import event listener added');
    }
    
    if (confirmImport) {
        confirmImport.addEventListener('click', importFromGist);
        console.log('Confirm import event listener added');
    }
    
    // Close modal on overlay click
    if (importModal) {
        importModal.addEventListener('click', (e) => {
            if (e.target === importModal) {
                hideImportModal();
            }
        });
        console.log('Modal overlay event listener added');
    }
    
    // Add keyboard support for modal
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById('importModal');
        if (modal && modal.style.display === 'flex') {
            if (e.key === 'Escape') {
                hideImportModal();
            } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                importFromGist();
            }
        }
    });
    
    // System theme change listener
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
            const preferences = loadPreferences();
            // Only auto-switch if user hasn't manually set a theme recently
            const lastManualThemeChange = preferences.lastManualThemeChange;
            const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
            
            if (!lastManualThemeChange || new Date(lastManualThemeChange) < oneHourAgo) {
                const newTheme = e.matches ? 'light' : 'dark';
                setTheme(newTheme);
                updateThemeToggleIcon(newTheme);
                showToast(`Auto-switched to ${newTheme} theme`);
            }
        });
    }
    
    // Track manual theme changes
    document.addEventListener('click', (e) => {
        if (e.target.closest('#themeToggle')) {
            savePreferences({ lastManualThemeChange: new Date().toISOString() });
        }
    });
    
    // Save preferences on page unload
    window.addEventListener('beforeunload', () => {
        savePreferences({ lastExit: new Date().toISOString() });
    });
    
    console.log('Bookmark application initialized with full preference management');
});

// Gist import functionality
function showImportModal() {
    console.log('showImportModal called');
    const modal = document.getElementById('importModal');
    if (modal) {
        modal.style.display = 'flex';
        console.log('Modal displayed');
        // Focus on the URL input
        const gistUrl = document.getElementById('gistUrl');
        if (gistUrl) {
            setTimeout(() => {
                gistUrl.focus();
                console.log('URL input focused');
            }, 100);
        }
    } else {
        console.error('Import modal not found');
    }
}

function hideImportModal() {
    console.log('hideImportModal called');
    const modal = document.getElementById('importModal');
    if (modal) {
        modal.style.display = 'none';
        // Clear inputs
        const gistUrl = document.getElementById('gistUrl');
        const gistFile = document.getElementById('gistFile');
        if (gistUrl) gistUrl.value = '';
        if (gistFile) gistFile.value = '';
        console.log('Modal hidden and inputs cleared');
    }
}

function extractGistId(input) {
    console.log('Extracting Gist ID from:', input);
    
    // Handle full URL: https://gist.github.com/username/gist-id
    const urlMatch = input.match(/gist\.github\.com\/[^\/]+\/([a-f0-9]+)/);
    if (urlMatch) {
        console.log('Found Gist ID from full URL:', urlMatch[1]);
        return urlMatch[1];
    }
    
    // Handle raw URL: https://gist.githubusercontent.com/username/gist-id/raw/...
    const rawMatch = input.match(/gist\.githubusercontent\.com\/[^\/]+\/([a-f0-9]+)/);
    if (rawMatch) {
        console.log('Found Gist ID from raw URL:', rawMatch[1]);
        return rawMatch[1];
    }
    
    // Handle just the ID: gist-id
    const idMatch = input.match(/^([a-f0-9]+)$/);
    if (idMatch) {
        console.log('Found Gist ID from direct input:', idMatch[1]);
        return idMatch[1];
    }
    
    console.log('No valid Gist ID found');
    return null;
}

async function importFromGist() {
    const gistUrlInput = document.getElementById('gistUrl');
    const gistFileInput = document.getElementById('gistFile');
    const confirmBtn = document.getElementById('confirmImport');
    
    if (!gistUrlInput || !confirmBtn) return;
    
    const gistInput = gistUrlInput.value.trim();
    const fileName = gistFileInput.value.trim();
    
    if (!gistInput) {
        showToast('Please enter a Gist URL or ID', 'error');
        return;
    }
    
    const gistId = extractGistId(gistInput);
    if (!gistId) {
        showToast('Invalid Gist URL or ID format', 'error');
        return;
    }
    
    // Show loading state
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...';
    
    try {
        // Try client-side import first (GitHub API)
        const gistResponse = await fetch(`https://api.github.com/gists/${gistId}`);
        
        if (!gistResponse.ok) {
            throw new Error(`Failed to fetch Gist: ${gistResponse.status}`);
        }
        
        const gistData = await gistResponse.json();
        const files = gistData.files;
        
        let targetFile = null;
        
        // Find the target file
        if (fileName) {
            // User specified a file name
            targetFile = files[fileName];
            if (!targetFile) {
                throw new Error(`File "${fileName}" not found in Gist`);
            }
        } else {
            // Find first JSON file
            const jsonFiles = Object.values(files).filter(file => 
                file.filename.endsWith('.json') || 
                file.type === 'application/json' ||
                file.language === 'JSON'
            );
            
            if (jsonFiles.length === 0) {
                throw new Error('No JSON files found in Gist');
            }
            
            targetFile = jsonFiles[0];
        }
        
        // Parse and validate the JSON content
        let bookmarkData;
        try {
            bookmarkData = JSON.parse(targetFile.content);
        } catch (parseError) {
            throw new Error(`Invalid JSON format: ${parseError.message}`);
        }
        
        // Validate structure (basic check)
        if (!bookmarkData || typeof bookmarkData !== 'object') {
            throw new Error('Invalid bookmark data structure');
        }
        
        // Import successful - update the application
        bookmarksData = bookmarkData;
        
        // Save to preferences for future use
        savePreferences({ 
            lastGistImport: new Date().toISOString(),
            lastGistId: gistId,
            lastGistFile: targetFile.filename
        });
        
        // Re-render everything
        renderSections();
        restoreSelectedSections();
        renderBookmarks();
        updateBulkOpenButton();
        
        hideImportModal();
        showToast(`Successfully imported from ${targetFile.filename}!`);
        
        console.log('Imported bookmarks from Gist:', gistId, targetFile.filename);
        
    } catch (error) {
        console.error('Gist import failed:', error);
        showToast(`Import failed: ${error.message}`, 'error');
    } finally {
        // Reset button state
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="fas fa-download"></i> Import Bookmarks';
    }
}

// Add keyboard support for modal
document.addEventListener('keydown', (e) => {
    const modal = document.getElementById('importModal');
    if (modal && modal.style.display === 'flex') {
        if (e.key === 'Escape') {
            hideImportModal();
        } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            importFromGist();
        }
    }
});

// Make functions globally available for debugging
window.showImportModal = showImportModal;
window.hideImportModal = hideImportModal;
window.importFromGist = importFromGist;
window.extractGistId = extractGistId;fas fa-copy"></i>';
                copyBtn.title = 'Copy link';
                copyBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    copyToClipboard(url);
                });
                
                actions.appendChild(copyBtn);
                bookmarkItem.appendChild(link);
                bookmarkItem.appendChild(actions);
                categoryDiv.appendChild(bookmarkItem);
            });
            
            if (categoryDiv.children.length > 1) {
                sectionColumn.appendChild(categoryDiv);
            }
        });
        
        if (sectionColumn.children.length > 1) {
            container.appendChild(sectionColumn);
        }
    });
}

// Open all bookmarks in a specific section
function openSectionBookmarks(buttonElement, sectionName) {
    const sectionLinks = document.querySelectorAll(`[data-section="${sectionName}"]`);
    const urls = Array.from(sectionLinks)
        .map(link => link.dataset.url)
        .filter(url => url && typeof url === 'string');
    
    if (urls.length === 0) {
        showToast('No bookmarks found in this section', 'error');
        return;
    }
    
    if (urls.length > 10) {
        const confirmed = confirm(`This will open ${urls.length} tabs from "${sectionName}". Continue?`);
        if (!confirmed) return;
    }
    
    urls.forEach((url, index) => {
        setTimeout(() => window.open(url, '_blank'), index * 100);
    });
    
    const displayName = sectionName.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    showToast(`Opened ${urls.length} bookmarks from ${displayName}!`);
}

// Open all bookmarks in a specific category
function openCategoryBookmarks(sectionName, categoryName) {
    const categoryLinks = document.querySelectorAll(`[data-section="${sectionName}"][data-category="${categoryName}"]`);
    const urls = Array.from(categoryLinks)
        .map(link => link.dataset.url)
        .filter(url => url && typeof url === 'string');
    
    if (urls.length === 0) {
        showToast('No bookmarks found in this category', 'error');
        return;
    }
    
    if (urls.length > 10) {
        const confirmed = confirm(`This will open ${urls.length} tabs from "${categoryName}". Continue?`);
        if (!confirmed) return;
    }
    
    urls.forEach((url, index) => {
        setTimeout(() => window.open(url, '_blank'), index * 100);
    });
    
    showToast(`Opened ${urls.length} bookmarks from ${categoryName}!`);
}

// Update bulk open button
function updateBulkOpenButton() {
    const bulkOpenBtn = document.getElementById('bulkOpenBtn');
    if (!bulkOpenBtn) return;
    
    const visibleLinks = document.querySelectorAll('.bookmark-link');
    
    if (visibleLinks.length > 1) {
        bulkOpenBtn.style.display = 'flex';
        bulkOpenBtn.innerHTML = `<i class="fas fa-external-link-alt"></i> Open All (${visibleLinks.length})`;
    } else {
        bulkOpenBtn.style.display = 'none';
    }
}

// Open all bookmarks
function openAllBookmarks() {
    const visibleLinks = document.querySelectorAll('.bookmark-link');
    const urls = Array.from(visibleLinks)
        .map(link => link.dataset.url)
        .filter(url => url && typeof url === 'string');
    
    if (urls.length === 0) {
        showToast('No bookmarks to open', 'error');
        return;
    }
    
    if (urls.length > 10) {
        const confirmed = confirm(`This will open ${urls.length} tabs. Continue?`);
        if (!confirmed) return;
    }
    
    urls.forEach((url, index) => {
        setTimeout(() => window.open(url, '_blank'), index * 100);
    });
    
    showToast(`Opened ${urls.length} bookmarks!`);
}

// Copy to clipboard
function copyToClipboard(text) {
    if (!text) return;
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text)
            .then(() => showToast('Link copied!'))
            .catch(() => fallbackCopyTextToClipboard(text));
    } else {
        fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        showToast(successful ? 'Link copied!' : 'Failed to copy link', successful ? 'success' : 'error');
    } catch (err) {
        showToast('Failed to copy link', 'error');
    }
    
    document.body.removeChild(textArea);
}

// Show toast notification
function showToast(message = 'Link copied!', type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = 'toast';
    
    if (type === 'error') {
        toast.style.background = '#dc3545';
        toast.style.color = '#ffffff';
    } else {
        toast.style.background = 'var(--toast-bg)';
        toast.style.color = 'var(--toast-text)';
    }
    
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing bookmark application...');
    
    initializeTheme();
    loadBookmarks();
    
    // Event listeners
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    const bulkOpenBtn = document.getElementById('bulkOpenBtn');
    if (bulkOpenBtn) {
        bulkOpenBtn.addEventListener('click', openAllBookmarks);
    }
    
    // System theme change listener
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
            if (!localStorage.getItem('bookmarks-theme')) {
                const newTheme = e.matches ? 'light' : 'dark';
                setTheme(newTheme);
                updateThemeToggleIcon(newTheme);
            }
        });
    }
    
    console.log('Bookmark application initialized successfully');
});