import frappe
import math

@frappe.whitelist(allow_guest=True)
def get_books(search=None, category=None, page=1, page_size=10):
  page = int(page)
  page_size = int(page_size)
  offset = (page - 1) * page_size

  filters = {}
  if search:
    filters["title"] = ["like", f"%{search}%"]
  if category:
    filters["category"] = category

  books = frappe.get_all("Book", fields=["title", "author", "category"],
  filters=filters, limit_start=offset, limit_page_length=page_size)

  total_books = frappe.db.count("Book", filters=filters)
  total_pages = math.ceil(total_books / page_size)

  return {
    "books": books,
    "total_pages": total_pages,
    "current_page": page
  }
