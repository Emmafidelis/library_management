# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate
from frappe import _


class Book(Document):
	def validate(self):
		self.validate_copies()
		self.update_availability()
		self.set_defaults()

	def validate_copies(self):
		"""Validate copy counts"""
		if self.total_copies < 1:
			frappe.throw(_("Total copies must be at least 1"))

		if self.damaged_copies > self.total_copies:
			frappe.throw(_("Damaged copies cannot exceed total copies"))

		# Calculate issued copies from transactions
		issued_count = frappe.db.count("Library Transaction", {
			"book": self.name,
			"transaction_type": "Issue",
			"return_date": ["is", "not set"]
		})

		self.issued_copies = issued_count

	def update_availability(self):
		"""Update available copies based on total, issued, and damaged copies"""
		self.available_copies = self.total_copies - self.issued_copies - cint(self.damaged_copies)

		# Update status based on availability
		if self.available_copies <= 0:
			if self.issued_copies > 0:
				self.status = "Issued"
			elif self.damaged_copies >= self.total_copies:
				self.status = "Damaged"
		else:
			self.status = "Available"

	def set_defaults(self):
		"""Set default values"""
		if not self.acquisition_date:
			self.acquisition_date = nowdate()

		if not self.condition:
			self.condition = "Good"

		if not self.currency:
			self.currency = frappe.defaults.get_global_default("currency")

	def can_be_issued(self):
		"""Check if book can be issued"""
		return self.available_copies > 0 and self.status == "Available"

	def issue_book(self):
		"""Issue a copy of the book"""
		if not self.can_be_issued():
			frappe.throw(_("Book is not available for issue"))

		self.issued_copies += 1
		self.update_availability()
		self.save()

	def return_book(self):
		"""Return a copy of the book"""
		if self.issued_copies <= 0:
			frappe.throw(_("No copies of this book are currently issued"))

		self.issued_copies -= 1
		self.update_availability()
		self.save()

	def get_availability_status(self):
		"""Get detailed availability status"""
		return {
			"total_copies": self.total_copies,
			"available_copies": self.available_copies,
			"issued_copies": self.issued_copies,
			"damaged_copies": self.damaged_copies,
			"can_be_issued": self.can_be_issued()
		}
