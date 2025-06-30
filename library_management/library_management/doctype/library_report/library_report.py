# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, now_datetime, getdate, add_days, date_diff
from frappe import _
import json
import pandas as pd
from io import BytesIO
import base64


class LibraryReport(Document):
	def validate(self):
		self.validate_dates()
		
	def before_save(self):
		if not self.generated_by:
			self.generated_by = frappe.session.user
			
	def validate_dates(self):
		"""Validate date range"""
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be greater than To Date"))
			
	def generate_report(self):
		"""Generate the report based on type and filters"""
		try:
			self.status = "Generating"
			self.generated_on = now_datetime()
			self.save()
			
			# Generate report based on type
			if self.report_type == "Circulation Report":
				data = self.generate_circulation_report()
			elif self.report_type == "Member Activity Report":
				data = self.generate_member_activity_report()
			elif self.report_type == "Fine Collection Report":
				data = self.generate_fine_collection_report()
			elif self.report_type == "Inventory Report":
				data = self.generate_inventory_report()
			elif self.report_type == "Overdue Books Report":
				data = self.generate_overdue_report()
			elif self.report_type == "Popular Books Report":
				data = self.generate_popular_books_report()
			elif self.report_type == "Membership Statistics":
				data = self.generate_membership_statistics()
			elif self.report_type == "Monthly Summary":
				data = self.generate_monthly_summary()
			else:
				frappe.throw(_("Report type not implemented"))
				
			# Store summary data
			self.summary_data = json.dumps(data.get('summary', {}))
			self.total_records = len(data.get('records', []))
			
			# Generate file
			file_content = self.create_report_file(data)
			self.attach_report_file(file_content)
			
			self.status = "Completed"
			self.save()
			
			return data
			
		except Exception as e:
			self.status = "Failed"
			self.notes = str(e)
			self.save()
			frappe.log_error(f"Error generating report: {str(e)}", "Library Report Generation")
			raise
			
	def generate_circulation_report(self):
		"""Generate circulation report"""
		filters = {
			"transaction_date": ["between", [self.from_date, self.to_date]]
		}
		
		if self.member_type_filter and self.member_type_filter != "All":
			# Get members of specific type
			members = frappe.get_all("Member", 
				filters={"membership_type": self.member_type_filter},
				pluck="name"
			)
			filters["member"] = ["in", members]
			
		transactions = frappe.get_all(
			"Library Transaction",
			filters=filters,
			fields=[
				"name", "transaction_type", "member", "book", 
				"transaction_date", "due_date", "return_date", "status"
			]
		)
		
		# Add member and book details
		for txn in transactions:
			member = frappe.get_doc("Member", txn.member)
			book = frappe.get_doc("Book", txn.book)
			txn.update({
				"member_name": member.member_name,
				"member_type": member.membership_type,
				"book_title": book.title,
				"book_author": book.author,
				"book_category": book.category
			})
			
		# Calculate summary
		summary = {
			"total_transactions": len(transactions),
			"issues": len([t for t in transactions if t.transaction_type == "Issue"]),
			"returns": len([t for t in transactions if t.transaction_type == "Return"]),
			"renewals": len([t for t in transactions if t.transaction_type == "Renewal"]),
			"overdue": len([t for t in transactions if t.status == "Overdue"])
		}
		
		return {"records": transactions, "summary": summary}
		
	def generate_member_activity_report(self):
		"""Generate member activity report"""
		# Get all members based on filter
		member_filters = {}
		if self.member_type_filter and self.member_type_filter != "All":
			member_filters["membership_type"] = self.member_type_filter
			
		members = frappe.get_all("Member", filters=member_filters, fields=[
			"name", "member_name", "member_id", "membership_type", 
			"current_books_issued", "total_fines"
		])
		
		# Get transaction counts for each member
		for member in members:
			transactions = frappe.get_all(
				"Library Transaction",
				filters={
					"member": member.name,
					"transaction_date": ["between", [self.from_date, self.to_date]]
				},
				fields=["transaction_type"]
			)
			
			member.update({
				"total_transactions": len(transactions),
				"books_issued": len([t for t in transactions if t.transaction_type == "Issue"]),
				"books_returned": len([t for t in transactions if t.transaction_type == "Return"]),
				"renewals": len([t for t in transactions if t.transaction_type == "Renewal"])
			})
			
		# Calculate summary
		summary = {
			"total_members": len(members),
			"active_members": len([m for m in members if m.total_transactions > 0]),
			"total_books_issued": sum([m.books_issued for m in members]),
			"average_books_per_member": round(sum([m.books_issued for m in members]) / len(members), 2) if members else 0
		}
		
		return {"records": members, "summary": summary}
		
	def generate_fine_collection_report(self):
		"""Generate fine collection report"""
		fines = frappe.get_all(
			"Library Fine",
			filters={
				"fine_date": ["between", [self.from_date, self.to_date]]
			},
			fields=[
				"name", "member", "book", "fine_type", "fine_amount",
				"paid_amount", "outstanding_amount", "status", "fine_date"
			]
		)
		
		# Add member details
		for fine in fines:
			member = frappe.get_doc("Member", fine.member)
			fine.update({
				"member_name": member.member_name,
				"member_type": member.membership_type
			})
			
		# Calculate summary
		summary = {
			"total_fines": len(fines),
			"total_fine_amount": sum([f.fine_amount for f in fines]),
			"total_paid": sum([f.paid_amount for f in fines]),
			"total_outstanding": sum([f.outstanding_amount for f in fines]),
			"collection_rate": round((sum([f.paid_amount for f in fines]) / sum([f.fine_amount for f in fines])) * 100, 2) if fines else 0
		}
		
		return {"records": fines, "summary": summary}
		
	def generate_inventory_report(self):
		"""Generate inventory report"""
		filters = {}
		if self.category_filter and self.category_filter != "All":
			filters["category"] = self.category_filter
			
		books = frappe.get_all(
			"Book",
			filters=filters,
			fields=[
				"name", "title", "author", "category", "isbn", "total_copies",
				"available_copies", "issued_copies", "damaged_copies", "status"
			]
		)
		
		# Calculate utilization rate for each book
		for book in books:
			if book.total_copies > 0:
				book["utilization_rate"] = round((book.issued_copies / book.total_copies) * 100, 2)
			else:
				book["utilization_rate"] = 0
				
		# Calculate summary
		summary = {
			"total_books": len(books),
			"total_copies": sum([b.total_copies for b in books]),
			"available_copies": sum([b.available_copies for b in books]),
			"issued_copies": sum([b.issued_copies for b in books]),
			"damaged_copies": sum([b.damaged_copies for b in books]),
			"average_utilization": round(sum([b.utilization_rate for b in books]) / len(books), 2) if books else 0
		}
		
		return {"records": books, "summary": summary}
		
	def generate_overdue_report(self):
		"""Generate overdue books report"""
		overdue_transactions = frappe.get_all(
			"Library Transaction",
			filters={
				"transaction_type": "Issue",
				"status": "Overdue",
				"due_date": ["<=", self.to_date]
			},
			fields=[
				"name", "member", "book", "transaction_date", 
				"due_date", "status"
			]
		)
		
		# Add member and book details, calculate overdue days
		for txn in overdue_transactions:
			member = frappe.get_doc("Member", txn.member)
			book = frappe.get_doc("Book", txn.book)
			
			overdue_days = date_diff(self.to_date, txn.due_date)
			
			txn.update({
				"member_name": member.member_name,
				"member_type": member.membership_type,
				"member_email": member.email,
				"book_title": book.title,
				"book_author": book.author,
				"overdue_days": overdue_days
			})
			
		# Calculate summary
		summary = {
			"total_overdue": len(overdue_transactions),
			"average_overdue_days": round(sum([t.overdue_days for t in overdue_transactions]) / len(overdue_transactions), 2) if overdue_transactions else 0,
			"max_overdue_days": max([t.overdue_days for t in overdue_transactions]) if overdue_transactions else 0
		}
		
		return {"records": overdue_transactions, "summary": summary}
		
	def generate_popular_books_report(self):
		"""Generate popular books report"""
		# Get books with issue count
		popular_books = frappe.db.sql("""
			SELECT 
				b.name, b.title, b.author, b.category,
				COUNT(t.name) as issue_count,
				b.total_copies,
				ROUND((COUNT(t.name) / b.total_copies), 2) as popularity_ratio
			FROM `tabBook` b
			LEFT JOIN `tabLibrary Transaction` t ON b.name = t.book 
				AND t.transaction_type = 'Issue'
				AND t.transaction_date BETWEEN %s AND %s
			WHERE b.status != 'Discarded'
			GROUP BY b.name
			ORDER BY issue_count DESC
			LIMIT 50
		""", [self.from_date, self.to_date], as_dict=True)
		
		# Calculate summary
		summary = {
			"total_books_analyzed": len(popular_books),
			"most_popular_book": popular_books[0].title if popular_books else "None",
			"highest_issue_count": popular_books[0].issue_count if popular_books else 0,
			"average_issues_per_book": round(sum([b.issue_count for b in popular_books]) / len(popular_books), 2) if popular_books else 0
		}
		
		return {"records": popular_books, "summary": summary}
		
	def generate_membership_statistics(self):
		"""Generate membership statistics"""
		# Get membership data by type
		membership_stats = frappe.db.sql("""
			SELECT 
				membership_type,
				COUNT(*) as total_members,
				SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_members,
				SUM(current_books_issued) as total_books_issued,
				SUM(total_fines) as total_outstanding_fines
			FROM `tabMember`
			GROUP BY membership_type
		""", as_dict=True)
		
		# Calculate summary
		total_members = sum([s.total_members for s in membership_stats])
		total_active = sum([s.active_members for s in membership_stats])
		
		summary = {
			"total_members": total_members,
			"active_members": total_active,
			"activation_rate": round((total_active / total_members) * 100, 2) if total_members else 0,
			"total_books_in_circulation": sum([s.total_books_issued for s in membership_stats]),
			"total_outstanding_fines": sum([s.total_outstanding_fines for s in membership_stats])
		}
		
		return {"records": membership_stats, "summary": summary}
		
	def generate_monthly_summary(self):
		"""Generate monthly summary report"""
		# This would be a comprehensive monthly report
		# combining multiple metrics
		
		# Get basic statistics
		total_books = frappe.db.count("Book")
		total_members = frappe.db.count("Member", {"status": "Active"})
		
		# Get monthly transactions
		monthly_transactions = frappe.get_all(
			"Library Transaction",
			filters={
				"transaction_date": ["between", [self.from_date, self.to_date]]
			},
			fields=["transaction_type"]
		)
		
		# Get monthly fines
		monthly_fines = frappe.get_all(
			"Library Fine",
			filters={
				"fine_date": ["between", [self.from_date, self.to_date]]
			},
			fields=["fine_amount", "paid_amount"]
		)
		
		summary = {
			"period": f"{self.from_date} to {self.to_date}",
			"total_books": total_books,
			"total_members": total_members,
			"monthly_issues": len([t for t in monthly_transactions if t.transaction_type == "Issue"]),
			"monthly_returns": len([t for t in monthly_transactions if t.transaction_type == "Return"]),
			"monthly_fine_amount": sum([f.fine_amount for f in monthly_fines]),
			"monthly_fine_collected": sum([f.paid_amount for f in monthly_fines])
		}
		
		return {"records": [summary], "summary": summary}
		
	def create_report_file(self, data):
		"""Create report file in specified format"""
		if self.export_format == "Excel":
			return self.create_excel_file(data)
		elif self.export_format == "CSV":
			return self.create_csv_file(data)
		elif self.export_format == "PDF":
			return self.create_pdf_file(data)
		else:
			return self.create_html_file(data)
			
	def create_excel_file(self, data):
		"""Create Excel file"""
		output = BytesIO()
		
		with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
			# Write records
			if data.get('records'):
				df = pd.DataFrame(data['records'])
				df.to_excel(writer, sheet_name='Data', index=False)
				
			# Write summary
			if data.get('summary'):
				summary_df = pd.DataFrame([data['summary']])
				summary_df.to_excel(writer, sheet_name='Summary', index=False)
				
		return output.getvalue()
		
	def create_csv_file(self, data):
		"""Create CSV file"""
		if data.get('records'):
			df = pd.DataFrame(data['records'])
			return df.to_csv(index=False).encode('utf-8')
		return b""
		
	def create_pdf_file(self, data):
		"""Create PDF file - placeholder for now"""
		# This would use a PDF library like reportlab
		return b"PDF generation not implemented yet"
		
	def create_html_file(self, data):
		"""Create HTML file"""
		html_content = f"""
		<html>
		<head>
			<title>{self.report_name}</title>
			<style>
				body {{ font-family: Arial, sans-serif; }}
				table {{ border-collapse: collapse; width: 100%; }}
				th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
				th {{ background-color: #f2f2f2; }}
			</style>
		</head>
		<body>
			<h1>{self.report_name}</h1>
			<p>Generated on: {self.generated_on}</p>
			<p>Period: {self.from_date} to {self.to_date}</p>
			
			<h2>Summary</h2>
			<table>
		"""
		
		# Add summary data
		if data.get('summary'):
			for key, value in data['summary'].items():
				html_content += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
				
		html_content += "</table></body></html>"
		return html_content.encode('utf-8')
		
	def attach_report_file(self, file_content):
		"""Attach generated file to the document"""
		file_name = f"{self.report_name}_{self.from_date}_{self.to_date}.{self.export_format.lower()}"
		
		# Create file attachment
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": file_name,
			"content": base64.b64encode(file_content).decode(),
			"decode": True,
			"attached_to_doctype": "Library Report",
			"attached_to_name": self.name
		})
		file_doc.insert()
		
		self.file_attachment = file_doc.file_url
