document.addEventListener("DOMContentLoaded", function() {
  const messageContainer = document.getElementById('login-message');

  async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
      const response = await fetch('/api/method/library_management.api.login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      });

        if (!response.ok) {
          throw new Error('Login failed! Please check your username and password.');
        }

        const data = await response.json();
        if (data.message === 'Login successful') {
          window.location.href = '/landing';
        } else {
          messageContainer.innerHTML = data.message;
        }
    } catch (error) {
      messageContainer.innerHTML = error.message; 
    }
  }

  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }
});

 
