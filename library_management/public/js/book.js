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


