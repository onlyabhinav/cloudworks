document.addEventListener("DOMContentLoaded", () => {
  // --- Theme Switching Functionality ---
  const themeToggleBtn = document.getElementById("theme-toggle");
  const body = document.body;

  // Function to set the theme and update the icon
  const applyTheme = (theme) => {
    if (theme === "light") {
      body.classList.add("light-theme");
      themeToggleBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
    } else {
      body.classList.remove("light-theme");
      themeToggleBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
    }
  };

  // Check for saved theme in localStorage on page load
  const savedTheme = localStorage.getItem("theme") || "dark"; // Default to dark
  applyTheme(savedTheme);

  // Event listener for the theme toggle button
  themeToggleBtn.addEventListener("click", () => {
    let newTheme = body.classList.contains("light-theme") ? "dark" : "light";
    applyTheme(newTheme);
    localStorage.setItem("theme", newTheme);
  });

  // --- Copy Link Functionality ---
  const copyFeedback = document.getElementById("copy-feedback");
  const allCopyButtons = document.querySelectorAll(".copy-btn");

  allCopyButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      const urlToCopy = event.currentTarget.dataset.url;

      navigator.clipboard
        .writeText(urlToCopy)
        .then(() => {
          copyFeedback.classList.add("show");
          setTimeout(() => {
            copyFeedback.classList.remove("show");
          }, 2000);
        })
        .catch((err) => {
          console.error("Failed to copy text: ", err);
          alert("Failed to copy link.");
        });
    });
  });

  // --- Section Filtering Functionality ---
  const allToggleCheckboxes = document.querySelectorAll(".section-toggle");
  const allBookmarkSections = document.querySelectorAll(".bookmark-section");

  const updateVisibility = () => {
    const checkedSections = new Set();
    allToggleCheckboxes.forEach((checkbox) => {
      if (checkbox.checked) {
        checkedSections.add(checkbox.value);
      }
    });

    allBookmarkSections.forEach((section) => {
      const sectionName = section.dataset.sectionName;
      if (checkedSections.has(sectionName)) {
        section.classList.remove("hidden");
      } else {
        section.classList.add("hidden");
      }
    });
  };

  allToggleCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", updateVisibility);
  });

  updateVisibility();
});
