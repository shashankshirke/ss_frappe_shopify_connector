"""
Receives Shopify's "Order creation" webhook and turns it into a draft
ERPNext Sales Order.

Design decisions (documented here on purpose, since they affect behaviour):

* Every line item must already have a "Mapped" (or reviewed) row in
  Shopify Product Mapping. If even one line item on the order can't be
  resolved to an ERPNext Item, the WHOLE order is rejected - nothing
  partial is created - and it's logged in Shopify Order Log for you to
  fix the mapping and reprocess manually.
* The Sales Order is created but left as a draft (docstatus 0). It is
  never auto-submitted.
* Duplicate webhook deliveries (Shopify retries on timeout) are detected
  by shopify_order_id and skipped rather than creating a second Sales
  Order.
* We always return HTTP 200 to Shopify once we've handled (or logged)
  the event - including failures - so Shopify doesn't treat a mapping
  problem on our end as a delivery failure and hammer us with retries
  for up to 48 hours. Failures are surfaced via Shopify Order Log
  instead.
"""

import base64
import hashlib
import hmac
import json

import frappe
from frappe.utils import now_datetime


@frappe.whitelist(allow_guest=True)
def order_webhook(*args, **kwargs):
	raw_body = frappe.request.get_data()
	shop_domain = frappe.request.headers.get("X-Shopify-Shop-Domain")
	received_hmac = frappe.request.headers.get("X-Shopify-Hmac-Sha256")
	topic = frappe.request.headers.get("X-Shopify-Topic", "")

	try:
		store = _resolve_store(shop_domain)
		_verify_hmac(store, raw_body, received_hmac)
		order = json.loads(raw_body)
	except Exception as e:
		frappe.log_error(
			title="Shopify Webhook Rejected",
			message=f"shop={shop_domain} topic={topic} error={e}\n{frappe.get_traceback()}",
		)
		# Don't create a log row tied to a store/order we couldn't even verify -
		# just refuse quietly. Returning a non-200 here IS what we want, since
		# a bad signature might mean the request isn't really from Shopify.
		frappe.local.response.http_status_code = 401
		return {"status": "rejected"}

	shopify_order_id = str(order.get("id"))
	shopify_order_number = str(order.get("name") or order.get("order_number") or "")

	if frappe.db.exists(
		"Shopify Order Log",
		{"shopify_order_id": shopify_order_id, "status": "Success"},
	):
		_log(store.name, shopify_order_id, shopify_order_number, "Duplicate Ignored",
			"Order already processed successfully; ignoring redelivered webhook.", raw_body)
		return {"status": "duplicate_ignored"}

	try:
		sales_order = _create_sales_order(store, order)
		_log(store.name, shopify_order_id, shopify_order_number, "Success",
			f"Created draft Sales Order {sales_order.name}", raw_body, sales_order.name)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title="Shopify Order Sync Failed", message=frappe.get_traceback())
		_log(store.name, shopify_order_id, shopify_order_number, "Failed", str(e), raw_body)

	# Always 200 - see module docstring.
	return {"status": "received"}


def _resolve_store(shop_domain: str):
	if not shop_domain:
		frappe.throw("Missing X-Shopify-Shop-Domain header")

	if not frappe.db.exists("Shopify Settings", shop_domain):
		frappe.throw(f"No Shopify Settings found for store {shop_domain}")

	store = frappe.get_doc("Shopify Settings", shop_domain)
	if not store.enabled:
		frappe.throw(f"Shopify Settings for {shop_domain} is disabled")

	return store


def _verify_hmac(store, raw_body: bytes, received_hmac: str):
	secret = store.get_password("webhook_secret")
	if not secret:
		frappe.throw(f"No webhook secret configured for {store.name}")
	if not received_hmac:
		frappe.throw("Missing X-Shopify-Hmac-Sha256 header")

	digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
	computed_hmac = base64.b64encode(digest).decode()

	if not hmac.compare_digest(computed_hmac, received_hmac):
		frappe.throw("HMAC signature verification failed")


def _create_sales_order(store, order: dict):
	line_items = order.get("line_items", [])
	if not line_items:
		frappe.throw("Order has no line items")

	resolved_items = []
	missing = []

	for line in line_items:
		variant_id = str(line.get("variant_id"))
		row_name = f"{store.name}-{variant_id}"
		item_code = frappe.db.get_value("Shopify Product Mapping", row_name, "erpnext_item_code")

		if not item_code:
			missing.append(f"{line.get('title')} (variant {variant_id})")
			continue

		resolved_items.append({
			"item_code": item_code,
			"qty": line.get("quantity") or 1,
			"rate": line.get("price"),
			"warehouse": store.default_warehouse,
		})

	if missing:
		frappe.throw(
			"Cannot create Sales Order - the following line items have no "
			"ERPNext Item mapped in Shopify Product Mapping: " + "; ".join(missing)
		)

	so = frappe.new_doc("Sales Order")
	so.customer = store.default_customer
	so.company = store.company
	so.selling_price_list = store.price_list
	so.transaction_date = now_datetime().date()
	so.delivery_date = now_datetime().date()
	so.po_no = order.get("name") or order.get("order_number")

	for item in resolved_items:
		so.append("items", item)

	so.insert(ignore_permissions=True)
	# Deliberately not submitted - stays as a draft for manual review.
	frappe.db.commit()
	return so


def _log(store, order_id, order_number, status, message, raw_payload, sales_order=None):
	frappe.get_doc({
		"doctype": "Shopify Order Log",
		"shopify_store": store,
		"shopify_order_id": order_id,
		"shopify_order_number": order_number,
		"status": status,
		"sales_order": sales_order,
		"message": message[:140] if message else message,
		"raw_payload": raw_payload.decode("utf-8") if isinstance(raw_payload, bytes) else raw_payload,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
