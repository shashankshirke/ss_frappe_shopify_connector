"""
Core helper for getting a valid Shopify access token.

Any other doctype/module in this app (or added later) should call
`get_access_token(store_url)` rather than reading the `access_token`
field on Shopify Settings directly. That way the refresh logic lives
in exactly one place and callers always get a token that is valid.
"""

import requests
import frappe
from frappe.utils import now_datetime, add_to_date, get_datetime

REFRESH_BUFFER_MINUTES = 60  # refresh if less than this much time is left


def get_access_token(store_url: str, force_refresh: bool = False) -> str:
	"""Return a valid access token for the given store, refreshing it first if needed."""

	settings = frappe.get_doc("Shopify Settings", store_url)

	if not settings.enabled:
		frappe.throw(f"Shopify Settings for {store_url} is disabled.")

	if force_refresh or _needs_refresh(settings):
		_refresh_token(settings)

	return settings.get_password("access_token")


def _needs_refresh(settings) -> bool:
	if not settings.access_token or not settings.token_expires_at:
		return True

	buffer_time = add_to_date(now_datetime(), minutes=REFRESH_BUFFER_MINUTES)
	return get_datetime(settings.token_expires_at) <= buffer_time


def _refresh_token(settings):
	"""Call Shopify's OAuth endpoint and persist the new token + expiry."""

	url = f"https://{settings.store_url}/admin/oauth/access_token"
	payload = {
		"grant_type": "client_credentials",
		"client_id": settings.client_id,
		"client_secret": settings.get_password("client_secret"),
	}

	try:
		response = requests.post(url, data=payload, timeout=30)
		response.raise_for_status()
		data = response.json()

		access_token = data["access_token"]
		expires_in = data.get("expires_in", 0)

		settings.db_set("access_token", access_token)
		settings.db_set("token_expires_at", add_to_date(now_datetime(), seconds=expires_in))
		settings.db_set("last_refreshed_on", now_datetime())
		settings.db_set("status", "Active")

		_log(settings.name, "Success", f"Token refreshed. Expires in {expires_in} seconds.")

	except Exception as e:
		settings.db_set("status", "Error")
		_log(settings.name, "Failed", str(e))
		frappe.log_error(title="Shopify Token Refresh Failed", message=frappe.get_traceback())
		frappe.throw(f"Failed to refresh Shopify token for {settings.store_url}: {e}")


def _log(store, status, message):
	frappe.get_doc({
		"doctype": "Shopify Logs",
		"store": store,
		"timestamp": now_datetime(),
		"status": status,
		"message": message,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
