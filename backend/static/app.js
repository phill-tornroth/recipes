document.addEventListener("DOMContentLoaded", () => {
  const responsePane = document.getElementById("response-pane");
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");
  const imageUpload = document.getElementById("image-upload");

  let threadId = null;
  let loadingIndicator = null;
  let selectedFile = null;

  function appendMessage(message, className) {
    const messageElement = document.createElement("div");
    messageElement.className = `message ${className}`;
    messageElement.innerHTML = marked.parse(message);
    responsePane.appendChild(messageElement);
    responsePane.scrollTop = responsePane.scrollHeight; // Scroll to the bottom
  }

  function appendImage(imageUrl, className) {
    const imageElement = document.createElement("img");
    imageElement.className = `message ${className}`;
    imageElement.src = imageUrl;
    responsePane.appendChild(imageElement);
    responsePane.scrollTop = responsePane.scrollHeight; // Scroll to the bottom
  }

  function showLoadingIndicator() {
    if (!loadingIndicator) {
      loadingIndicator = document.createElement("div");
      loadingIndicator.id = "loading-indicator";
      loadingIndicator.innerHTML = '<div class="spinner"></div>';
      responsePane.appendChild(loadingIndicator);
      responsePane.scrollTop = responsePane.scrollHeight; // Scroll to the bottom
    }
  }

  function hideLoadingIndicator() {
    if (loadingIndicator) {
      responsePane.removeChild(loadingIndicator);
      loadingIndicator = null;
    }
  }

  async function sendMessage() {
    const message = userInput.value.trim();
    if (message || selectedFile) {
      appendMessage(message, "user-message");
      userInput.value = "";
      showLoadingIndicator();

      const formData = new FormData();
      const jsonPayload = JSON.stringify({
        message: message,
        thread_id: threadId,
      });
      formData.append("message", jsonPayload);
      if (selectedFile) {
        formData.append("attachment", selectedFile);
      }

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
      hideLoadingIndicator();
      selectedFile = null; // Reset the selected file after sending
    }
  }

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
});
