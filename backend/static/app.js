document.addEventListener("DOMContentLoaded", () => {
  const responsePane = document.getElementById("response-pane");
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");

  let threadId = null;
  let loadingIndicator = null;

  function appendMessage(message, className) {
    const messageElement = document.createElement("div");
    messageElement.className = `message ${className}`;
    messageElement.innerHTML = marked.parse(message);
    // messageElement.textContent = message;
    responsePane.appendChild(messageElement);
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
    if (message) {
      appendMessage(message, "user-message");
      userInput.value = "";
      showLoadingIndicator();

      // Send message to the backend
      const response = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: message,
          thread_id: threadId,
        }),
      });
      const data = await response.json();
      threadId = data.thread_id; // Store the thread_id for future messages
      appendMessage(data.response, "bot-message");
      hideLoadingIndicator();
    }
  }

  sendButton.addEventListener("click", sendMessage);

  userInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
      sendMessage();
    }
  });
});
