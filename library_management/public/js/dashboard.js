// Dashboard JavaScript
let monthlyTrendsChart;
let categoryChart;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    setupEventListeners();
});

// Load all dashboard data
async function loadDashboardData() {
    try {
        showLoading();
        
        // Load analytics data
        const analyticsResponse = await fetch('/api/method/library_management.library_management.api.get_library_analytics');
        const analyticsData = await analyticsResponse.json();
        
        if (analyticsData.message) {
            updateStatistics(analyticsData.message.overview);
            createMonthlyTrendsChart(analyticsData.message.monthly_trends);
            createCategoryChart(analyticsData.message.books_by_category);
            displayTopBooks(analyticsData.message.top_books);
        }
        
        // Load recent transactions
        loadRecentTransactions();
        
        hideLoading();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError('Failed to load dashboard data');
        hideLoading();
    }
}

// Update statistics cards
function updateStatistics(overview) {
    document.getElementById('total-books').textContent = overview.total_books || 0;
    document.getElementById('total-members').textContent = overview.total_members || 0;
    document.getElementById('total-issued').textContent = overview.total_issued || 0;
    document.getElementById('total-overdue').textContent = overview.total_overdue || 0;
}

// Create monthly trends chart
function createMonthlyTrendsChart(data) {
    const ctx = document.getElementById('monthlyTrendsChart').getContext('2d');
    
    if (monthlyTrendsChart) {
        monthlyTrendsChart.destroy();
    }
    
    monthlyTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(item => item.month),
            datasets: [{
                label: 'Books Issued',
                data: data.map(item => item.issues),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Create category chart
function createCategoryChart(data) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    if (categoryChart) {
        categoryChart.destroy();
    }
    
    const colors = [
        '#667eea', '#764ba2', '#f093fb', '#f5576c',
        '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
        '#ffecd2', '#fcb69f', '#a8edea', '#fed6e3'
    ];
    
    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.category),
            datasets: [{
                data: data.map(item => item.count),
                backgroundColor: colors.slice(0, data.length),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                }
            }
        }
    });
}

// Display top books
function displayTopBooks(books) {
    const container = document.getElementById('top-books');
    container.innerHTML = '';
    
    books.slice(0, 6).forEach(book => {
        const bookCard = document.createElement('div');
        bookCard.className = 'book-card';
        bookCard.innerHTML = `
            <h4>${book.title}</h4>
            <p>by ${book.author}</p>
            <small>${book.borrow_count} times borrowed</small>
        `;
        container.appendChild(bookCard);
    });
}

// Load recent transactions
async function loadRecentTransactions() {
    try {
        // This would typically fetch recent transactions from the API
        const container = document.getElementById('recent-transactions');
        container.innerHTML = `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas fa-book-open"></i>
                </div>
                <div class="activity-content">
                    <h4>Book issued to John Doe</h4>
                    <p>The Great Gatsby - 2 minutes ago</p>
                </div>
            </div>
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas fa-undo"></i>
                </div>
                <div class="activity-content">
                    <h4>Book returned by Jane Smith</h4>
                    <p>To Kill a Mockingbird - 15 minutes ago</p>
                </div>
            </div>
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas fa-user-plus"></i>
                </div>
                <div class="activity-content">
                    <h4>New member registered</h4>
                    <p>Alice Johnson - 1 hour ago</p>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading recent transactions:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Quick issue form
    document.getElementById('quickIssueForm').addEventListener('submit', handleQuickIssue);
    
    // Quick return form
    document.getElementById('quickReturnForm').addEventListener('submit', handleQuickReturn);
    
    // Search functionality for modals
    setupSearchFunctionality();
}

// Handle quick issue
async function handleQuickIssue(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const memberName = document.getElementById('memberSearch').dataset.selectedValue;
    const bookName = document.getElementById('bookSearch').dataset.selectedValue;
    const notes = formData.get('notes');
    
    if (!memberName || !bookName) {
        showError('Please select both member and book');
        return;
    }
    
    try {
        const response = await fetch('/api/method/library_management.library_management.api.issue_book', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                book_name: bookName,
                member_name: memberName,
                notes: notes
            })
        });
        
        const result = await response.json();
        
        if (result.message && result.message.success) {
            showSuccess('Book issued successfully!');
            closeModal('quickIssueModal');
            loadDashboardData(); // Refresh data
        } else {
            showError(result.message.message || 'Failed to issue book');
        }
    } catch (error) {
        console.error('Error issuing book:', error);
        showError('An error occurred while issuing the book');
    }
}

// Handle quick return
async function handleQuickReturn(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const transactionName = document.getElementById('transactionSearch').dataset.selectedValue;
    const condition = formData.get('condition');
    const notes = formData.get('notes');
    
    if (!transactionName) {
        showError('Please select a transaction');
        return;
    }
    
    try {
        const response = await fetch('/api/method/library_management.library_management.api.return_book', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_name: transactionName,
                condition_at_return: condition,
                notes: notes
            })
        });
        
        const result = await response.json();
        
        if (result.message && result.message.success) {
            showSuccess('Book returned successfully!');
            if (result.message.fine_applicable) {
                showWarning(`Fine applicable: $${result.message.fine_amount}`);
            }
            closeModal('quickReturnModal');
            loadDashboardData(); // Refresh data
        } else {
            showError(result.message.message || 'Failed to return book');
        }
    } catch (error) {
        console.error('Error returning book:', error);
        showError('An error occurred while returning the book');
    }
}

// Setup search functionality for modals
function setupSearchFunctionality() {
    // Member search
    const memberSearch = document.getElementById('memberSearch');
    memberSearch.addEventListener('input', debounce(searchMembers, 300));
    
    // Book search
    const bookSearch = document.getElementById('bookSearch');
    bookSearch.addEventListener('input', debounce(searchBooks, 300));
    
    // Transaction search
    const transactionSearch = document.getElementById('transactionSearch');
    transactionSearch.addEventListener('input', debounce(searchTransactions, 300));
}

// Search members
async function searchMembers(event) {
    const query = event.target.value;
    if (query.length < 2) return;
    
    try {
        const response = await fetch(`/api/method/library_management.library_management.api.search_members?search=${encodeURIComponent(query)}&page_size=5`);
        const result = await response.json();
        
        if (result.message && result.message.members) {
            showSuggestions('memberSuggestions', result.message.members, 'member_name', 'name');
        }
    } catch (error) {
        console.error('Error searching members:', error);
    }
}

// Search books
async function searchBooks(event) {
    const query = event.target.value;
    if (query.length < 2) return;
    
    try {
        const response = await fetch(`/api/method/library_management.library_management.api.get_books?search=${encodeURIComponent(query)}&page_size=5`);
        const result = await response.json();
        
        if (result.message && result.message.books) {
            showSuggestions('bookSuggestions', result.message.books, 'title', 'name');
        }
    } catch (error) {
        console.error('Error searching books:', error);
    }
}

// Search transactions (for returns)
async function searchTransactions(event) {
    const query = event.target.value;
    if (query.length < 2) return;
    
    // This would search for active transactions
    // For now, showing placeholder
    const suggestions = [
        { name: 'TXN-001', display: 'John Doe - The Great Gatsby' },
        { name: 'TXN-002', display: 'Jane Smith - To Kill a Mockingbird' }
    ];
    
    showSuggestions('transactionSuggestions', suggestions, 'display', 'name');
}

// Show suggestions dropdown
function showSuggestions(containerId, items, displayField, valueField) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (items.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.textContent = item[displayField];
        div.addEventListener('click', () => {
            const input = container.previousElementSibling;
            input.value = item[displayField];
            input.dataset.selectedValue = item[valueField];
            container.style.display = 'none';
        });
        container.appendChild(div);
    });
    
    container.style.display = 'block';
}

// Modal functions
function showQuickIssue() {
    document.getElementById('quickIssueModal').style.display = 'block';
}

function showQuickReturn() {
    document.getElementById('quickReturnModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    // Reset form
    const form = document.querySelector(`#${modalId} form`);
    if (form) form.reset();
}

// Quick action functions
function showAddBook() {
    window.location.href = '/app/book/new';
}

function showAddMember() {
    window.location.href = '/app/member/new';
}

function showOverdueBooks() {
    window.location.href = '/app/library-transaction?status=Overdue';
}

function showReports() {
    window.location.href = '/reports';
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showLoading() {
    // Show loading indicator
}

function hideLoading() {
    // Hide loading indicator
}

function showSuccess(message) {
    // Show success notification
    alert(message); // Temporary - replace with proper notification system
}

function showError(message) {
    // Show error notification
    alert('Error: ' + message); // Temporary - replace with proper notification system
}

function showWarning(message) {
    // Show warning notification
    alert('Warning: ' + message); // Temporary - replace with proper notification system
}

// Close modals when clicking outside
window.addEventListener('click', function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});
