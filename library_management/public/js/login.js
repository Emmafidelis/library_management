document.getElementById('loginForm').addEventListener('submit', function (event) {
  event.preventDefault();

  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const loginMessage = document.getElementById('loginMessage');

  fetch('/api/method/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      usr: username,
      pwd: password
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.message === 'Logged In') {
      window.location.href = '/book';
    } else {
      loginMessage.textContent = 'Invalid username or password';
      loginMessage.style.color = 'red';
    }
  })
  .catch(error => {
    console.error('Error:', error);
    loginMessage.textContent = 'An error occurred. Please try again.';
    loginMessage.style.color = 'red';
  });
});
