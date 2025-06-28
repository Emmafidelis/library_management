# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, nowdate, cint
from frappe import _


def is_erpnext_installed():
	"""Check if ERPNext is installed"""
	return "erpnext" in frappe.get_installed_apps()


def get_library_settings():
	"""Get library settings"""
	return frappe.get_single("Library Settings")


def create_customer_for_member(member):
	"""Create ERPNext Customer for library member"""
	if not is_erpnext_installed():
		return None
		
	settings = get_library_settings()
	if not settings.enable_erpnext_integration:
		return None
	
	try:
		# Check if customer already exists
		existing_customer = frappe.db.get_value("Customer", {"custom_library_member": member.name})
		if existing_customer:
			return existing_customer
		
		# Create new customer
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": member.member_name,
			"customer_type": "Individual",
			"customer_group": settings.default_customer_group or "Individual",
			"territory": "All Territories",
			"custom_library_member": member.name,
			"custom_member_id": member.member_id,
			"custom_membership_type": member.membership_type,
			"email_id": member.email,
			"mobile_no": member.phone_number
		})
		
		customer.insert(ignore_permissions=True)
		
		# Update member with customer reference
		member.db_set("custom_erpnext_customer", customer.name)
		
		return customer.name
		
	except Exception as e:
		frappe.log_error(f"Error creating customer for member {member.name}: {str(e)}", "ERPNext Integration")
		return None


def create_item_for_book(book):
	"""Create ERPNext Item for library book"""
	if not is_erpnext_installed():
		return None
		
	settings = get_library_settings()
	if not settings.enable_erpnext_integration:
		return None
	
	try:
		# Check if item already exists
		existing_item = frappe.db.get_value("Item", {"custom_library_book": book.name})
		if existing_item:
			return existing_item
		
		# Create new item
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": f"BOOK-{book.name}",
			"item_name": book.title,
			"item_group": "Library Books",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"is_sales_item": 0,
			"is_purchase_item": 1,
			"is_fixed_asset": 1,
			"asset_category": "Library Assets",
			"custom_library_book": book.name,
			"custom_isbn": book.isbn,
			"custom_author": book.author,
			"custom_category": book.category,
			"description": f"{book.title} by {book.author}"
		})
		
		item.insert(ignore_permissions=True)
		
		# Update book with item reference
		book.db_set("custom_erpnext_item", item.name)
		
		return item.name
		
	except Exception as e:
		frappe.log_error(f"Error creating item for book {book.name}: {str(e)}", "ERPNext Integration")
		return None


def create_asset_for_book(book):
	"""Create ERPNext Asset for library book"""
	if not is_erpnext_installed():
		return None
		
	settings = get_library_settings()
	if not settings.enable_erpnext_integration:
		return None
	
	try:
		# Ensure item exists
		item_code = create_item_for_book(book)
		if not item_code:
			return None
		
		# Create assets for each copy
		assets_created = []
		
		for copy_num in range(1, book.total_copies + 1):
			asset_name = f"{book.name}-COPY-{copy_num:03d}"
			
			# Check if asset already exists
			existing_asset = frappe.db.get_value("Asset", {"asset_name": asset_name})
			if existing_asset:
				assets_created.append(existing_asset)
				continue
			
			asset = frappe.get_doc({
				"doctype": "Asset",
				"asset_name": asset_name,
				"item_code": item_code,
				"asset_category": "Library Assets",
				"company": frappe.defaults.get_global_default("company"),
				"purchase_date": book.acquisition_date or nowdate(),
				"gross_purchase_amount": book.price or 0,
				"location": book.location or "Library",
				"custodian": frappe.session.user,
				"custom_library_book": book.name,
				"custom_copy_number": copy_num,
				"custom_barcode": f"{book.barcode}-{copy_num:03d}" if book.barcode else None
			})
			
			asset.insert(ignore_permissions=True)
			assets_created.append(asset.name)
		
		return assets_created
		
	except Exception as e:
		frappe.log_error(f"Error creating assets for book {book.name}: {str(e)}", "ERPNext Integration")
		return None


def create_sales_invoice_for_fine(fine):
	"""Create ERPNext Sales Invoice for library fine"""
	if not is_erpnext_installed():
		return None
		
	settings = get_library_settings()
	if not settings.enable_erpnext_integration or not settings.auto_create_payment_entries:
		return None
	
	try:
		member = frappe.get_doc("Member", fine.member)
		
		# Ensure customer exists
		customer = create_customer_for_member(member)
		if not customer:
			return None
		
		# Create sales invoice
		invoice = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": customer,
			"posting_date": fine.fine_date,
			"due_date": fine.due_date or nowdate(),
			"custom_library_fine": fine.name,
			"custom_fine_type": fine.fine_type,
			"items": [{
				"item_code": "LIBRARY-FINE",
				"item_name": f"Library Fine - {fine.fine_type}",
				"description": f"Library fine for {fine.fine_type}",
				"qty": 1,
				"rate": fine.fine_amount,
				"income_account": settings.default_income_account,
				"cost_center": settings.default_cost_center
			}]
		})
		
		invoice.insert(ignore_permissions=True)
		invoice.submit()
		
		# Update fine with invoice reference
		fine.db_set("custom_erpnext_invoice", invoice.name)
		
		return invoice.name
		
	except Exception as e:
		frappe.log_error(f"Error creating sales invoice for fine {fine.name}: {str(e)}", "ERPNext Integration")
		return None


def create_payment_entry_for_fine(fine, payment_amount, payment_method="Cash"):
	"""Create ERPNext Payment Entry for fine payment"""
	if not is_erpnext_installed():
		return None
		
	settings = get_library_settings()
	if not settings.enable_erpnext_integration or not settings.auto_create_payment_entries:
		return None
	
	try:
		# Get the sales invoice
		invoice_name = fine.custom_erpnext_invoice
		if not invoice_name:
			invoice_name = create_sales_invoice_for_fine(fine)
			if not invoice_name:
				return None
		
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		
		# Create payment entry
		payment = frappe.get_doc({
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": invoice.customer,
			"posting_date": nowdate(),
			"paid_amount": payment_amount,
			"received_amount": payment_amount,
			"mode_of_payment": payment_method,
			"custom_library_fine": fine.name,
			"references": [{
				"reference_doctype": "Sales Invoice",
				"reference_name": invoice_name,
				"allocated_amount": payment_amount
			}]
		})
		
		payment.insert(ignore_permissions=True)
		payment.submit()
		
		return payment.name
		
	except Exception as e:
		frappe.log_error(f"Error creating payment entry for fine {fine.name}: {str(e)}", "ERPNext Integration")
		return None


def sync_employee_to_member():
	"""Sync ERPNext employees to library members"""
	if not is_erpnext_installed():
		return
		
	settings = get_library_settings()
	if not settings.enable_erpnext_integration:
		return
	
	try:
		# Get all active employees
		employees = frappe.get_all("Employee", 
			filters={"status": "Active"},
			fields=["name", "employee_name", "personal_email", "cell_number", "department", "designation"]
		)
		
		for emp in employees:
			# Check if member already exists
			existing_member = frappe.db.get_value("Member", {"custom_employee": emp.name})
			if existing_member:
				continue
			
			# Determine membership type based on designation
			membership_type = "Staff"
			if emp.designation and "professor" in emp.designation.lower():
				membership_type = "Faculty"
			elif emp.designation and any(word in emp.designation.lower() for word in ["student", "intern"]):
				membership_type = "Student"
			
			# Create member
			member = frappe.get_doc({
				"doctype": "Member",
				"member_name": emp.employee_name,
				"email": emp.personal_email,
				"phone_number": emp.cell_number,
				"membership_type": membership_type,
				"membership_date": nowdate(),
				"status": "Active",
				"custom_employee": emp.name,
				"custom_department": emp.department
			})
			
			member.insert(ignore_permissions=True)
			
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Error syncing employees to members: {str(e)}", "ERPNext Integration")


def create_purchase_order_for_books(vendor, books_list):
	"""Create ERPNext Purchase Order for book procurement"""
	if not is_erpnext_installed():
		return None
		
	settings = get_library_settings()
	if not settings.enable_erpnext_integration:
		return None
	
	try:
		# Create supplier if not exists
		supplier = create_supplier_for_vendor(vendor)
		if not supplier:
			return None
		
		# Create purchase order
		po = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": supplier,
			"transaction_date": nowdate(),
			"schedule_date": nowdate(),
			"custom_book_vendor": vendor.name,
			"items": []
		})
		
		for book_data in books_list:
			# Ensure item exists for book
			book = frappe.get_doc("Book", book_data.get("book"))
			item_code = create_item_for_book(book)
			
			if item_code:
				po.append("items", {
					"item_code": item_code,
					"qty": book_data.get("quantity", 1),
					"rate": book_data.get("rate", book.price or 0),
					"schedule_date": nowdate(),
					"custom_library_book": book.name
				})
		
		if po.items:
			po.insert(ignore_permissions=True)
			return po.name
		
		return None
		
	except Exception as e:
		frappe.log_error(f"Error creating purchase order: {str(e)}", "ERPNext Integration")
		return None


def create_supplier_for_vendor(vendor):
	"""Create ERPNext Supplier for book vendor"""
	if not is_erpnext_installed():
		return None
	
	try:
		# Check if supplier already exists
		existing_supplier = frappe.db.get_value("Supplier", {"custom_book_vendor": vendor.name})
		if existing_supplier:
			return existing_supplier
		
		# Create new supplier
		supplier = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": vendor.vendor_name,
			"supplier_type": "Company",
			"supplier_group": "Book Vendors",
			"custom_book_vendor": vendor.name,
			"custom_vendor_code": vendor.vendor_code,
			"email_id": vendor.email,
			"mobile_no": vendor.phone
		})
		
		supplier.insert(ignore_permissions=True)
		
		# Update vendor with supplier reference
		vendor.db_set("custom_erpnext_supplier", supplier.name)
		
		return supplier.name
		
	except Exception as e:
		frappe.log_error(f"Error creating supplier for vendor {vendor.name}: {str(e)}", "ERPNext Integration")
		return None


def get_library_dashboard_data():
	"""Get library data for ERPNext dashboard"""
	if not is_erpnext_installed():
		return {}
	
	try:
		data = {
			"total_books": frappe.db.count("Book"),
			"total_members": frappe.db.count("Member", {"status": "Active"}),
			"books_issued": frappe.db.count("Library Transaction", {"transaction_type": "Issue", "status": "Active"}),
			"overdue_books": frappe.db.sql("""
				SELECT COUNT(*) FROM `tabLibrary Transaction` 
				WHERE transaction_type = 'Issue' 
				AND status = 'Active' 
				AND due_date < %s
			""", [nowdate()])[0][0],
			"total_fines": frappe.db.sql("""
				SELECT SUM(outstanding_amount) 
				FROM `tabLibrary Fine` 
				WHERE status IN ('Unpaid', 'Partially Paid')
			""")[0][0] or 0
		}
		
		return data
		
	except Exception as e:
		frappe.log_error(f"Error getting library dashboard data: {str(e)}", "ERPNext Integration")
		return {}
