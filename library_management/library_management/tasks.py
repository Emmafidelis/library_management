# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, add_days, getdate, date_diff
from frappe import _


def send_due_date_reminders():
	"""Send email reminders for books due in the next few days"""
	try:
		settings = frappe.get_single("Library Settings")
		if not settings.enable_email_notifications:
			return
			
		reminder_days = settings.reminder_days_before_due or 3
		due_date = add_days(nowdate(), reminder_days)
		
		# Get transactions due soon
		transactions = frappe.get_all(
			"Library Transaction",
			filters={
				"transaction_type": "Issue",
				"status": "Active",
				"due_date": due_date
			},
			fields=["name", "member", "book", "due_date"]
		)
		
		for transaction in transactions:
			send_due_reminder_email(transaction)
			
		frappe.log_error(f"Sent {len(transactions)} due date reminders", "Library Due Date Reminders")
		
	except Exception as e:
		frappe.log_error(f"Error sending due date reminders: {str(e)}", "Library Due Date Reminders Error")


def mark_overdue_books():
	"""Mark books as overdue and calculate fines"""
	try:
		# Get overdue transactions
		overdue_transactions = frappe.get_all(
			"Library Transaction",
			filters={
				"transaction_type": "Issue",
				"status": "Active",
				"due_date": ["<", nowdate()]
			},
			fields=["name", "member", "book", "due_date"]
		)
		
		settings = frappe.get_single("Library Settings")
		fine_per_day = settings.fine_per_day or 1.0
		
		for transaction in overdue_transactions:
			# Update transaction status
			doc = frappe.get_doc("Library Transaction", transaction.name)
			doc.status = "Overdue"
			doc.save()
			
			# Calculate and create fine
			overdue_days = date_diff(nowdate(), transaction.due_date)
			fine_amount = overdue_days * fine_per_day
			
			# Check if fine already exists
			existing_fine = frappe.db.exists("Library Fine", {
				"transaction": transaction.name,
				"fine_type": "Overdue"
			})
			
			if not existing_fine:
				fine = frappe.get_doc({
					"doctype": "Library Fine",
					"member": transaction.member,
					"book": transaction.book,
					"transaction": transaction.name,
					"fine_type": "Overdue",
					"fine_amount": fine_amount,
					"reason": f"Book overdue by {overdue_days} days"
				})
				fine.insert()
				
		frappe.log_error(f"Marked {len(overdue_transactions)} books as overdue", "Library Overdue Processing")
		
	except Exception as e:
		frappe.log_error(f"Error marking overdue books: {str(e)}", "Library Overdue Processing Error")


def expire_reservations():
	"""Expire old reservations"""
	try:
		# Get expired reservations
		expired_reservations = frappe.get_all(
			"Book Reservation",
			filters={
				"status": "Active",
				"expiry_date": ["<", nowdate()]
			},
			fields=["name"]
		)
		
		for reservation in expired_reservations:
			doc = frappe.get_doc("Book Reservation", reservation.name)
			doc.status = "Expired"
			doc.save()
			
		frappe.log_error(f"Expired {len(expired_reservations)} reservations", "Library Reservation Expiry")
		
	except Exception as e:
		frappe.log_error(f"Error expiring reservations: {str(e)}", "Library Reservation Expiry Error")


def send_overdue_reminders():
	"""Send weekly reminders for overdue books"""
	try:
		settings = frappe.get_single("Library Settings")
		if not settings.enable_email_notifications:
			return
			
		# Get overdue transactions
		overdue_transactions = frappe.get_all(
			"Library Transaction",
			filters={
				"transaction_type": "Issue",
				"status": "Overdue"
			},
			fields=["name", "member", "book", "due_date"]
		)
		
		for transaction in overdue_transactions:
			send_overdue_reminder_email(transaction)
			
		frappe.log_error(f"Sent {len(overdue_transactions)} overdue reminders", "Library Overdue Reminders")
		
	except Exception as e:
		frappe.log_error(f"Error sending overdue reminders: {str(e)}", "Library Overdue Reminders Error")


def update_member_statistics():
	"""Update member statistics weekly"""
	try:
		members = frappe.get_all("Member", fields=["name"])
		
		for member in members:
			doc = frappe.get_doc("Member", member.name)
			doc.update_current_stats()
			doc.save()
			
		frappe.log_error(f"Updated statistics for {len(members)} members", "Library Member Statistics Update")
		
	except Exception as e:
		frappe.log_error(f"Error updating member statistics: {str(e)}", "Library Member Statistics Error")


def generate_monthly_reports():
	"""Generate monthly library reports"""
	try:
		# This would generate and email monthly reports
		# For now, just log the activity
		frappe.log_error("Monthly reports generated", "Library Monthly Reports")
		
	except Exception as e:
		frappe.log_error(f"Error generating monthly reports: {str(e)}", "Library Monthly Reports Error")


def send_due_reminder_email(transaction):
	"""Send due date reminder email to member"""
	try:
		member = frappe.get_doc("Member", transaction.member)
		book = frappe.get_doc("Book", transaction.book)
		
		if not member.email:
			return
			
		subject = f"Library Reminder: {book.title} due soon"
		message = f"""
		Dear {member.member_name},
		
		This is a friendly reminder that the following book is due for return:
		
		Book: {book.title}
		Author: {book.author}
		Due Date: {transaction.due_date}
		
		Please return the book on or before the due date to avoid any late fees.
		
		Thank you,
		Library Management System
		"""
		
		frappe.sendmail(
			recipients=[member.email],
			subject=subject,
			message=message
		)
		
	except Exception as e:
		frappe.log_error(f"Error sending due reminder email: {str(e)}", "Library Email Error")


def send_overdue_reminder_email(transaction):
	"""Send overdue reminder email to member"""
	try:
		member = frappe.get_doc("Member", transaction.member)
		book = frappe.get_doc("Book", transaction.book)
		
		if not member.email:
			return
			
		overdue_days = date_diff(nowdate(), transaction.due_date)
		
		subject = f"Library Notice: {book.title} is overdue"
		message = f"""
		Dear {member.member_name},
		
		The following book is overdue for return:
		
		Book: {book.title}
		Author: {book.author}
		Due Date: {transaction.due_date}
		Days Overdue: {overdue_days}
		
		Please return the book immediately to avoid additional late fees.
		
		Thank you,
		Library Management System
		"""
		
		frappe.sendmail(
			recipients=[member.email],
			subject=subject,
			message=message
		)
		
	except Exception as e:
		frappe.log_error(f"Error sending overdue reminder email: {str(e)}", "Library Email Error")


def process_book_reservations():
	"""Process book reservations when books become available"""
	try:
		# Get available books that have reservations
		available_books = frappe.db.sql("""
			SELECT DISTINCT br.book
			FROM `tabBook Reservation` br
			JOIN `tabBook` b ON br.book = b.name
			WHERE br.status = 'Active'
			AND b.available_copies > 0
			ORDER BY br.priority ASC, br.reservation_date ASC
		""", as_dict=True)
		
		for book_data in available_books:
			# Get the next reservation in queue
			reservation = frappe.get_all(
				"Book Reservation",
				filters={
					"book": book_data.book,
					"status": "Active"
				},
				fields=["name", "member"],
				order_by="priority asc, reservation_date asc",
				limit=1
			)
			
			if reservation:
				# Notify member that book is available
				send_book_available_notification(reservation[0])
				
	except Exception as e:
		frappe.log_error(f"Error processing book reservations: {str(e)}", "Library Reservation Processing Error")


def send_book_available_notification(reservation):
	"""Send notification when reserved book becomes available"""
	try:
		reservation_doc = frappe.get_doc("Book Reservation", reservation.name)
		member = frappe.get_doc("Member", reservation.member)
		book = frappe.get_doc("Book", reservation_doc.book)
		
		if not member.email:
			return
			
		subject = f"Library Notification: {book.title} is now available"
		message = f"""
		Dear {member.member_name},
		
		Good news! The book you reserved is now available:
		
		Book: {book.title}
		Author: {book.author}
		
		Please visit the library within 3 days to collect your reserved book.
		
		Thank you,
		Library Management System
		"""
		
		frappe.sendmail(
			recipients=[member.email],
			subject=subject,
			message=message
		)
		
		# Mark notification as sent
		reservation_doc.notification_sent = 1
		reservation_doc.save()
		
	except Exception as e:
		frappe.log_error(f"Error sending book available notification: {str(e)}", "Library Email Error")
