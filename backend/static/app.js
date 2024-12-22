document.addEventListener("DOMContentLoaded", () => {
  const responsePane = document.getElementById("response-pane");
  const userInput = document.getElementById("user-input");
  const sendButton = document.getElementById("send-button");
  const imageUpload = document.getElementById("image-upload");
  const imageUploadButton = document.getElementById("image-upload-button");

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
