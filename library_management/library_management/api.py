# library_management_system/library_management_system/api.py

import frappe
from frappe import _
import math

@frappe.whitelist(allow_guest=True)
def get_books(search=None, category=None, page=1, page_size=10):
  try:
    page = int(page)
    page_size = int(page_size)
    offset = (page - 1) * page_size

    filters = {}
    if search:
      filters["title"] = ["like", f"%{search}%"]
    if category:
      filters["category"] = category

    books = frappe.get_all("Book", fields=["title", "author", "category"], filters=filters, limit_start=offset, limit_page_length=page_size)

    if not books:
      return {
        "books": [],
        "message": "The book you're searching for is not available.",
        "total_pages": 0,
        "current_page": page
      }

    total_books = frappe.db.count("Book", filters=filters)
    total_pages = math.ceil(total_books / page_size)

    return {
      "books": books,
      "total_pages": total_pages,
      "current_page": page
    }
    
  except Exception as e:
    frappe.log_error(message=str(e), title="get_books API Error")
    return {
      "error": "An error occurred while fetching books."
    }


@frappe.whitelist(allow_guest=True)
def login(username, password):
  member = frappe.db.get_value("Member", {"username": username}, ["name", "password"])

  if member:
    member_name, stored_password = member
    if stored_password == password:
      return {"status": "success", "message": _("Login successful"), "member_name": member_name}
    else:
      return {"status": "failed", "message": _("Incorrect password")}
  else:
    return {"status": "failed", "message": _("User not found")}

