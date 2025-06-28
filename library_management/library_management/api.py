# library_management_system/library_management_system/api.py

import frappe
from frappe import _
import random
import string
from frappe.utils import now, nowdate, add_days, getdate, cint, flt
import math
import uuid
import json


@frappe.whitelist(allow_guest=True)
def get_books(search=None, category=None, language=None, status=None, page=1, page_size=10):
	"""Enhanced book search with multiple filters"""
	try:
		filters = {"status": ["!=", "Discarded"]}

		if search:
			# Search in title, author, ISBN, and keywords
			search_conditions = [
				["title", "like", f"%{search}%"],
				["author", "like", f"%{search}%"],
				["isbn", "like", f"%{search}%"],
				["keywords", "like", f"%{search}%"]
			]
			filters["name"] = ["in", frappe.db.sql_list("""
				SELECT name FROM `tabBook`
				WHERE title LIKE %(search)s
				OR author LIKE %(search)s
				OR isbn LIKE %(search)s
				OR keywords LIKE %(search)s
			""", {"search": f"%{search}%"})]

		if category:
			filters["category"] = category

		if language:
			filters["language"] = language

		if status:
			filters["status"] = status

		offset = (int(page) - 1) * int(page_size)
		books = frappe.get_all(
			"Book",
			filters=filters,
			fields=[
				"name", "title", "author", "category", "language", "status",
				"isbn", "publisher", "total_copies", "available_copies",
				"issued_copies", "location", "shelf_number", "book_type"
			],
			limit_start=offset,
			limit_page_length=int(page_size),
			order_by="title asc"
		)

		# Add availability status for each book
		for book in books:
			book["can_be_issued"] = book["available_copies"] > 0 and book["status"] == "Available"
			book["availability_status"] = get_book_availability_status(book["name"])

		total_books = frappe.db.count("Book", filters=filters)

		return {
			"books": books,
			"total_books": total_books,
			"page": int(page),
			"page_size": int(page_size),
			"total_pages": math.ceil(total_books / int(page_size)),
			"filters_applied": {
				"search": search,
				"category": category,
				"language": language,
				"status": status
			}
		}

	except Exception as e:
		frappe.log_error(f"Error fetching books: {str(e)}")
		return {"error": "An error occurred while fetching books."}


def get_book_availability_status(book_name):
	"""Get detailed availability status for a book"""
	book = frappe.get_doc("Book", book_name)
	return book.get_availability_status()


@frappe.whitelist()
def get_book_details(book_name):
	"""Get detailed information about a specific book"""
	try:
		book = frappe.get_doc("Book", book_name)

		# Get current transactions
		current_transactions = frappe.get_all(
			"Library Transaction",
			filters={"book": book_name, "status": "Active"},
			fields=["name", "member", "transaction_date", "due_date", "status"]
		)

		# Get reservation queue
		reservations = frappe.get_all(
			"Book Reservation",
			filters={"book": book_name, "status": "Active"},
			fields=["name", "member", "reservation_date", "priority"],
			order_by="priority asc, reservation_date asc"
		)

		return {
			"book_details": book.as_dict(),
			"availability": book.get_availability_status(),
			"current_transactions": current_transactions,
			"reservations": reservations
		}

	except Exception as e:
		frappe.log_error(f"Error fetching book details: {str(e)}")
		return {"error": "An error occurred while fetching book details."}


@frappe.whitelist()
def issue_book(book_name, member_name, notes=None):
	"""Issue a book to a member"""
	try:
		# Validate member eligibility
		member = frappe.get_doc("Member", member_name)
		can_issue, message = member.can_issue_book()
		if not can_issue:
			return {"success": False, "message": message}

		# Validate book availability
		book = frappe.get_doc("Book", book_name)
		if not book.can_be_issued():
			return {"success": False, "message": _("Book is not available for issue")}

		# Create transaction
		transaction = frappe.get_doc({
			"doctype": "Library Transaction",
			"transaction_type": "Issue",
			"member": member_name,
			"book": book_name,
			"transaction_date": now(),
			"notes": notes or "",
			"condition_at_issue": book.condition or "Good"
		})
		transaction.insert()
		transaction.submit()

		return {
			"success": True,
			"message": _("Book issued successfully"),
			"transaction": transaction.name,
			"due_date": transaction.due_date
		}

	except Exception as e:
		frappe.log_error(f"Error issuing book: {str(e)}")
		return {"success": False, "error": "An error occurred while issuing the book."}


@frappe.whitelist()
def return_book(transaction_name, condition_at_return=None, notes=None):
	"""Return a book"""
	try:
		transaction = frappe.get_doc("Library Transaction", transaction_name)
		returned_transaction = transaction.return_book(condition_at_return, notes)

		return {
			"success": True,
			"message": _("Book returned successfully"),
			"transaction": returned_transaction.name,
			"fine_applicable": returned_transaction.fine_applicable,
			"fine_amount": returned_transaction.fine_amount if returned_transaction.fine_applicable else 0
		}

	except Exception as e:
		frappe.log_error(f"Error returning book: {str(e)}")
		return {"success": False, "error": "An error occurred while returning the book."}


@frappe.whitelist()
def renew_book(transaction_name):
	"""Renew a book loan"""
	try:
		transaction = frappe.get_doc("Library Transaction", transaction_name)
		renewal = transaction.renew_book()

		return {
			"success": True,
			"message": _("Book renewed successfully"),
			"new_due_date": transaction.due_date,
			"renewal_count": transaction.renewal_count,
			"max_renewals": transaction.max_renewals_allowed
		}

	except Exception as e:
		frappe.log_error(f"Error renewing book: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_member_dashboard(member_name=None):
	"""Get member dashboard data"""
	try:
		if not member_name:
			# Get current user's member record
			user = frappe.session.user
			member_name = frappe.db.get_value("Member", {"user": user}, "name")
			if not member_name:
				return {"error": "No member record found for current user"}

		member = frappe.get_doc("Member", member_name)

		# Get current issued books
		issued_books = frappe.get_all(
			"Library Transaction",
			filters={"member": member_name, "transaction_type": "Issue", "status": "Active"},
			fields=["name", "book", "transaction_date", "due_date", "renewal_count", "max_renewals_allowed"]
		)

		# Add book details to issued books
		for transaction in issued_books:
			book = frappe.get_doc("Book", transaction["book"])
			transaction["book_title"] = book.title
			transaction["book_author"] = book.author
			transaction["can_renew"] = frappe.get_doc("Library Transaction", transaction["name"]).can_renew()[0]

			# Check if overdue
			if getdate(transaction["due_date"]) < getdate(nowdate()):
				transaction["is_overdue"] = True
				transaction["overdue_days"] = (getdate(nowdate()) - getdate(transaction["due_date"])).days
			else:
				transaction["is_overdue"] = False

		# Get outstanding fines
		outstanding_fines = frappe.get_all(
			"Library Fine",
			filters={"member": member_name, "status": ["in", ["Unpaid", "Partially Paid"]]},
			fields=["name", "fine_type", "fine_amount", "outstanding_amount", "fine_date", "due_date"]
		)

		# Get reading history (last 10 transactions)
		reading_history = frappe.get_all(
			"Library Transaction",
			filters={"member": member_name, "transaction_type": "Return"},
			fields=["book", "transaction_date", "return_date"],
			order_by="return_date desc",
			limit=10
		)

		# Add book details to reading history
		for transaction in reading_history:
			book = frappe.get_doc("Book", transaction["book"])
			transaction["book_title"] = book.title
			transaction["book_author"] = book.author

		return {
			"member_info": member.get_member_summary(),
			"issued_books": issued_books,
			"outstanding_fines": outstanding_fines,
			"reading_history": reading_history,
			"statistics": {
				"total_books_issued": len(issued_books),
				"total_outstanding_fines": sum([flt(fine["outstanding_amount"]) for fine in outstanding_fines]),
				"books_read_this_year": len(reading_history)
			}
		}

	except Exception as e:
		frappe.log_error(f"Error fetching member dashboard: {str(e)}")
		return {"error": "An error occurred while fetching member dashboard."}


@frappe.whitelist()
def get_library_analytics():
	"""Get library analytics and statistics"""
	try:
		# Basic statistics
		total_books = frappe.db.count("Book")
		total_members = frappe.db.count("Member", {"status": "Active"})
		total_issued = frappe.db.count("Library Transaction", {"transaction_type": "Issue", "status": "Active"})
		total_overdue = frappe.db.sql("""
			SELECT COUNT(*) FROM `tabLibrary Transaction`
			WHERE transaction_type = 'Issue'
			AND status = 'Active'
			AND due_date < %s
		""", [nowdate()])[0][0]

		# Books by category
		books_by_category = frappe.db.sql("""
			SELECT category, COUNT(*) as count
			FROM `tabBook`
			WHERE status != 'Discarded'
			GROUP BY category
			ORDER BY count DESC
		""", as_dict=True)

		# Monthly issue trends (last 12 months)
		monthly_issues = frappe.db.sql("""
			SELECT
				DATE_FORMAT(transaction_date, '%%Y-%%m') as month,
				COUNT(*) as issues
			FROM `tabLibrary Transaction`
			WHERE transaction_type = 'Issue'
			AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
			GROUP BY DATE_FORMAT(transaction_date, '%%Y-%%m')
			ORDER BY month
		""", as_dict=True)

		# Top borrowed books
		top_books = frappe.db.sql("""
			SELECT
				b.title,
				b.author,
				COUNT(t.name) as borrow_count
			FROM `tabBook` b
			JOIN `tabLibrary Transaction` t ON b.name = t.book
			WHERE t.transaction_type = 'Issue'
			GROUP BY b.name
			ORDER BY borrow_count DESC
			LIMIT 10
		""", as_dict=True)

		# Member statistics by type
		members_by_type = frappe.db.sql("""
			SELECT membership_type, COUNT(*) as count
			FROM `tabMember`
			WHERE status = 'Active'
			GROUP BY membership_type
		""", as_dict=True)

		return {
			"overview": {
				"total_books": total_books,
				"total_members": total_members,
				"total_issued": total_issued,
				"total_overdue": total_overdue,
				"availability_rate": round((total_books - total_issued) / total_books * 100, 2) if total_books > 0 else 0
			},
			"books_by_category": books_by_category,
			"monthly_trends": monthly_issues,
			"top_books": top_books,
			"members_by_type": members_by_type
		}

	except Exception as e:
		frappe.log_error(f"Error fetching library analytics: {str(e)}")
		return {"error": "An error occurred while fetching analytics."}


@frappe.whitelist()
def search_members(search=None, membership_type=None, status=None, page=1, page_size=20):
	"""Search and filter members"""
	try:
		filters = {}

		if search:
			filters["name"] = ["in", frappe.db.sql_list("""
				SELECT name FROM `tabMember`
				WHERE member_name LIKE %(search)s
				OR email LIKE %(search)s
				OR phone_number LIKE %(search)s
				OR member_id LIKE %(search)s
			""", {"search": f"%{search}%"})]

		if membership_type:
			filters["membership_type"] = membership_type

		if status:
			filters["status"] = status

		offset = (int(page) - 1) * int(page_size)
		members = frappe.get_all(
			"Member",
			filters=filters,
			fields=[
				"name", "member_name", "member_id", "email", "phone_number",
				"membership_type", "status", "membership_date", "expiry_date",
				"current_books_issued", "max_books_allowed", "total_fines"
			],
			limit_start=offset,
			limit_page_length=int(page_size),
			order_by="member_name asc"
		)

		total_members = frappe.db.count("Member", filters=filters)

		return {
			"members": members,
			"total_members": total_members,
			"page": int(page),
			"page_size": int(page_size),
			"total_pages": math.ceil(total_members / int(page_size))
		}

	except Exception as e:
		frappe.log_error(f"Error searching members: {str(e)}")
		return {"error": "An error occurred while searching members."}


@frappe.whitelist()
def generate_library_report(report_type, from_date, to_date, filters=None):
	"""Generate library report"""
	try:
		# Create report document
		report = frappe.get_doc({
			"doctype": "Library Report",
			"report_name": f"{report_type} - {from_date} to {to_date}",
			"report_type": report_type,
			"from_date": from_date,
			"to_date": to_date,
			"export_format": "Excel"
		})

		# Apply filters if provided
		if filters:
			filters_dict = json.loads(filters) if isinstance(filters, str) else filters
			for key, value in filters_dict.items():
				if hasattr(report, key):
					setattr(report, key, value)

		report.insert()

		# Generate the report
		data = report.generate_report()

		return {
			"success": True,
			"report_name": report.name,
			"file_url": report.file_attachment,
			"summary": data.get("summary", {}),
			"total_records": report.total_records
		}

	except Exception as e:
		frappe.log_error(f"Error generating report: {str(e)}")
		return {"success": False, "error": "An error occurred while generating the report."}


@frappe.whitelist()
def get_digital_resources(search=None, resource_type=None, category=None, access_level=None, page=1, page_size=10):
	"""Get digital resources with filters"""
	try:
		filters = {"status": ["in", ["Approved", "Published"]]}

		if search:
			filters["name"] = ["in", frappe.db.sql_list("""
				SELECT name FROM `tabDigital Resource`
				WHERE title LIKE %(search)s
				OR author LIKE %(search)s
				OR keywords LIKE %(search)s
			""", {"search": f"%{search}%"})]

		if resource_type:
			filters["resource_type"] = resource_type

		if category:
			filters["category"] = category

		if access_level:
			filters["access_level"] = access_level

		offset = (int(page) - 1) * int(page_size)
		resources = frappe.get_all(
			"Digital Resource",
			filters=filters,
			fields=[
				"name", "title", "author", "resource_type", "category",
				"access_level", "file_format", "file_size", "download_allowed",
				"total_downloads", "total_views", "average_rating"
			],
			limit_start=offset,
			limit_page_length=int(page_size),
			order_by="title asc"
		)

		total_resources = frappe.db.count("Digital Resource", filters=filters)

		return {
			"resources": resources,
			"total_resources": total_resources,
			"page": int(page),
			"page_size": int(page_size),
			"total_pages": math.ceil(total_resources / int(page_size))
		}

	except Exception as e:
		frappe.log_error(f"Error fetching digital resources: {str(e)}")
		return {"error": "An error occurred while fetching digital resources."}


@frappe.whitelist()
def access_digital_resource(resource_name, member_name=None):
	"""Access a digital resource"""
	try:
		if not member_name:
			# Get current user's member record
			user = frappe.session.user
			member_name = frappe.db.get_value("Member", {"user": user}, "name")
			if not member_name:
				return {"success": False, "message": "No member record found for current user"}

		resource = frappe.get_doc("Digital Resource", resource_name)
		member = frappe.get_doc("Member", member_name)

		# Check access permissions
		if resource.access_level == "Members Only" and member.status != "Active":
			return {"success": False, "message": "Active membership required"}

		if resource.access_level == "Faculty Only" and member.membership_type != "Faculty":
			return {"success": False, "message": "Faculty access only"}

		if resource.access_level == "Students Only" and member.membership_type != "Student":
			return {"success": False, "message": "Student access only"}

		# Update statistics
		resource.total_views += 1
		resource.last_accessed = now_datetime()
		resource.save()

		# Create access log
		frappe.get_doc({
			"doctype": "Digital Resource Access Log",
			"resource": resource_name,
			"member": member_name,
			"access_type": "View",
			"access_date": now_datetime()
		}).insert()

		return {
			"success": True,
			"resource_url": resource.file_attachment or resource.external_url,
			"download_allowed": resource.download_allowed,
			"access_duration": resource.access_duration_days
		}

	except Exception as e:
		frappe.log_error(f"Error accessing digital resource: {str(e)}")
		return {"success": False, "error": "An error occurred while accessing the resource."}


@frappe.whitelist()
def get_library_events(event_type=None, status=None, from_date=None, to_date=None, page=1, page_size=10):
	"""Get library events with filters"""
	try:
		filters = {}

		if event_type:
			filters["event_type"] = event_type

		if status:
			filters["status"] = status
		else:
			filters["status"] = ["!=", "Cancelled"]

		if from_date and to_date:
			filters["event_date"] = ["between", [from_date, to_date]]
		elif from_date:
			filters["event_date"] = [">=", from_date]

		offset = (int(page) - 1) * int(page_size)
		events = frappe.get_all(
			"Library Event",
			filters=filters,
			fields=[
				"name", "event_name", "event_type", "event_category", "event_date",
				"start_time", "end_time", "venue", "status", "registration_required",
				"max_participants", "current_registrations", "registration_fee"
			],
			limit_start=offset,
			limit_page_length=int(page_size),
			order_by="event_date asc"
		)

		total_events = frappe.db.count("Library Event", filters=filters)

		return {
			"events": events,
			"total_events": total_events,
			"page": int(page),
			"page_size": int(page_size),
			"total_pages": math.ceil(total_events / int(page_size))
		}

	except Exception as e:
		frappe.log_error(f"Error fetching library events: {str(e)}")
		return {"error": "An error occurred while fetching library events."}


@frappe.whitelist()
def register_for_event(event_name, member_name=None, notes=None):
	"""Register for a library event"""
	try:
		if not member_name:
			# Get current user's member record
			user = frappe.session.user
			member_name = frappe.db.get_value("Member", {"user": user}, "name")
			if not member_name:
				return {"success": False, "message": "No member record found for current user"}

		event = frappe.get_doc("Library Event", event_name)
		member = frappe.get_doc("Member", member_name)

		# Check if registration is required
		if not event.registration_required:
			return {"success": False, "message": "Registration not required for this event"}

		# Check if event is open for registration
		if event.status not in ["Planned", "Open for Registration"]:
			return {"success": False, "message": "Event is not open for registration"}

		# Check if already registered
		existing_registration = frappe.db.exists("Event Registration", {
			"event": event_name,
			"member": member_name
		})

		if existing_registration:
			return {"success": False, "message": "Already registered for this event"}

		# Check capacity
		if event.max_participants and event.current_registrations >= event.max_participants:
			return {"success": False, "message": "Event is full"}

		# Create registration
		registration = frappe.get_doc({
			"doctype": "Event Registration",
			"event": event_name,
			"member": member_name,
			"registration_date": nowdate(),
			"status": "Registered",
			"notes": notes or ""
		})
		registration.insert()

		# Update event registration count
		event.current_registrations += 1
		if event.current_registrations >= event.max_participants:
			event.status = "Full"
		event.save()

		return {
			"success": True,
			"message": "Successfully registered for the event",
			"registration_id": registration.name
		}

	except Exception as e:
		frappe.log_error(f"Error registering for event: {str(e)}")
		return {"success": False, "error": "An error occurred while registering for the event."}

