# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_years, cint, flt, getdate
from frappe import _
import uuid


class Member(Document):
	def validate(self):
		self.validate_email()
		self.set_member_id()
		self.set_membership_limits()
		self.calculate_expiry_date()
		self.update_current_stats()

	def validate_email(self):
		"""Validate email format and uniqueness"""
		if self.email:
			# Check if email already exists for another member
			existing = frappe.db.get_value("Member", {"email": self.email, "name": ["!=", self.name]})
			if existing:
				frappe.throw(_("Email {0} already exists for another member").format(self.email))

	def set_member_id(self):
		"""Generate unique member ID if not set"""
		if not self.member_id:
			# Generate member ID based on membership type and sequence
			prefix_map = {
				"Student": "STU",
				"Faculty": "FAC",
				"Staff": "STF",
				"Public": "PUB",
				"Senior Citizen": "SEN",
				"Child": "CHD"
			}
			prefix = prefix_map.get(self.membership_type, "MEM")

			# Get next sequence number
			last_member = frappe.db.sql("""
				SELECT member_id FROM `tabMember`
				WHERE member_id LIKE %s
				ORDER BY creation DESC LIMIT 1
			""", f"{prefix}%")

			if last_member and last_member[0][0]:
				last_num = int(last_member[0][0].split('-')[-1])
				new_num = last_num + 1
			else:
				new_num = 1

			self.member_id = f"{prefix}-{new_num:04d}"

	def set_membership_limits(self):
		"""Set max books allowed based on membership type"""
		if not self.max_books_allowed:
			limits = {
				"Student": 3,
				"Faculty": 10,
				"Staff": 5,
				"Public": 2,
				"Senior Citizen": 3,
				"Child": 2
			}
			self.max_books_allowed = limits.get(self.membership_type, 2)

	def calculate_expiry_date(self):
		"""Calculate membership expiry date"""
		if not self.expiry_date and self.membership_date:
			# Default membership validity periods
			validity_periods = {
				"Student": 1,  # 1 year
				"Faculty": 2,  # 2 years
				"Staff": 2,    # 2 years
				"Public": 1,   # 1 year
				"Senior Citizen": 1,  # 1 year
				"Child": 1     # 1 year
			}
			years = validity_periods.get(self.membership_type, 1)
			self.expiry_date = add_years(self.membership_date, years)

	def update_current_stats(self):
		"""Update current books issued and total fines"""
		# Count current issued books
		issued_count = frappe.db.count("Library Transaction", {
			"member": self.name,
			"transaction_type": "Issue",
			"return_date": ["is", "not set"]
		})
		self.current_books_issued = issued_count

		# Calculate total outstanding fines
		total_fines = frappe.db.sql("""
			SELECT SUM(fine_amount)
			FROM `tabLibrary Fine`
			WHERE member = %s AND status = 'Unpaid'
		""", self.name)[0][0] or 0
		self.total_fines = flt(total_fines)

	def can_issue_book(self):
		"""Check if member can issue more books"""
		if self.status != "Active":
			return False, _("Member account is not active")

		if getdate(self.expiry_date) < getdate(nowdate()):
			return False, _("Membership has expired")

		if self.current_books_issued >= self.max_books_allowed:
			return False, _("Maximum book limit reached")

		if self.total_fines > 0:
			return False, _("Please clear outstanding fines before issuing new books")

		return True, ""

	def get_member_summary(self):
		"""Get member summary for dashboard"""
		return {
			"member_name": self.member_name,
			"member_id": self.member_id,
			"membership_type": self.membership_type,
			"status": self.status,
			"current_books_issued": self.current_books_issued,
			"max_books_allowed": self.max_books_allowed,
			"total_fines": self.total_fines,
			"expiry_date": self.expiry_date,
			"can_issue_book": self.can_issue_book()[0]
		}

