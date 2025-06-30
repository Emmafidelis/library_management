# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, getdate, now_datetime, date_diff
from frappe import _


class LibraryTransaction(Document):
	def validate(self):
		self.validate_member_eligibility()
		self.validate_book_availability()
		self.set_due_date()
		self.calculate_fine()
		
	def before_save(self):
		self.set_librarian()
		
	def on_submit(self):
		self.update_book_status()
		self.update_member_stats()
		
	def validate_member_eligibility(self):
		"""Validate if member can perform this transaction"""
		if self.transaction_type == "Issue":
			member = frappe.get_doc("Member", self.member)
			can_issue, message = member.can_issue_book()
			if not can_issue:
				frappe.throw(message)
				
	def validate_book_availability(self):
		"""Validate if book is available for the transaction"""
		if self.transaction_type == "Issue":
			book = frappe.get_doc("Book", self.book)
			if not book.can_be_issued():
				frappe.throw(_("Book {0} is not available for issue").format(book.title))
				
	def set_due_date(self):
		"""Set due date based on membership type and library settings"""
		if self.transaction_type == "Issue" and not self.due_date:
			member = frappe.get_doc("Member", self.member)
			
			# Default loan periods by membership type
			loan_periods = {
				"Student": 14,    # 14 days
				"Faculty": 30,    # 30 days
				"Staff": 21,      # 21 days
				"Public": 14,     # 14 days
				"Senior Citizen": 21,  # 21 days
				"Child": 7        # 7 days
			}
			
			days = loan_periods.get(member.membership_type, 14)
			self.due_date = add_days(self.transaction_date, days)
			self.issue_date = getdate(self.transaction_date)
			
	def calculate_fine(self):
		"""Calculate fine for overdue books"""
		if self.transaction_type == "Return" and self.return_date and self.due_date:
			return_date = getdate(self.return_date)
			due_date = getdate(self.due_date)
			
			if return_date > due_date:
				overdue_days = date_diff(return_date, due_date)
				fine_per_day = 1.0  # Default fine per day
				
				self.fine_applicable = 1
				self.fine_amount = overdue_days * fine_per_day
				self.fine_reason = "Overdue"
				
	def set_librarian(self):
		"""Set current user as librarian"""
		if not self.librarian:
			self.librarian = frappe.session.user
			
	def update_book_status(self):
		"""Update book availability after transaction"""
		book = frappe.get_doc("Book", self.book)
		
		if self.transaction_type == "Issue":
			book.issue_book()
		elif self.transaction_type == "Return":
			book.return_book()
			
	def update_member_stats(self):
		"""Update member statistics"""
		member = frappe.get_doc("Member", self.member)
		member.update_current_stats()
		member.save()
		
	def can_renew(self):
		"""Check if transaction can be renewed"""
		if self.transaction_type != "Issue":
			return False, _("Only issued books can be renewed")
			
		if self.status != "Active":
			return False, _("Book is not currently active")
			
		if self.renewal_count >= self.max_renewals_allowed:
			return False, _("Maximum renewals exceeded")
			
		if self.fine_applicable and not self.fine_paid:
			return False, _("Please clear outstanding fines before renewal")
			
		return True, ""
		
	def renew_book(self):
		"""Renew the book loan"""
		can_renew, message = self.can_renew()
		if not can_renew:
			frappe.throw(message)
			
		# Create renewal transaction
		renewal = frappe.get_doc({
			"doctype": "Library Transaction",
			"transaction_type": "Renewal",
			"member": self.member,
			"book": self.book,
			"transaction_date": now_datetime(),
			"librarian": frappe.session.user
		})
		renewal.insert()
		renewal.submit()
		
		# Update current transaction
		self.renewal_count += 1
		member = frappe.get_doc("Member", self.member)
		loan_periods = {
			"Student": 14, "Faculty": 30, "Staff": 21,
			"Public": 14, "Senior Citizen": 21, "Child": 7
		}
		days = loan_periods.get(member.membership_type, 14)
		self.due_date = add_days(nowdate(), days)
		self.save()
		
		return renewal
		
	def return_book(self, condition_at_return=None, notes=None):
		"""Process book return"""
		if self.transaction_type != "Issue":
			frappe.throw(_("Only issued books can be returned"))
			
		if self.status == "Returned":
			frappe.throw(_("Book is already returned"))
			
		self.transaction_type = "Return"
		self.return_date = now_datetime()
		self.status = "Returned"
		
		if condition_at_return:
			self.condition_at_return = condition_at_return
			
		if notes:
			self.notes = notes
			
		self.calculate_fine()
		self.save()
		self.submit()
		
		return self
