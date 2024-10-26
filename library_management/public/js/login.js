function handleLogin(event) {
  event.preventDefault();

  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  const messageContainer = document.getElementById("message-container");

  messageContainer.innerHTML = "";

  fetch(`/api/method/library_management.library_management.api.login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  })
  }   
