let currentPage = 1;
const pageSize = 10;

function searchBooks() {
  const searchQuery = document.getElementById("search-input").value;
  const category = document.getElementById("category-filter").value;

  fetch(`/api/method/library_management.api.get_books?search=${encodeURIComponent(searchQuery)}&category=${encodeURIComponent(category)}&page=${currentPage}&page_size=${pageSize}`)
    .then(response => response.json())
    .then(data => {
      if (data && data.message) {
        displayBooks(data.message.books);
        updatePagination(data.message.current_page, data.message.total_pages);
      } else {
        console.error("Failed to fetch books data");
      }
    })
    .catch(error => {
      console.error("Error fetching data:", error);
    });
}

function displayBooks(books) {
    const booksContainer = document.getElementById("books-container");
    booksContainer.innerHTML = "";

    books.forEach(book => {
      const bookCard = document.createElement("div");
      bookCard.classList.add("book-card");
      bookCard.innerHTML = `<h3>${book.title}</h3><p>Author: ${book.author}</p><p>Category: ${book.category}</p>`;
      booksContainer.appendChild(bookCard);
    });
}

function prevPage() {
  if (currentPage > 1) {
    currentPage--;
    searchBooks();
  }
}

function nextPage() {
  const pageInfo = document.getElementById("page-info");
  const totalPages = parseInt(pageInfo.getAttribute("data-total-pages"));
  if (currentPage < totalPages) {
    currentPage++;
    searchBooks();
  }
}

function updatePagination(current, total) {
  document.getElementById("page-info").textContent = `Page ${current} of ${total}`;
  document.getElementById("page-info").setAttribute("data-total-pages", total);
}

document.addEventListener("DOMContentLoaded", () => {
  searchBooks();
});
