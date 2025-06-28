# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, add_years
from frappe import _


def after_install():
	"""Setup library management system after installation"""
	try:
		create_default_roles()
		create_default_settings()
		create_default_categories()
		create_sample_data()
		setup_email_templates()
		create_default_workflows()
		setup_custom_fields()
		
		frappe.db.commit()
		
		print("✅ Library Management System installed successfully!")
		print("📚 Default data and configurations have been created.")
		print("🔧 Please configure Library Settings according to your needs.")
		
	except Exception as e:
		frappe.log_error(f"Error during installation: {str(e)}", "Library Management Installation")
		print(f"❌ Installation error: {str(e)}")


def create_default_roles():
	"""Create default roles for library management"""
	roles = [
		{
			"role_name": "Librarian",
			"description": "Library staff with full access to library operations"
		},
		{
			"role_name": "Library Member",
			"description": "Library members with limited access to their own data"
		},
		{
			"role_name": "Library Admin",
			"description": "Library administrator with full system access"
		}
	]
	
	for role_data in roles:
		if not frappe.db.exists("Role", role_data["role_name"]):
			role = frappe.get_doc({
				"doctype": "Role",
				"role_name": role_data["role_name"],
				"description": role_data["description"]
			})
			role.insert(ignore_permissions=True)
			print(f"✅ Created role: {role_data['role_name']}")


def create_default_settings():
	"""Create default library settings"""
	if not frappe.db.exists("Library Settings", "Library Settings"):
		settings = frappe.get_doc({
			"doctype": "Library Settings",
			"library_name": "Central Library",
			"library_code": "CL001",
			"default_loan_period": 14,
			"max_renewals": 2,
			"grace_period_days": 3,
			"fine_per_day": 1.0,
			"max_fine_amount": 100.0,
			"student_max_books": 3,
			"faculty_max_books": 10,
			"staff_max_books": 5,
			"public_max_books": 2,
			"student_loan_days": 14,
			"faculty_loan_days": 30,
			"staff_loan_days": 21,
			"public_loan_days": 14,
			"enable_email_notifications": 1,
			"reminder_days_before_due": 3,
			"overdue_reminder_frequency": "Daily",
			"enable_barcode_scanning": 1,
			"barcode_prefix": "LIB",
			"auto_generate_barcodes": 1,
			"barcode_format": "Code128"
		})
		settings.insert(ignore_permissions=True)
		print("✅ Created default library settings")


def create_default_categories():
	"""Create default book categories and other master data"""
	# Create default item group for library books if ERPNext is installed
	try:
		if "erpnext" in frappe.get_installed_apps():
			if not frappe.db.exists("Item Group", "Library Books"):
				item_group = frappe.get_doc({
					"doctype": "Item Group",
					"item_group_name": "Library Books",
					"parent_item_group": "All Item Groups",
					"is_group": 0
				})
				item_group.insert(ignore_permissions=True)
				print("✅ Created Library Books item group")
			
			# Create asset category
			if not frappe.db.exists("Asset Category", "Library Assets"):
				asset_category = frappe.get_doc({
					"doctype": "Asset Category",
					"asset_category_name": "Library Assets",
					"depreciation_method": "Straight Line",
					"total_number_of_depreciations": 5,
					"frequency_of_depreciation": 12
				})
				asset_category.insert(ignore_permissions=True)
				print("✅ Created Library Assets category")
				
			# Create customer group
			if not frappe.db.exists("Customer Group", "Library Members"):
				customer_group = frappe.get_doc({
					"doctype": "Customer Group",
					"customer_group_name": "Library Members",
					"parent_customer_group": "All Customer Groups",
					"is_group": 0
				})
				customer_group.insert(ignore_permissions=True)
				print("✅ Created Library Members customer group")
				
	except Exception as e:
		print(f"⚠️ ERPNext integration setup skipped: {str(e)}")


def create_sample_data():
	"""Create sample data for demonstration"""
	# Create sample books
	sample_books = [
		{
			"title": "The Great Gatsby",
			"author": "F. Scott Fitzgerald",
			"isbn": "9780743273565",
			"category": "Fiction",
			"language": "English",
			"publisher": "Scribner",
			"total_copies": 3,
			"location": "Fiction Section",
			"shelf_number": "F-001"
		},
		{
			"title": "To Kill a Mockingbird",
			"author": "Harper Lee",
			"isbn": "9780061120084",
			"category": "Fiction",
			"language": "English",
			"publisher": "Harper Perennial",
			"total_copies": 2,
			"location": "Fiction Section",
			"shelf_number": "F-002"
		},
		{
			"title": "Python Programming",
			"author": "John Smith",
			"isbn": "9781234567890",
			"category": "Technology",
			"language": "English",
			"publisher": "Tech Books",
			"total_copies": 5,
			"location": "Technology Section",
			"shelf_number": "T-001"
		}
	]
	
	for book_data in sample_books:
		if not frappe.db.exists("Book", {"isbn": book_data["isbn"]}):
			book = frappe.get_doc({
				"doctype": "Book",
				**book_data
			})
			book.insert(ignore_permissions=True)
			print(f"✅ Created sample book: {book_data['title']}")
	
	# Create sample member
	if not frappe.db.exists("Member", {"email": "demo@library.com"}):
		member = frappe.get_doc({
			"doctype": "Member",
			"member_name": "Demo User",
			"email": "demo@library.com",
			"phone_number": "1234567890",
			"membership_type": "Public",
			"membership_date": nowdate(),
			"status": "Active"
		})
		member.insert(ignore_permissions=True)
		print("✅ Created demo member")


def setup_email_templates():
	"""Setup default email templates"""
	templates = [
		{
			"name": "Library Due Reminder",
			"subject": "Library Reminder: Book due soon",
			"response": """
			<p>Dear {{ member_name }},</p>
			<p>This is a friendly reminder that the following book is due for return:</p>
			<ul>
				<li><strong>Book:</strong> {{ book_title }}</li>
				<li><strong>Author:</strong> {{ book_author }}</li>
				<li><strong>Due Date:</strong> {{ due_date }}</li>
			</ul>
			<p>Please return the book on or before the due date to avoid any late fees.</p>
			<p>Thank you,<br>Library Management System</p>
			"""
		},
		{
			"name": "Library Overdue Notice",
			"subject": "Library Notice: Overdue book",
			"response": """
			<p>Dear {{ member_name }},</p>
			<p>The following book is overdue for return:</p>
			<ul>
				<li><strong>Book:</strong> {{ book_title }}</li>
				<li><strong>Author:</strong> {{ book_author }}</li>
				<li><strong>Due Date:</strong> {{ due_date }}</li>
				<li><strong>Days Overdue:</strong> {{ overdue_days }}</li>
			</ul>
			<p>Please return the book immediately to avoid additional late fees.</p>
			<p>Thank you,<br>Library Management System</p>
			"""
		}
	]
	
	for template_data in templates:
		if not frappe.db.exists("Email Template", template_data["name"]):
			template = frappe.get_doc({
				"doctype": "Email Template",
				"name": template_data["name"],
				"subject": template_data["subject"],
				"response": template_data["response"]
			})
			template.insert(ignore_permissions=True)
			print(f"✅ Created email template: {template_data['name']}")


def create_default_workflows():
	"""Create default workflows for library processes"""
	# This would create workflows for book approval, member registration, etc.
	# For now, we'll skip this as it's complex and optional
	pass


def setup_custom_fields():
	"""Setup custom fields for ERPNext integration"""
	if "erpnext" not in frappe.get_installed_apps():
		return
	
	custom_fields = [
		{
			"dt": "Customer",
			"fieldname": "custom_library_member",
			"label": "Library Member",
			"fieldtype": "Link",
			"options": "Member"
		},
		{
			"dt": "Customer",
			"fieldname": "custom_member_id",
			"label": "Member ID",
			"fieldtype": "Data"
		},
		{
			"dt": "Customer",
			"fieldname": "custom_membership_type",
			"label": "Membership Type",
			"fieldtype": "Data"
		},
		{
			"dt": "Item",
			"fieldname": "custom_library_book",
			"label": "Library Book",
			"fieldtype": "Link",
			"options": "Book"
		},
		{
			"dt": "Item",
			"fieldname": "custom_isbn",
			"label": "ISBN",
			"fieldtype": "Data"
		},
		{
			"dt": "Item",
			"fieldname": "custom_author",
			"label": "Author",
			"fieldtype": "Data"
		},
		{
			"dt": "Item",
			"fieldname": "custom_category",
			"label": "Book Category",
			"fieldtype": "Data"
		}
	]
	
	for field_data in custom_fields:
		if not frappe.db.exists("Custom Field", {"dt": field_data["dt"], "fieldname": field_data["fieldname"]}):
			custom_field = frappe.get_doc({
				"doctype": "Custom Field",
				**field_data
			})
			custom_field.insert(ignore_permissions=True)
			print(f"✅ Created custom field: {field_data['fieldname']} for {field_data['dt']}")


def before_uninstall():
	"""Cleanup before uninstalling"""
	try:
		# Remove custom fields
		custom_fields = frappe.get_all("Custom Field", 
			filters={"fieldname": ["like", "custom_library_%"]},
			fields=["name"]
		)
		
		for field in custom_fields:
			frappe.delete_doc("Custom Field", field.name, ignore_permissions=True)
		
		# Remove email templates
		templates = ["Library Due Reminder", "Library Overdue Notice"]
		for template in templates:
			if frappe.db.exists("Email Template", template):
				frappe.delete_doc("Email Template", template, ignore_permissions=True)
		
		frappe.db.commit()
		print("✅ Library Management System uninstalled successfully!")
		
	except Exception as e:
		frappe.log_error(f"Error during uninstallation: {str(e)}", "Library Management Uninstallation")
		print(f"❌ Uninstallation error: {str(e)}")


def get_setup_status():
	"""Get setup status for the library system"""
	status = {
		"library_settings": frappe.db.exists("Library Settings", "Library Settings"),
		"sample_books": frappe.db.count("Book") > 0,
		"sample_members": frappe.db.count("Member") > 0,
		"email_templates": frappe.db.exists("Email Template", "Library Due Reminder"),
		"erpnext_integration": "erpnext" in frappe.get_installed_apps()
	}
	
	return status
