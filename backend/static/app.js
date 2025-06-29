document.addEventListener("DOMContentLoaded", () => {
  // Authentication elements
  const authContainer = document.getElementById("auth-container");
  const chatContainer = document.getElementById("chat-container");
  const googleLoginBtn = document.getElementById("google-login-btn");
  const userHeader = document.getElementById("user-header");
  const userAvatar = document.getElementById("user-avatar");
  const userName = document.getElementById("user-name");
  const logoutBtn = document.getElementById("logout-btn");

  // Chat elements
  const responsePane = document.getElementById("response-pane");
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");
  const imageUpload = document.getElementById("image-upload");
  const imageUploadButton = document.getElementById("image-upload-button");
  const micButton = document.getElementById("mic-button");
  const tooltip = micButton.querySelector(".tooltip");

  // Application state
  let currentUser = null;
  let threadId = null;
  let loadingIndicator = null;
  let selectedFile = null;
  let recognition = null;
  let isRecording = false;
  let retryCount = 0;
  let isRetrying = false;
  const MAX_RETRIES = 3;
  const RETRY_DELAY = 2000; // 2 seconds between retries

  // Authentication functions
  async function checkAuthStatus() {
    try {
      const response = await fetch("/auth/status");
      if (response.ok) {
        const data = await response.json();
        if (data.authenticated) {
          currentUser = data.user;
          showChatInterface();
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
    chatContainer.style.display = "none";
  }

  function showChatInterface() {
    authContainer.style.display = "none";
    chatContainer.style.display = "flex";

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

    // Initialize speech recognition only when authenticated
    if (!recognition) {
      initializeSpeechRecognition();
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
        threadId = null; // Reset thread on logout
        responsePane.innerHTML = ""; // Clear chat history
        showAuthInterface();
      } else {
        showError("Failed to logout");
      }
    } catch (error) {
      console.error("Error during logout:", error);
      showError("Failed to logout");
    }
  }

  // Event listeners
  googleLoginBtn.addEventListener("click", handleGoogleLogin);
  logoutBtn.addEventListener("click", handleLogout);

  // Check authentication status on page load
  checkAuthStatus();

  function showError(message) {
    const errorMessage = document.createElement("div");
    errorMessage.className = "message error-message";
    errorMessage.textContent = message;
    responsePane.appendChild(errorMessage);
    responsePane.scrollTop = responsePane.scrollHeight;
  }

  function isSpeechRecognitionSupported() {
    // Check for basic support
    if (
      !("webkitSpeechRecognition" in window || "SpeechRecognition" in window)
    ) {
      return false;
    }

    // Check for specific browser support
    const userAgent = navigator.userAgent.toLowerCase();
    const isChrome = /chrome/.test(userAgent) && !/edg/.test(userAgent);
    const isArc = /arc/.test(userAgent);
    const isMobile = /mobile|android|iphone|ipad|ipod/.test(userAgent);

    // Chrome and Arc have reliable support
    return (isChrome || isArc) && !isMobile;
  }

  function testSpeechRecognition() {
    return new Promise((resolve) => {
      if (!isSpeechRecognitionSupported()) {
        resolve(false);
        return;
      }

      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const testRecognition = new SpeechRecognition();

      testRecognition.onerror = (event) => {
        if (
          event.error === "network" ||
          event.error === "service-not-allowed"
        ) {
          resolve(false);
        } else {
          resolve(true);
        }
      };

      testRecognition.onstart = () => {
        testRecognition.stop();
        resolve(true);
      };

      try {
        testRecognition.start();
      } catch (error) {
        resolve(false);
      }
    });
  }

  function updateTooltip(message) {
    tooltip.textContent = message;
  }

  function setMicButtonState(enabled, message) {
    if (enabled) {
      micButton.classList.remove("disabled");
      micButton.disabled = false;
    } else {
      micButton.classList.add("disabled");
      micButton.disabled = true;
      updateTooltip(message);
    }
  }

  async function initializeSpeechRecognition() {
    // Start with the button disabled
    setMicButtonState(false, "Testing speech recognition...");

    // Test if speech recognition is actually available
    const isAvailable = await testSpeechRecognition();

    if (!isAvailable) {
      console.warn("Speech recognition not available");
      setMicButtonState(
        false,
        "Speech recognition is not available in this browser"
      );
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      console.log("Speech recognition started");
      micButton.classList.add("recording");
      isRecording = true;
      isRetrying = false;
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      userInput.value = transcript;
      console.log("Speech recognition result:", transcript);
      retryCount = 0; // Reset retry count on successful result
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      micButton.classList.remove("recording");
      isRecording = false;

      let errorMessage = "Speech recognition error. ";

      switch (event.error) {
        case "network":
          if (retryCount < MAX_RETRIES && !isRetrying) {
            isRetrying = true;
            retryCount++;
            errorMessage += `Retrying (${retryCount}/${MAX_RETRIES})...`;

            setTimeout(() => {
              isRetrying = false;
              try {
                recognition.start();
              } catch (error) {
                console.error("Retry failed:", error);
                showError(
                  "Failed to retry speech recognition. Please check your internet connection."
                );
              }
            }, RETRY_DELAY);
          } else if (retryCount >= MAX_RETRIES) {
            errorMessage =
              "Speech recognition service is currently unavailable. Please try again later or use text input.";
            setMicButtonState(
              false,
              "Speech recognition service is unavailable. Please try again later."
            );
            retryCount = 0;
          }
          break;
        case "not-allowed":
        case "permission-denied":
          errorMessage =
            "Microphone access was denied. Please enable it in your browser settings.";
          setMicButtonState(
            false,
            "Microphone access was denied. Please enable it in your browser settings."
          );
          break;
        case "audio-capture":
          errorMessage =
            "No microphone was found. Please ensure a microphone is connected.";
          setMicButtonState(
            false,
            "No microphone was found. Please ensure a microphone is connected."
          );
          break;
        case "service-not-allowed":
          errorMessage =
            "Speech recognition service is not available. Please try again later.";
          setMicButtonState(
            false,
            "Speech recognition service is not available. Please try again later."
          );
          break;
        default:
          errorMessage += "Please try again.";
      }

      showError(errorMessage);
    };

    recognition.onend = () => {
      console.log("Speech recognition ended");
      micButton.classList.remove("recording");
      isRecording = false;
      isRetrying = false;
    };

    // Request microphone permission
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log("Microphone permission granted");
      setMicButtonState(true, "Click to start recording");
    } catch (error) {
      console.error("Microphone permission denied:", error);
      setMicButtonState(
        false,
        "Microphone access was denied. Please enable it in your browser settings."
      );
    }
  }

  micButton.addEventListener("click", () => {
    if (!recognition || micButton.disabled) return;

    if (!isRecording) {
      try {
        retryCount = 0; // Reset retry count when manually starting
        recognition.start();
      } catch (error) {
        console.error("Failed to start speech recognition:", error);
        showError("Failed to start speech recognition. Please try again.");
      }
    } else {
      recognition.stop();
    }
  });

  function appendMessage(message, className) {
    const messageElement = document.createElement("div");
    messageElement.className = `message ${className}`;
    messageElement.innerHTML = marked.parse(message);
    responsePane.appendChild(messageElement);
    responsePane.scrollTop = responsePane.scrollHeight; // Scroll to the bottom
  }

  function appendImage(imageUrl, className) {
    const imageContainer = document.createElement("div");
    imageContainer.className = `message ${className}`;
    const imageElement = document.createElement("img");
    imageElement.src = imageUrl;
    imageElement.alt = "Uploaded Image";
    imageElement.style.maxWidth = "100%";
    imageContainer.appendChild(imageElement);
    responsePane.appendChild(imageContainer);
    responsePane.scrollTop = responsePane.scrollHeight; // Scroll to the bottom
  }

  function showLoadingIndicator() {
    const spinner = document.getElementById("spinner");
    spinner.style.display = "block";
  }

  function hideLoadingIndicator() {
    const spinner = document.getElementById("spinner");
    spinner.style.display = "none";
  }

  function showStatusMessage(message, type = 'status') {
    // Create or update status message element
    let statusElement = document.getElementById('status-message');
    if (!statusElement) {
      statusElement = document.createElement('div');
      statusElement.id = 'status-message';
      statusElement.className = 'status-message';
      responsePane.appendChild(statusElement);
    }

    // Update content based on type
    if (type === 'recipe_search') {
      statusElement.innerHTML = `<span class="search-icon">🔍</span> ${message}`;
      statusElement.className = 'status-message recipe-search';
    } else if (type === 'tool_use') {
      statusElement.innerHTML = `<span class="tool-icon">⚙️</span> ${message}`;
      statusElement.className = 'status-message tool-use';
    } else if (type === 'tool_complete') {
      statusElement.innerHTML = message;
      statusElement.className = 'status-message tool-complete';
      // Auto-remove tool complete messages after 2 seconds
      setTimeout(() => {
        if (statusElement && statusElement.parentNode) {
          statusElement.remove();
        }
      }, 2000);
      return;
    } else {
      statusElement.innerHTML = `<span class="spinner-small"></span> ${message}`;
      statusElement.className = 'status-message';
    }

    responsePane.scrollTop = responsePane.scrollHeight;
  }

  function removeStatusMessage() {
    const statusElement = document.getElementById('status-message');
    if (statusElement) {
      statusElement.remove();
    }
  }

  async function sendMessage() {
    // Check if user is authenticated
    if (!currentUser) {
      showError("Please login to send messages");
      return;
    }

    const message = userInput.value.trim();
    if (message || selectedFile) {
      if (message) {
        appendMessage(message, "user-message");
      }
      if (selectedFile) {
        // Display the image in the chat before sending
        const reader = new FileReader();
        reader.onload = (e) => {
          appendImage(e.target.result, "user-image");
        };
        reader.readAsDataURL(selectedFile);
      }
      userInput.value = "";

      const formData = new FormData();
      const jsonPayload = JSON.stringify({
        message: message,
        thread_id: threadId,
      });
      formData.append("message", jsonPayload);
      if (selectedFile) {
        formData.append("attachment", selectedFile);
      }

      try {
        // Use streaming endpoint for real-time feedback
        const response = await fetch("/chat/stream", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          if (response.status === 401) {
            showError("Session expired. Please login again.");
            currentUser = null;
            showAuthInterface();
          } else {
            showError(`Failed to send message: ${response.statusText}`);
          }
          return;
        }

        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');

          // Process complete lines, keep incomplete line in buffer
          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i].trim();
            if (line.startsWith('data: ')) {
              try {
                const eventData = JSON.parse(line.slice(6));
                handleStreamEvent(eventData);
              } catch (e) {
                console.error('Error parsing stream event:', e);
              }
            }
          }

          buffer = lines[lines.length - 1];
        }

      } catch (error) {
        console.error("Streaming failed, falling back to regular endpoint:", error);
        removeStatusMessage();

        // Fallback to non-streaming endpoint
        try {
          showLoadingIndicator();
          const fallbackResponse = await fetch("/chat", {
            method: "POST",
            body: formData,
          });

          if (fallbackResponse.ok) {
            const data = await fallbackResponse.json();
            threadId = data.thread_id;
            appendMessage(data.response, "bot-message");
          } else {
            showError("Failed to send message. Please try again.");
          }
        } catch (fallbackError) {
          console.error("Fallback also failed:", fallbackError);
          showError("Failed to send message. Please try again.");
        } finally {
          hideLoadingIndicator();
        }
      } finally {
        selectedFile = null;
        imageUpload.value = "";
      }
    }
  }

  function handleStreamEvent(event) {
    switch (event.type) {
      case 'status':
        showStatusMessage(event.message, 'status');
        break;

      case 'recipe_search':
        showStatusMessage(event.message, 'recipe_search');
        break;

      case 'tool_use':
        showStatusMessage(event.message, 'tool_use');
        break;

      case 'tool_complete':
        showStatusMessage(event.message, 'tool_complete');
        break;

      case 'response':
        removeStatusMessage();
        threadId = event.thread_id;
        appendMessage(event.content, "bot-message");
        break;

      case 'end':
        removeStatusMessage();
        break;

      case 'error':
        removeStatusMessage();
        showError(`Error: ${event.message}`);
        break;

      default:
        console.log('Unknown event type:', event.type, event);
    }
  }

  // Trigger the hidden file input when the button is clicked
  imageUploadButton.addEventListener("click", () => {
    imageUpload.click();
  });

  imageUpload.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (file) {
      selectedFile = file;
      const reader = new FileReader();
      reader.onload = (e) => {
        appendImage(e.target.result, "user-image");
      };
      reader.readAsDataURL(file);
    }
  });

  sendButton.addEventListener("click", sendMessage);

  // Optionally, allow sending the message by pressing Enter
  userInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
});
