import frappe
from frappe.model.document import Document
from frappe.utils import get_url
from ss_frappe_shopify_connector.api import get_access_token


class ShopifySettings(Document):
	def validate(self):
		# Keep the read-only helper field showing the exact URL the user needs
		# to paste into Shopify Admin when creating the order webhook.
		self.webhook_url = get_url(
			"/api/method/ss_frappe_shopify_connector.orders.order_webhook"
		)


@frappe.whitelist()
def generate_token_now(store_url):
	"""Called from the 'Generate Token Now' button on the form."""
	frappe.only_for("System Manager")
	get_access_token(store_url, force_refresh=True)
	frappe.msgprint(f"Access token refreshed for {store_url}")


@frappe.whitelist()
def fetch_products_now(store_url):
	"""Called from the 'Fetch Products' button on the form."""
	frappe.only_for("System Manager")
	from ss_frappe_shopify_connector.products import fetch_products

	summary = fetch_products(store_url)
	frappe.msgprint(
		"Fetch complete.<br>"
		f"New: {summary['created']} &nbsp; "
		f"Updated: {summary['updated']} &nbsp; "
		f"Auto-matched by SKU: {summary['auto_matched']}"
	)
	return summary
