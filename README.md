# Modern Library Management System

A comprehensive, modern library management system built on Frappe/ERPNext framework with advanced features for managing books, members, transactions, and analytics.

## 🚀 Features

### Core Functionality
- **Advanced Book Management**: Complete book catalog with ISBN, barcode, multiple copies, and digital resources
- **Member Management**: Comprehensive member profiles with different membership types and privileges
- **Smart Transaction System**: Issue, return, renewal with automated fine calculation
- **Reservation System**: Book reservation queue with priority management
- **Fine Management**: Automated fine calculation with payment tracking

### Modern UI/UX
- **Responsive Dashboard**: Modern analytics dashboard with charts and statistics
- **Mobile-Friendly**: Fully responsive design for all devices
- **Quick Actions**: Fast book issue/return with search functionality
- **Real-time Updates**: Live statistics and notifications

### Advanced Features
- **Analytics & Reporting**: Comprehensive reports and data visualization
- **Automated Notifications**: Email reminders for due dates and overdue books
- **Barcode Support**: Barcode generation and scanning capabilities
- **Multi-language Support**: Support for multiple languages
- **ERPNext Integration**: Seamless integration with ERPNext for accounting and HR

### Automation
- **Scheduled Tasks**: Automated overdue processing, reminders, and statistics updates
- **Smart Reservations**: Automatic notification when reserved books become available
- **Fine Calculation**: Automated fine calculation based on membership type and library settings

## 📋 Requirements

- Frappe Framework v15+
- ERPNext v15+ (optional, for advanced integrations)
- Python 3.10+
- Node.js 18+

## 🛠️ Installation

### Quick Installation

```bash
# Get the app
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Emmafidelis/library_management --branch develop

# Install the app
bench install-app library_management

# Migrate and build
bench migrate
bench build
```

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Emmafidelis/library_management.git
cd library_management

# Install pre-commit hooks
pre-commit install

# Start development
bench start
```

## ⚙️ Configuration

### Initial Setup

1. **Access Library Settings**: Go to `Library Management > Settings > Library Settings`
2. **Configure Basic Information**: Set library name, contact details, and operating hours
3. **Set Loan Policies**: Configure loan periods, fine rates, and renewal limits
4. **Enable Integrations**: Configure ERPNext integration if needed

### Library Settings Configuration

```python
# Example configuration
{
    "library_name": "Central Library",
    "default_loan_period": 14,  # days
    "fine_per_day": 1.0,  # currency
    "max_renewals": 2,
    "enable_email_notifications": True,
    "enable_erpnext_integration": True
}
```

## 🔗 ERPNext Integration

### Accounting Integration
- **Fine Payments**: Automatic creation of payment entries for fines
- **Membership Fees**: Integration with ERPNext's subscription management
- **Asset Management**: Books as assets in ERPNext

### HR Integration
- **Employee Library Access**: Automatic member creation for employees
- **Department-wise Reports**: Library usage by department
- **Leave Integration**: Book return reminders based on leave schedules

### Setup ERPNext Integration

1. Enable integration in Library Settings
2. Configure default accounts:
   - Income Account for fines
   - Customer Group for library members
   - Cost Center for library operations

```python
# ERPNext Integration Settings
{
    "enable_erpnext_integration": True,
    "default_customer_group": "Library Members",
    "default_income_account": "Library Fines - Company",
    "default_cost_center": "Library - Company",
    "auto_create_payment_entries": True
}
```

## 📊 Dashboard & Analytics

### Key Metrics
- Total books and availability
- Active members and membership trends
- Issue/return statistics
- Overdue books and fine collection
- Popular books and categories

### Reports Available
- Monthly circulation reports
- Member activity reports
- Fine collection reports
- Book popularity analysis
- Inventory reports

## 🔧 API Endpoints

### Books API
```javascript
// Get books with filters
GET /api/method/library_management.library_management.api.get_books
?search=python&category=Technology&page=1&page_size=10

// Get book details
GET /api/method/library_management.library_management.api.get_book_details
?book_name=BOOK-001
```

### Transactions API
```javascript
// Issue a book
POST /api/method/library_management.library_management.api.issue_book
{
    "book_name": "BOOK-001",
    "member_name": "MEM-001",
    "notes": "Regular issue"
}

// Return a book
POST /api/method/library_management.library_management.api.return_book
{
    "transaction_name": "TXN-001",
    "condition_at_return": "Good",
    "notes": "Returned in good condition"
}
```

### Member Dashboard API
```javascript
// Get member dashboard
GET /api/method/library_management.library_management.api.get_member_dashboard
?member_name=MEM-001
```

## 🎨 Customization

### Custom Fields
Add custom fields to any doctype using Frappe's customization tools:

```python
# Example: Add custom field to Book
{
    "doctype": "Custom Field",
    "dt": "Book",
    "fieldname": "custom_rating",
    "fieldtype": "Rating",
    "label": "Book Rating"
}
```

### Custom Reports
Create custom reports using Frappe's Report Builder or custom Python reports.

### Themes
Customize the UI theme by modifying CSS files in `public/css/`.

## 🔒 Security & Permissions

### Role-based Access
- **System Manager**: Full access to all features
- **Librarian**: Book and member management, transactions
- **Library Member**: View own transactions, search books

### Data Security
- Row-level security for member data
- Audit trail for all transactions
- Secure API endpoints with authentication

## 📱 Mobile App Support

The system is fully responsive and works on mobile devices. For a native mobile experience, you can:

1. Use Frappe's mobile app framework
2. Create a PWA (Progressive Web App)
3. Integrate with existing mobile apps via API

## 🧪 Testing

```bash
# Run tests
bench run-tests --app library_management

# Run specific test
bench run-tests --app library_management --module library_management.library_management.doctype.book.test_book
```

## 📈 Performance Optimization

### Database Optimization
- Proper indexing on frequently queried fields
- Optimized queries for large datasets
- Database cleanup for old transactions

### Caching
- Redis caching for frequently accessed data
- Browser caching for static assets
- API response caching

## 🔄 Backup & Migration

### Regular Backups
```bash
# Database backup
bench backup --with-files

# Restore backup
bench restore /path/to/backup
```

### Data Migration
Use Frappe's data migration tools for upgrading between versions.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Standards
- Follow PEP 8 for Python code
- Use ESLint for JavaScript
- Write comprehensive tests
- Document new features

## 📞 Support

- **Documentation**: [Wiki](https://github.com/Emmafidelis/library_management/wiki)
- **Issues**: [GitHub Issues](https://github.com/Emmafidelis/library_management/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Emmafidelis/library_management/discussions)
- **Email**: emanuelkagombora28@gmail.com

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](license.txt) file for details.

## 🙏 Acknowledgments

- Built on the amazing [Frappe Framework](https://frappeframework.com/)
- Inspired by modern library management needs
- Thanks to all contributors and the open-source community

---

**Made with ❤️ by Emanuel Fidelis**
