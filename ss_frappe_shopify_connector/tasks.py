import frappe
from ss_frappe_shopify_connector.api import get_access_token


def refresh_expiring_tokens():
	"""Runs every 15 minutes via cron. Refreshes any enabled store's token
	that is within the buffer window (or already missing/expired).
	get_access_token() already contains the "does it need refreshing"
	check, so this task just needs to call it for every enabled store."""

	stores = frappe.get_all("Shopify Settings", filters={"enabled": 1}, pluck="name")

	for store_url in stores:
		try:
			get_access_token(store_url)
		except Exception:
			# already logged inside api.py; keep going for other stores
			frappe.log_error(
				title="Shopify Scheduled Refresh Failed",
				message=frappe.get_traceback(),
			)
