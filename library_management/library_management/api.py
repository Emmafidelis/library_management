# library_management_system/library_management_system/api.py

import frappe
from frappe import _
import random
import string
from frappe.utils import now
import math
import uuid

@frappe.whitelist(allow_guest=True)
def get_books(search=None, category=None, page=1, page_size=10):
  try:
    filters = {} 
    if search:
      filters["title"] = ["like", f"%{search}%"]
    if category:
      filters["category"] = category

    offset = (int(page) - 1) * int(page_size)
    books = frappe.get_all(
      "Book",
      filters=filters,
      fields=["name", "title", "author", "category"],
      limit_start=offset,
      limit_page_length=int(page_size),
    )

    if not books:
      return {"message": "No books found matching your criteria."}

    total_books = frappe.db.count("Book", filters=filters)
    return {
      "books": books,
      "total_books": total_books,
      "page": int(page),
      "page_size": int(page_size),
      "total_pages": (total_books + int(page_size) - 1) // int(page_size),
    }

  except Exception as e:
    frappe.log_error(f"Error fetching books: {str(e)}")
    return {"error": "An error occurred while fetching books."}


@frappe.whitelist(allow_guest=True)
def login(username, password):
  try:
    frappe.auth.LoginManager().authenticate(username, password)
    frappe.auth.LoginManager().post_login()
    return {"message": "Logged In"}
  except frappe.exceptions.AuthenticationError:
    return {"message": "Invalid username or password"}


@frappe.whitelist(allow_guest=True)
def borrow_book(book_id, member_id):
    """
    Borrow a book and generate a coupon code for the user.
    """
    try:
      book = frappe.get_doc("Book", book_id)
      if not book:
        return {"message": "The requested book does not exist."}

      coupon_code = str(uuid.uuid4()).split('-')[0]

      borrowed_book = frappe.get_doc({
        "doctype": "Borrowed Book",
        "book": book_id,
        "member": member_id,
        "coupon_code": coupon_code,
        "borrow_date": frappe.utils.nowdate(),
      })
      borrowed_book.insert()
      frappe.db.commit()

      return {"message": "Book borrowed successfully!", "coupon_code": coupon_code}

    except frappe.DoesNotExistError:
      return {"message": "The specified book or member does not exist."}
    except Exception as e:
      frappe.log_error(f"Error borrowing book: {str(e)}")
      return {"error": "An error occurred while borrowing the book."}

