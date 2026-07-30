"""
Pulls products/variants from Shopify and keeps them mirrored into the
"Shopify Product Mapping" doctype (one row per variant).

Safe to run repeatedly: existing rows (matched by store + variant id) are
updated in place rather than duplicated, and a manual ERPNext Item mapping
that's already been set is never overwritten by a re-fetch.
"""

import re
import requests
import frappe
from frappe.utils import now_datetime

from ss_frappe_shopify_connector.api import get_access_token

SHOPIFY_API_VERSION = "2024-10"
PAGE_LIMIT = 250


def fetch_products(store_url: str) -> dict:
	"""Fetch all products from Shopify and upsert Shopify Product Mapping rows.

	Returns a summary dict: {"created": n, "updated": n, "auto_matched": n}
	"""

	access_token = get_access_token(store_url)
	summary = {"created": 0, "updated": 0, "auto_matched": 0}

	url = (
		f"https://{store_url}/admin/api/{SHOPIFY_API_VERSION}/products.json"
		f"?limit={PAGE_LIMIT}"
	)
	headers = {"X-Shopify-Access-Token": access_token}

	try:
		while url:
			response = requests.get(url, headers=headers, timeout=30)
			response.raise_for_status()
			products = response.json().get("products", [])

			for product in products:
				_upsert_variants(store_url, product, summary)

			url = _get_next_page_url(response)

		frappe.db.commit()
		_log(store_url, "Success", f"Fetched products. {summary}")

	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Shopify Fetch Products Failed", message=frappe.get_traceback())
		_log(store_url, "Failed", frappe.get_traceback())
		frappe.throw("Failed to fetch products from Shopify. Check Shopify Logs for details.")

	return summary


def _get_next_page_url(response) -> str | None:
	"""Shopify paginates via the Link header (cursor-based), e.g.:
	<https://store.myshopify.com/admin/api/.../products.json?page_info=xyz>; rel="next"
	"""
	link_header = response.headers.get("Link", "")
	match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
	return match.group(1) if match else None


def _upsert_variants(store_url: str, product: dict, summary: dict):
	product_id = str(product.get("id"))
	product_title = product.get("title") or ""

	for variant in product.get("variants", []):
		variant_id = str(variant.get("id"))
		variant_title = variant.get("title") or ""
		if variant_title == "Default Title":
			variant_title = ""
		sku = (variant.get("sku") or "").strip()

		row_name = f"{store_url}-{variant_id}"

		if frappe.db.exists("Shopify Product Mapping", row_name):
			doc = frappe.get_doc("Shopify Product Mapping", row_name)
			doc.shopify_product_name = product_title
			doc.shopify_variant_title = variant_title
			doc.shopify_sku = sku
			doc.last_synced_on = now_datetime()
			doc.save(ignore_permissions=True)
			summary["updated"] += 1
		else:
			doc = frappe.new_doc("Shopify Product Mapping")
			doc.shopify_store = store_url
			doc.shopify_product_id = product_id
			doc.shopify_variant_id = variant_id
			doc.shopify_product_name = product_title
			doc.shopify_variant_title = variant_title
			doc.shopify_sku = sku
			doc.last_synced_on = now_datetime()

			matched_item = _auto_match_by_sku(sku)
			if matched_item:
				doc.erpnext_item_code = matched_item
				doc.mapping_status = "Auto-Matched (Review)"
				summary["auto_matched"] += 1

			doc.insert(ignore_permissions=True)
			summary["created"] += 1


def _auto_match_by_sku(sku: str) -> str | None:
	"""Best-effort match: Shopify variant SKU == ERPNext Item Code.
	Only ever suggests a match - never marks it fully "Mapped" on its own,
	so a human still reviews/saves it before it's trusted for order sync.
	"""
	if not sku:
		return None

	if frappe.db.exists("Item", sku):
		return sku

	return None


def _log(store, status, message):
	frappe.get_doc({
		"doctype": "Shopify Logs",
		"store": store,
		"timestamp": now_datetime(),
		"status": status,
		"message": message[:1000] if message else message,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
