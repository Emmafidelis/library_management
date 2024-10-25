# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Member(Document):
	def validate_coupon(member):
		valid_coupons = ["WELCOME50", "LIBRARY2024", "READINGFUN"]
		if member.coupon_code not in valid_coupons:
			frappe.throw("Invalid Coupon Code")

