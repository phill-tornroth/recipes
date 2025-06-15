document.addEventListener("DOMContentLoaded", () => {
  const responsePane = document.getElementById("response-pane");
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");
  const imageUpload = document.getElementById("image-upload");
  const imageUploadButton = document.getElementById("image-upload-button");
  const micButton = document.getElementById("mic-button");
  const tooltip = micButton.querySelector(".tooltip");

  let threadId = null;
  let loadingIndicator = null;
  let selectedFile = null;
  let recognition = null;
  let isRecording = false;
  let retryCount = 0;
  let isRetrying = false;
  const MAX_RETRIES = 3;
  const RETRY_DELAY = 2000; // 2 seconds between retries

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

  // Initialize speech recognition
  initializeSpeechRecognition();

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

  async function sendMessage() {
    const message = userInput.value.trim();
    if (message || selectedFile) {
      if (message) {
        appendMessage(message, "user-message");
      }
      if (selectedFile) {
        // Optionally, you can display the image in the chat before sending
        const reader = new FileReader();
        reader.onload = (e) => {
          appendImage(e.target.result, "user-image");
        };
        reader.readAsDataURL(selectedFile);
      }
      userInput.value = "";
      showLoadingIndicator();

      const formData = new FormData();
      const jsonPayload = JSON.stringify({
        message: message,
        thread_id: threadId,
      });
      formData.append("message", jsonPayload);
      if (selectedFile) {
        formData.append("attachment", selectedFile); // Fixed typo here
      }

      try {
        // Send message to the backend
        const response = await fetch("/chat", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          console.error("Failed to send message", response.statusText);
          hideLoadingIndicator();
          return;
        }

        const data = await response.json();
        threadId = data.thread_id; // Store the thread_id for future messages
        appendMessage(data.response, "bot-message");
      } catch (error) {
        console.error("Error sending message:", error);
      } finally {
        hideLoadingIndicator();
        selectedFile = null; // Reset the selected file after sending
        imageUpload.value = ""; // Reset the file input
      }
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
