document.addEventListener("DOMContentLoaded", () => {
  // Authentication elements
  const authContainer = document.getElementById("auth-container");
  const settingsContainer = document.getElementById("settings-container");
  const googleLoginBtn = document.getElementById("google-login-btn");
  const userHeader = document.getElementById("user-header");
  const userAvatar = document.getElementById("user-avatar");
  const userName = document.getElementById("user-name");
  const logoutBtn = document.getElementById("logout-btn");

  // Upload elements
  const recipeFileInput = document.getElementById("recipe-file-input");
  const uploadDropzone = document.getElementById("upload-dropzone");
  const uploadBtn = document.getElementById("upload-btn");
  const uploadStatus = document.getElementById("upload-status");

  // Application state
  let currentUser = null;
  let selectedFile = null;

  // Authentication functions
  async function checkAuthStatus() {
    try {
      const response = await fetch("/auth/status");
      if (response.ok) {
        const data = await response.json();
        if (data.authenticated) {
          currentUser = data.user;
          showSettingsInterface();
          return true;
        }
      }
      showAuthInterface();
      return false;
    } catch (error) {
      console.error("Error checking auth status:", error);
      showAuthInterface();
      return false;
    }
  }

  function showAuthInterface() {
    authContainer.style.display = "flex";
    settingsContainer.style.display = "none";
  }

  function showSettingsInterface() {
    authContainer.style.display = "none";
    settingsContainer.style.display = "flex";

    if (currentUser) {
      userName.textContent = currentUser.name;
      userAvatar.src = currentUser.avatar_url || "/static/default-avatar.svg";
      userAvatar.alt = currentUser.name;

      // Add error handling for broken avatar images
      userAvatar.onerror = function() {
        this.src = "/static/default-avatar.svg";
        this.onerror = null; // Prevent infinite loop
      };
    }
  }

  async function handleGoogleLogin() {
    try {
      const response = await fetch("/auth/google/login");
      if (response.ok) {
        const data = await response.json();
        // Redirect to Google OAuth
        window.location.href = data.auth_url;
      } else {
        showError("Failed to initiate Google login");
      }
    } catch (error) {
      console.error("Error initiating Google login:", error);
      showError("Failed to initiate Google login");
    }
  }

  async function handleLogout() {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (response.ok) {
        currentUser = null;
        showAuthInterface();
      } else {
        showError("Failed to logout");
      }
    } catch (error) {
      console.error("Error during logout:", error);
      showError("Failed to logout");
    }
  }

  // File upload functions
  function showError(message) {
    uploadStatus.style.display = "block";
    uploadStatus.className = "upload-status error";
    uploadStatus.innerHTML = `❌ ${message}`;
  }

  function showSuccess(message) {
    uploadStatus.style.display = "block";
    uploadStatus.className = "upload-status success";
    uploadStatus.innerHTML = `✅ ${message}`;
  }

  function showLoading(message) {
    uploadStatus.style.display = "block";
    uploadStatus.className = "upload-status loading";
    uploadStatus.innerHTML = `⏳ ${message}`;
  }

  function handleFileSelection(file) {
    if (!file) {
      selectedFile = null;
      uploadBtn.disabled = true;
      uploadDropzone.classList.remove("has-file");
      return;
    }

    if (!file.name.endsWith('.yaml') && !file.name.endsWith('.yml')) {
      showError("Please select a YAML file (.yaml or .yml)");
      return;
    }

    selectedFile = file;
    uploadBtn.disabled = false;
    uploadDropzone.classList.add("has-file");
    uploadDropzone.innerHTML = `
      <div class="upload-icon">📄</div>
      <p><strong>${file.name}</strong></p>
      <small>Ready to upload</small>
    `;
  }

  async function uploadRecipes() {
    if (!selectedFile) {
      showError("Please select a file first");
      return;
    }

    if (!currentUser) {
      showError("Please login to upload recipes");
      return;
    }

    try {
      showLoading("Uploading and processing recipes...");
      uploadBtn.disabled = true;

      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch("/recipes/bulk-upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 401) {
          showError("Session expired. Please login again.");
          currentUser = null;
          showAuthInterface();
          return;
        }

        const errorData = await response.json();
        showError(errorData.detail || "Upload failed");
        return;
      }

      const result = await response.json();

      if (result.success) {
        let message = result.message;
        if (result.errors.length > 0) {
          message += "<br><br><strong>Errors:</strong><ul>";
          result.errors.forEach(error => {
            message += `<li>${error}</li>`;
          });
          message += "</ul>";
        }
        showSuccess(message);

        // Reset the form
        selectedFile = null;
        recipeFileInput.value = "";
        uploadDropzone.classList.remove("has-file");
        uploadDropzone.innerHTML = `
          <div class="upload-icon">📄</div>
          <p><strong>Click to select</strong> or drag and drop a YAML file</p>
          <small>Supports .yaml and .yml files</small>
        `;
      } else {
        let errorMessage = result.message;
        if (result.errors.length > 0) {
          errorMessage += "<br><br><strong>Errors:</strong><ul>";
          result.errors.forEach(error => {
            errorMessage += `<li>${error}</li>`;
          });
          errorMessage += "</ul>";
        }
        showError(errorMessage);
      }

    } catch (error) {
      console.error("Upload error:", error);
      showError("Network error during upload. Please try again.");
    } finally {
      uploadBtn.disabled = selectedFile === null;
    }
  }

  // Event listeners
  googleLoginBtn.addEventListener("click", handleGoogleLogin);
  logoutBtn.addEventListener("click", handleLogout);

  // File input handlers
  recipeFileInput.addEventListener("change", (event) => {
    const file = event.target.files[0];
    handleFileSelection(file);
  });

  uploadDropzone.addEventListener("click", () => {
    recipeFileInput.click();
  });

  uploadBtn.addEventListener("click", uploadRecipes);

  // Drag and drop handlers
  uploadDropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    uploadDropzone.classList.add("drag-over");
  });

  uploadDropzone.addEventListener("dragleave", () => {
    uploadDropzone.classList.remove("drag-over");
  });

  uploadDropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    uploadDropzone.classList.remove("drag-over");

    const files = event.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  });

  // Check authentication status on page load
  checkAuthStatus();
});
