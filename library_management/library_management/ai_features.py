# Copyright (c) 2024, Emanuel Fidelis and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, flt, cint
import json
import math
from collections import defaultdict, Counter
import re


def find_similar_members(member_name, reading_history):
	"""Find members with similar reading patterns using collaborative filtering"""
	try:
		# Get reading history of all members
		all_reading_history = frappe.db.sql("""
			SELECT member, book, COUNT(*) as frequency
			FROM `tabLibrary Transaction`
			WHERE transaction_type = 'Issue'
			AND member != %s
			GROUP BY member, book
		""", [member_name], as_dict=True)
		
		# Create member-book matrix
		member_books = defaultdict(set)
		for record in all_reading_history:
			member_books[record.member].add(record.book)
		
		# Current member's books
		current_books = set([r.book for r in reading_history])
		
		# Calculate similarity scores using Jaccard similarity
		similarities = []
		for other_member, other_books in member_books.items():
			if len(other_books) < 3:  # Skip members with too few books
				continue
			
			intersection = len(current_books.intersection(other_books))
			union = len(current_books.union(other_books))
			
			if union > 0:
				similarity = intersection / union
				if similarity > 0.1:  # Only consider members with some similarity
					similarities.append({
						"member": other_member,
						"similarity": similarity,
						"common_books": intersection,
						"total_books": len(other_books)
					})
		
		# Sort by similarity and return top matches
		similarities.sort(key=lambda x: x["similarity"], reverse=True)
		return similarities[:10]
		
	except Exception as e:
		frappe.log_error(f"Error finding similar members: {str(e)}")
		return []


def collaborative_filtering(member_name, similar_members):
	"""Generate book recommendations using collaborative filtering"""
	try:
		if not similar_members:
			return []
		
		# Get books read by current member
		current_books = frappe.db.sql("""
			SELECT DISTINCT book
			FROM `tabLibrary Transaction`
			WHERE member = %s AND transaction_type = 'Issue'
		""", [member_name], pluck=True)
		
		current_books_set = set(current_books)
		
		# Get books read by similar members
		similar_member_names = [m["member"] for m in similar_members[:5]]
		
		recommended_books = frappe.db.sql("""
			SELECT book, COUNT(*) as frequency, AVG(rating) as avg_rating
			FROM `tabLibrary Transaction` lt
			LEFT JOIN `tabBook Review` br ON lt.book = br.book
			WHERE lt.member IN ({})
			AND lt.transaction_type = 'Issue'
			AND lt.book NOT IN ({})
			GROUP BY book
			ORDER BY frequency DESC, avg_rating DESC
			LIMIT 20
		""".format(
			",".join(["%s"] * len(similar_member_names)),
			",".join(["%s"] * len(current_books)) if current_books else "''"
		), similar_member_names + current_books, as_dict=True)
		
		# Calculate recommendation scores
		recommendations = []
		for book_data in recommended_books:
			book = frappe.get_doc("Book", book_data.book)
			
			# Calculate score based on frequency and similarity of recommenders
			score = 0
			for member in similar_members:
				if member["member"] in similar_member_names:
					# Check if this member read this book
					read_book = frappe.db.exists("Library Transaction", {
						"member": member["member"],
						"book": book_data.book,
						"transaction_type": "Issue"
					})
					if read_book:
						score += member["similarity"] * 100
			
			if score > 0:
				recommendations.append({
					"book": book_data.book,
					"score": score,
					"reason": f"Recommended by {book_data.frequency} similar readers",
					"title": book.title,
					"author": book.author,
					"category": book.category
				})
		
		return sorted(recommendations, key=lambda x: x["score"], reverse=True)
		
	except Exception as e:
		frappe.log_error(f"Error in collaborative filtering: {str(e)}")
		return []


def content_based_filtering(genres, authors):
	"""Generate book recommendations using content-based filtering"""
	try:
		recommendations = []
		
		# Get top genres and authors
		top_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)[:3]
		top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:3]
		
		# Find books by favorite authors
		for author, count in top_authors:
			author_books = frappe.get_all(
				"Book",
				filters={"author": author, "available_copies": [">", 0]},
				fields=["name", "title", "author", "category", "average_rating"],
				limit=5
			)
			
			for book in author_books:
				recommendations.append({
					"book": book.name,
					"score": count * 20 + (book.average_rating or 0) * 10,
					"reason": f"By your favorite author: {author}",
					"title": book.title,
					"author": book.author,
					"category": book.category
				})
		
		# Find books in favorite genres
		for genre, count in top_genres:
			genre_books = frappe.get_all(
				"Book",
				filters={"category": genre, "available_copies": [">", 0]},
				fields=["name", "title", "author", "category", "average_rating"],
				limit=5,
				order_by="average_rating desc"
			)
			
			for book in genre_books:
				# Check if already recommended
				if not any(r["book"] == book.name for r in recommendations):
					recommendations.append({
						"book": book.name,
						"score": count * 15 + (book.average_rating or 0) * 10,
						"reason": f"In your favorite genre: {genre}",
						"title": book.title,
						"author": book.author,
						"category": book.category
					})
		
		return sorted(recommendations, key=lambda x: x["score"], reverse=True)
		
	except Exception as e:
		frappe.log_error(f"Error in content-based filtering: {str(e)}")
		return []


def merge_recommendations(collab_books, content_books):
	"""Merge collaborative and content-based recommendations"""
	try:
		merged = {}
		
		# Add collaborative filtering results with higher weight
		for book in collab_books:
			merged[book["book"]] = {
				**book,
				"score": book["score"] * 1.5,  # Higher weight for collaborative
				"reason": f"Collaborative: {book['reason']}"
			}
		
		# Add content-based results
		for book in content_books:
			if book["book"] in merged:
				# Combine scores if book appears in both
				merged[book["book"]]["score"] += book["score"]
				merged[book["book"]]["reason"] += f" + Content: {book['reason']}"
			else:
				merged[book["book"]] = book
		
		return sorted(merged.values(), key=lambda x: x["score"], reverse=True)
		
	except Exception as e:
		frappe.log_error(f"Error merging recommendations: {str(e)}")
		return []


def calculate_confidence_score(recommended_books):
	"""Calculate confidence score for recommendations"""
	try:
		if not recommended_books:
			return 0
		
		# Base confidence on number of recommendations and score distribution
		num_books = len(recommended_books)
		avg_score = sum([book["score"] for book in recommended_books]) / num_books
		
		# Normalize to percentage
		confidence = min(100, (avg_score / 100) * 100)
		
		# Boost confidence if we have many recommendations
		if num_books >= 10:
			confidence = min(100, confidence * 1.2)
		
		return round(confidence, 2)
		
	except Exception as e:
		frappe.log_error(f"Error calculating confidence score: {str(e)}")
		return 0


def generate_recommendation_reason(genres, authors, algorithm):
	"""Generate human-readable reason for recommendations"""
	try:
		top_genre = max(genres.items(), key=lambda x: x[1])[0] if genres else "various genres"
		top_author = max(authors.items(), key=lambda x: x[1])[0] if authors else "various authors"
		
		reasons = {
			"collaborative": f"Based on readers with similar tastes who enjoy {top_genre} books",
			"content_based": f"Based on your preference for {top_genre} and books by {top_author}",
			"hybrid": f"Based on your reading history ({top_genre}, {top_author}) and similar readers' preferences"
		}
		
		return reasons.get(algorithm.lower(), "Based on your reading patterns and preferences")
		
	except Exception as e:
		frappe.log_error(f"Error generating recommendation reason: {str(e)}")
		return "Based on your reading patterns"


def analyze_reading_patterns(member_name):
	"""Analyze member's reading patterns using AI"""
	try:
		# Get comprehensive reading history
		transactions = frappe.db.sql("""
			SELECT 
				lt.book, lt.transaction_date, lt.return_date,
				b.title, b.author, b.category, b.pages, b.language,
				DATEDIFF(lt.return_date, lt.transaction_date) as reading_days
			FROM `tabLibrary Transaction` lt
			JOIN `tabBook` b ON lt.book = b.name
			WHERE lt.member = %s 
			AND lt.transaction_type = 'Issue'
			AND lt.return_date IS NOT NULL
			ORDER BY lt.transaction_date DESC
		""", [member_name], as_dict=True)
		
		if not transactions:
			return {"error": "No reading history found"}
		
		# Analyze patterns
		analysis = {
			"total_books": len(transactions),
			"reading_frequency": calculate_reading_frequency(transactions),
			"genre_distribution": analyze_genre_preferences(transactions),
			"reading_speed": calculate_reading_speed(transactions),
			"complexity_preference": analyze_complexity_preference(transactions),
			"seasonal_patterns": analyze_seasonal_patterns(transactions),
			"author_loyalty": analyze_author_loyalty(transactions),
			"language_preferences": analyze_language_preferences(transactions)
		}
		
		return analysis
		
	except Exception as e:
		frappe.log_error(f"Error analyzing reading patterns: {str(e)}")
		return {"error": "Failed to analyze reading patterns"}


def calculate_reading_frequency(transactions):
	"""Calculate how often the member reads"""
	try:
		if len(transactions) < 2:
			return "Insufficient data"
		
		# Calculate days between transactions
		intervals = []
		for i in range(1, len(transactions)):
			current_date = frappe.utils.getdate(transactions[i-1]["transaction_date"])
			previous_date = frappe.utils.getdate(transactions[i]["transaction_date"])
			interval = (current_date - previous_date).days
			if interval > 0:
				intervals.append(interval)
		
		if not intervals:
			return "Irregular"
		
		avg_interval = sum(intervals) / len(intervals)
		
		if avg_interval <= 7:
			return "Very Active (Weekly)"
		elif avg_interval <= 14:
			return "Active (Bi-weekly)"
		elif avg_interval <= 30:
			return "Regular (Monthly)"
		else:
			return "Occasional"
			
	except Exception as e:
		return "Unknown"


def analyze_genre_preferences(transactions):
	"""Analyze genre reading preferences"""
	try:
		genres = Counter([t["category"] for t in transactions if t["category"]])
		total = len(transactions)
		
		preferences = {}
		for genre, count in genres.most_common():
			preferences[genre] = {
				"count": count,
				"percentage": round((count / total) * 100, 1)
			}
		
		return preferences
		
	except Exception as e:
		return {}


def calculate_reading_speed(transactions):
	"""Calculate average reading speed"""
	try:
		valid_readings = [t for t in transactions if t["reading_days"] and t["pages"] and t["reading_days"] > 0]
		
		if not valid_readings:
			return "Unknown"
		
		speeds = []
		for t in valid_readings:
			pages_per_day = t["pages"] / t["reading_days"]
			speeds.append(pages_per_day)
		
		avg_speed = sum(speeds) / len(speeds)
		
		if avg_speed >= 50:
			return "Fast Reader"
		elif avg_speed >= 25:
			return "Average Reader"
		else:
			return "Slow Reader"
			
	except Exception as e:
		return "Unknown"


def analyze_complexity_preference(transactions):
	"""Analyze preference for book complexity"""
	try:
		# This would ideally use NLP to analyze book complexity
		# For now, use category as a proxy
		complex_categories = ["Science", "Technology", "Academic", "Research", "Philosophy"]
		moderate_categories = ["History", "Biography", "Non-Fiction"]
		
		complex_count = sum(1 for t in transactions if t["category"] in complex_categories)
		moderate_count = sum(1 for t in transactions if t["category"] in moderate_categories)
		light_count = len(transactions) - complex_count - moderate_count
		
		total = len(transactions)
		if complex_count / total > 0.5:
			return "Prefers Complex Content"
		elif moderate_count / total > 0.5:
			return "Prefers Moderate Content"
		else:
			return "Prefers Light Reading"
			
	except Exception as e:
		return "Unknown"


def analyze_seasonal_patterns(transactions):
	"""Analyze seasonal reading patterns"""
	try:
		seasons = {"Spring": 0, "Summer": 0, "Fall": 0, "Winter": 0}
		
		for t in transactions:
			month = frappe.utils.getdate(t["transaction_date"]).month
			if month in [3, 4, 5]:
				seasons["Spring"] += 1
			elif month in [6, 7, 8]:
				seasons["Summer"] += 1
			elif month in [9, 10, 11]:
				seasons["Fall"] += 1
			else:
				seasons["Winter"] += 1
		
		return seasons
		
	except Exception as e:
		return {}


def analyze_author_loyalty(transactions):
	"""Analyze loyalty to specific authors"""
	try:
		authors = Counter([t["author"] for t in transactions if t["author"]])
		total = len(transactions)
		
		# Find authors with multiple books
		loyal_authors = {author: count for author, count in authors.items() if count > 1}
		
		loyalty_score = sum(loyal_authors.values()) / total if total > 0 else 0
		
		return {
			"loyalty_score": round(loyalty_score * 100, 1),
			"favorite_authors": dict(authors.most_common(5)),
			"repeat_authors": len(loyal_authors)
		}
		
	except Exception as e:
		return {}


def analyze_language_preferences(transactions):
	"""Analyze language reading preferences"""
	try:
		languages = Counter([t["language"] for t in transactions if t["language"]])
		total = len(transactions)
		
		preferences = {}
		for language, count in languages.items():
			preferences[language] = {
				"count": count,
				"percentage": round((count / total) * 100, 1)
			}
		
		return preferences
		
	except Exception as e:
		return {}


def get_space_sensor_data(space_name):
	"""Get real-time sensor data for smart spaces (simulated)"""
	try:
		# In a real implementation, this would connect to IoT sensors
		# For now, return simulated data
		import random
		
		return {
			"temperature": round(random.uniform(20, 26), 1),
			"humidity": round(random.uniform(40, 60), 1),
			"noise_level": round(random.uniform(30, 50), 1),
			"air_quality": random.choice(["Good", "Moderate", "Poor"]),
			"lighting_level": round(random.uniform(300, 800), 0),
			"occupancy_detected": random.choice([True, False]),
			"last_updated": frappe.utils.now_datetime()
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting sensor data: {str(e)}")
		return {}


def generate_ai_discussion_prompts(book_name, reading_progress=None):
	"""Generate AI-powered discussion prompts for reading circles"""
	try:
		book = frappe.get_doc("Book", book_name)
		
		# Basic prompts based on book metadata
		prompts = [
			f"What themes in '{book.title}' resonate most with current events?",
			f"How does {book.author}'s writing style contribute to the story's impact?",
			f"What character development surprised you the most and why?",
			f"How does this book compare to other works in the {book.category} genre?",
			f"What questions would you ask {book.author} if you could meet them?"
		]
		
		# Add progress-specific prompts if available
		if reading_progress:
			if reading_progress < 0.3:
				prompts.extend([
					"What are your first impressions of the main characters?",
					"How effective is the opening in drawing you into the story?"
				])
			elif reading_progress < 0.7:
				prompts.extend([
					"What plot developments have surprised you so far?",
					"How are the conflicts developing in the story?"
				])
			else:
				prompts.extend([
					"How satisfying was the resolution of the main conflict?",
					"What will you remember most about this book?"
				])
		
		return prompts
		
	except Exception as e:
		frappe.log_error(f"Error generating discussion prompts: {str(e)}")
		return ["What did you think of this book?"]
