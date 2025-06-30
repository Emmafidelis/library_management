# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from frappe import _


class LibraryFine(Document):
	def validate(self):
		self.calculate_outstanding_amount()
		self.update_status()
		
	def calculate_outstanding_amount(self):
		"""Calculate outstanding amount"""
		self.outstanding_amount = flt(self.fine_amount) - flt(self.paid_amount)
		
	def update_status(self):
		"""Update status based on payment"""
		if self.waived:
			self.status = "Waived"
		elif flt(self.paid_amount) >= flt(self.fine_amount):
			self.status = "Paid"
		elif flt(self.paid_amount) > 0:
			self.status = "Partially Paid"
		else:
			self.status = "Unpaid"
			
	def make_payment(self, amount, payment_method=None, payment_reference=None):
		"""Record payment for the fine"""
		if flt(amount) <= 0:
			frappe.throw(_("Payment amount must be greater than 0"))
			
		if flt(self.paid_amount) + flt(amount) > flt(self.fine_amount):
			frappe.throw(_("Payment amount cannot exceed fine amount"))
			
		self.paid_amount = flt(self.paid_amount) + flt(amount)
		self.payment_date = nowdate()
		
		if payment_method:
			self.payment_method = payment_method
			
		if payment_reference:
			self.payment_reference = payment_reference
			
		self.save()
		
		# Create payment entry if ERPNext integration is enabled
		self.create_payment_entry(amount)
		
		return self
		
	def waive_fine(self, reason=None):
		"""Waive the fine"""
		self.waived = 1
		self.waived_by = frappe.session.user
		self.waived_date = nowdate()
		
		if reason:
			self.waived_reason = reason
			
		self.save()
		
		return self
		
	def create_payment_entry(self, amount):
		"""Create payment entry for ERPNext integration"""
		# This would integrate with ERPNext's Payment Entry
		# For now, we'll create a simple log
		frappe.log_error(
			f"Fine payment of {amount} recorded for member {self.member}",
			"Library Fine Payment"
		)
