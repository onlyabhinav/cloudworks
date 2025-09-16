// Global variables
let bookmarksData = {};
let selectedSections = ["all"];

// Icon mappings
const categoryIcons = {
  development: "fas fa-code",
  tools: "fas fa-wrench",
  learning: "fas fa-graduation-cap",
  design: "fas fa-paint-brush",
  api: "fas fa-plug",
  database: "fas fa-database",
  cloud: "fas fa-cloud",
  security: "fas fa-shield-alt",
  infrastructure: "fas fa-server",
  monitoring: "fas fa-chart-line",
  support: "fas fa-headset",
  documentation: "fas fa-book",
  default: "fas fa-bookmark",
};

const sectionIcons = {
  common: "fas fa-star",
  application: "fas fa-desktop",
  app: "fas fa-mobile-alt",
  links: "fas fa-link",
  default: "fas fa-layer-group",
};

// Theme management
function initializeTheme() {
  let savedTheme = localStorage.getItem("bookmarks-theme");

  if (!savedTheme) {
    savedTheme =
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark";
  }

  setTheme(savedTheme);
  updateThemeToggleIcon(savedTheme);
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("bookmarks-theme", theme);
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute("data-theme");
  const newTheme = currentTheme === "light" ? "dark" : "light";
  setTheme(newTheme);
  updateThemeToggleIcon(newTheme);
  showToast(`Switched to ${newTheme} theme`);
}

function updateThemeToggleIcon(theme) {
  const themeToggle = document.getElementById("themeToggle");
  if (!themeToggle) return;

  const icon = themeToggle.querySelector("i");
  if (icon) {
    icon.className = theme === "light" ? "fas fa-sun" : "fas fa-moon";
    themeToggle.title =
      theme === "light" ? "Switch to dark theme" : "Switch to light theme";
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
    const response = await fetch("/api/bookmarks");
    if (!response.ok) throw new Error("Failed to load bookmarks");

    bookmarksData = await response.json();
    console.log("Loaded bookmarks:", bookmarksData);

    renderSections();
    renderBookmarks();
    updateBulkOpenButton();
  } catch (error) {
    console.error("Error loading bookmarks:", error);
    showToast("Error loading bookmarks", "error");
  }
}

// Render section filter buttons
function renderSections() {
  const sectionContainer = document.getElementById("sectionContainer");
  if (!sectionContainer) return;

  // Remove existing buttons except "All Sections"
  const existingBtns = sectionContainer.querySelectorAll(
    '[data-section]:not([data-section="all"])'
  );
  existingBtns.forEach((btn) => btn.remove());

  // Add section buttons
  Object.keys(bookmarksData).forEach((section) => {
    const btn = document.createElement("button");
    btn.className = "section-btn";
    btn.dataset.section = section;

    const displayName = section
      .replace(/[-_]/g, " ")
      .replace(/\b\w/g, (l) => l.toUpperCase());
    btn.innerHTML = `<i class="${getIconForSection(
      section
    )}"></i> ${displayName}`;
    btn.addEventListener("click", () => toggleSection(section));
    sectionContainer.appendChild(btn);
  });
}

// Toggle section selection
function toggleSection(section) {
  const btn = document.querySelector(`[data-section="${section}"]`);
  const allBtn = document.querySelector('[data-section="all"]');

  if (!btn || !allBtn) return;

  if (section === "all") {
    selectedSections = ["all"];
    document
      .querySelectorAll(".section-btn")
      .forEach((b) => b.classList.remove("active"));
    allBtn.classList.add("active");
  } else {
    if (selectedSections.includes("all")) {
      selectedSections = [];
      allBtn.classList.remove("active");
    }

    if (selectedSections.includes(section)) {
      selectedSections = selectedSections.filter((s) => s !== section);
      btn.classList.remove("active");
    } else {
      selectedSections.push(section);
      btn.classList.add("active");
    }

    if (selectedSections.length === 0) {
      selectedSections = ["all"];
      allBtn.classList.add("active");
    }
  }

  renderBookmarks();
  updateBulkOpenButton();
}

// Render bookmarks in section columns
function renderBookmarks() {
  const container = document.getElementById("mainContainer");
  if (!container) return;

  container.innerHTML = "";

  Object.entries(bookmarksData).forEach(([sectionName, sectionData]) => {
    if (
      !selectedSections.includes("all") &&
      !selectedSections.includes(sectionName)
    ) {
      return;
    }

    if (!sectionData || typeof sectionData !== "object") return;

    // Create section column
    const sectionColumn = document.createElement("div");
    sectionColumn.className = "section-column";

    // Section header with bulk open button
    const sectionHeader = document.createElement("div");
    sectionHeader.className = "section-header";
    const displayName = sectionName
      .replace(/[-_]/g, " ")
      .replace(/\b\w/g, (l) => l.toUpperCase());

    // Count total bookmarks in this section
    const sectionBookmarkCount = Object.values(sectionData).reduce(
      (total, links) => {
        return (
          total +
          (links && typeof links === "object" ? Object.keys(links).length : 0)
        );
      },
      0
    );

    sectionHeader.innerHTML = `
            <h2><i class="${getIconForSection(
              sectionName
            )}"></i> ${displayName}</h2>
            <button class="section-bulk-btn" onclick="openSectionBookmarks(this, '${sectionName}')" title="Open all bookmarks in this section">
                <i class="fas fa-external-link-alt"></i> Open Section (${sectionBookmarkCount})
            </button>
        `;
    sectionColumn.appendChild(sectionHeader);

    // Add categories
    Object.entries(sectionData).forEach(([categoryName, links]) => {
      if (!links || typeof links !== "object") return;

      const categoryDiv = document.createElement("div");
      categoryDiv.className = "category";

      // Category header with title and bulk open button
      const categoryHeader = document.createElement("div");
      categoryHeader.className = "category-header";

      const categoryTitle = document.createElement("div");
      categoryTitle.className = "category-title";
      categoryTitle.innerHTML = `<i class="${getIconForCategory(
        categoryName
      )}"></i> ${categoryName}`;

      const categoryBulkBtn = document.createElement("button");
      categoryBulkBtn.className = "category-bulk-btn";
      categoryBulkBtn.innerHTML = `<i class="fas fa-external-link-alt"></i> Open (${
        Object.keys(links).length
      })`;
      categoryBulkBtn.title = "Open all bookmarks in this category";
      categoryBulkBtn.addEventListener("click", () =>
        openCategoryBookmarks(sectionName, categoryName)
      );

      categoryHeader.appendChild(categoryTitle);
      categoryHeader.appendChild(categoryBulkBtn);
      categoryDiv.appendChild(categoryHeader);

      // Add bookmarks
      Object.entries(links).forEach(([linkName, url]) => {
        if (typeof url !== "string") return;

        const bookmarkItem = document.createElement("div");
        bookmarkItem.className = "bookmark-item";

        const link = document.createElement("a");
        link.className = "bookmark-link";
        link.href = url;
        link.target = "_blank";
        link.innerHTML = `<i class="fas fa-external-link-alt"></i> ${linkName}`;
        link.dataset.url = url;
        link.dataset.section = sectionName;
        link.dataset.category = categoryName;

        const actions = document.createElement("div");
        actions.className = "bookmark-actions";

        const copyBtn = document.createElement("button");
        copyBtn.className = "action-btn";
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = "Copy link";
        copyBtn.addEventListener("click", (e) => {
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
  const sectionLinks = document.querySelectorAll(
    `[data-section="${sectionName}"]`
  );
  const urls = Array.from(sectionLinks)
    .map((link) => link.dataset.url)
    .filter((url) => url && typeof url === "string");

  if (urls.length === 0) {
    showToast("No bookmarks found in this section", "error");
    return;
  }

  if (urls.length > 10) {
    const confirmed = confirm(
      `This will open ${urls.length} tabs from "${sectionName}". Continue?`
    );
    if (!confirmed) return;
  }

  urls.forEach((url, index) => {
    setTimeout(() => window.open(url, "_blank"), index * 100);
  });

  const displayName = sectionName
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
  showToast(`Opened ${urls.length} bookmarks from ${displayName}!`);
}

// Open all bookmarks in a specific category
function openCategoryBookmarks(sectionName, categoryName) {
  const categoryLinks = document.querySelectorAll(
    `[data-section="${sectionName}"][data-category="${categoryName}"]`
  );
  const urls = Array.from(categoryLinks)
    .map((link) => link.dataset.url)
    .filter((url) => url && typeof url === "string");

  if (urls.length === 0) {
    showToast("No bookmarks found in this category", "error");
    return;
  }

  if (urls.length > 10) {
    const confirmed = confirm(
      `This will open ${urls.length} tabs from "${categoryName}". Continue?`
    );
    if (!confirmed) return;
  }

  urls.forEach((url, index) => {
    setTimeout(() => window.open(url, "_blank"), index * 100);
  });

  showToast(`Opened ${urls.length} bookmarks from ${categoryName}!`);
}

// Update bulk open button
function updateBulkOpenButton() {
  const bulkOpenBtn = document.getElementById("bulkOpenBtn");
  if (!bulkOpenBtn) return;

  const visibleLinks = document.querySelectorAll(".bookmark-link");

  if (visibleLinks.length > 1) {
    bulkOpenBtn.style.display = "flex";
    bulkOpenBtn.innerHTML = `<i class="fas fa-external-link-alt"></i> Open All (${visibleLinks.length})`;
  } else {
    bulkOpenBtn.style.display = "none";
  }
}

// Open all bookmarks
function openAllBookmarks() {
  const visibleLinks = document.querySelectorAll(".bookmark-link");
  const urls = Array.from(visibleLinks)
    .map((link) => link.dataset.url)
    .filter((url) => url && typeof url === "string");

  if (urls.length === 0) {
    showToast("No bookmarks to open", "error");
    return;
  }

  if (urls.length > 10) {
    const confirmed = confirm(`This will open ${urls.length} tabs. Continue?`);
    if (!confirmed) return;
  }

  urls.forEach((url, index) => {
    setTimeout(() => window.open(url, "_blank"), index * 100);
  });

  showToast(`Opened ${urls.length} bookmarks!`);
}

// Copy to clipboard
function copyToClipboard(text) {
  if (!text) return;

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard
      .writeText(text)
      .then(() => showToast("Link copied!"))
      .catch(() => fallbackCopyTextToClipboard(text));
  } else {
    fallbackCopyTextToClipboard(text);
  }
}

function fallbackCopyTextToClipboard(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";

  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const successful = document.execCommand("copy");
    showToast(
      successful ? "Link copied!" : "Failed to copy link",
      successful ? "success" : "error"
    );
  } catch (err) {
    showToast("Failed to copy link", "error");
  }

  document.body.removeChild(textArea);
}

// Show toast notification
function showToast(message = "Link copied!", type = "success") {
  const toast = document.getElementById("toast");
  if (!toast) return;

  toast.textContent = message;
  toast.className = "toast";

  if (type === "error") {
    toast.style.background = "#dc3545";
    toast.style.color = "#ffffff";
  } else {
    toast.style.background = "var(--toast-bg)";
    toast.style.color = "var(--toast-text)";
  }

  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3000);
}

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
  console.log("Initializing bookmark application...");

  initializeTheme();
  loadBookmarks();

  // Event listeners
  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", toggleTheme);
  }

  const bulkOpenBtn = document.getElementById("bulkOpenBtn");
  if (bulkOpenBtn) {
    bulkOpenBtn.addEventListener("click", openAllBookmarks);
  }

  // System theme change listener
  if (window.matchMedia) {
    window
      .matchMedia("(prefers-color-scheme: light)")
      .addEventListener("change", (e) => {
        if (!localStorage.getItem("bookmarks-theme")) {
          const newTheme = e.matches ? "light" : "dark";
          setTheme(newTheme);
          updateThemeToggleIcon(newTheme);
        }
      });
  }

  console.log("Bookmark application initialized successfully");
});
