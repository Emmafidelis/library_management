const searchInput = document.getElementById("searchInput");
const categorySelect = document.getElementById("categorySelect");
const booksList = document.getElementById("booksList");
const messageContainer = document.getElementById("messageContainer");

function fetchBooks() {
  const searchQuery = searchInput.value;
  const category = categorySelect.value;
  const page = 1;

  messageContainer.innerHTML = 'Loading books...';

  fetch(`/api/method/library_management.api.get_books?search=${searchQuery}&category=${category}&page=${page}&page_size=10`)
    .then(response => response.json())
    .then(data => {
      if (data.books && data.books.length > 0) {
        displayBooks(data.books);
        messageContainer.innerHTML = '';
      } else {
        messageContainer.innerHTML = data.message || 'No books found.';
      }
    })
    .catch(error => {
      console.error('Error fetching books:', error);
      messageContainer.innerHTML = 'Error loading books.';
    });
}

function displayBooks(books) {
  booksList.innerHTML = '';

  books.forEach(book => {
    const bookItem = document.createElement("div");
    bookItem.classList.add("book-item");

    bookItem.innerHTML = `
      <h3>${book.title}</h3>
      <p>Author: ${book.author}</p>
      <p>Category: ${book.category}</p>
      <button onclick="borrowBook('${book.name}')">Borrow</button>
    `;

    booksList.appendChild(bookItem);
  });
}

function borrowBook(bookId) {
  const memberId = 'YOUR_MEMBER_ID';

  fetch(`/api/method/library_management.api.borrow_book`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: bookId, member_id: memberId })
  })
  .then(response => response.json())
  .then(data => {
    if (data.coupon_code) {
      messageContainer.innerHTML = `Coupon Code: ${data.coupon_code}`;
      messageContainer.style.color = 'green';
    } else {
      messageContainer.innerHTML = data.message || 'Failed to borrow the book.';
      messageContainer.style.color = 'red';
    }
  })
  .catch(error => {
    console.error('Error borrowing book:', error);
    messageContainer.innerHTML = 'An error occurred. Please try again.';
  });
}
