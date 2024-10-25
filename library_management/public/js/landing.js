
let currentPage = 1;
const totalPages = 10; // Replace with the actual total number of pages from the backend

function searchBooks() {
    const searchQuery = document.getElementById("search-input").value;
    const category = document.getElementById("category-filter").value;

    alert(`Searching for "${searchQuery}" in category "${category}"`);
}

function displayBooks(books) {
    const booksContainer = document.getElementById("books-container");
    booksContainer.innerHTML = "";
    
    books.forEach(book => {
        const bookCard = document.createElement("div");
        bookCard.classList.add("book-card");
        bookCard.innerHTML = `<h3>${book.title}</h3><p>Author: ${book.author}</p>`;
        booksContainer.appendChild(bookCard);
    });
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        updatePagination();
        searchBooks(); // Re-fetch books on the new page
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        updatePagination();
        searchBooks(); // Re-fetch books on the new page
    }
}

function updatePagination() {
    document.getElementById("page-info").textContent = `Page ${currentPage} of ${totalPages}`;
}

updatePagination();
