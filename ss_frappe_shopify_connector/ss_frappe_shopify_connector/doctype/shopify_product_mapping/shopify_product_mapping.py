import frappe
from frappe.model.document import Document


class ShopifyProductMapping(Document):
	def validate(self):
		# Keep mapping_status in sync with whether an Item has been linked.
		# Any row that has an ERPNext Item Code and is saved through the UI
		# (whether that's a fresh manual mapping or an edit to an existing
		# row) is treated as reviewed and promoted to "Mapped". If the Item
		# Code is ever cleared, it drops back to "Unmapped".
		#
		# Note: this only fires when the form is actually dirty (Frappe skips
		# save entirely otherwise) - see confirm_mapping() below for the case
		# where an auto-matched row is already correct and nothing needs editing.
		if self.erpnext_item_code:
			self.mapping_status = "Mapped"
		else:
			self.mapping_status = "Unmapped"


@frappe.whitelist()
def confirm_mapping(name):
	"""Called from the 'Confirm Mapping' button - promotes an Auto-Matched
	(Review) row straight to Mapped without requiring the user to make an
	edit first just to get the form into a dirty/saveable state."""
	doc = frappe.get_doc("Shopify Product Mapping", name)
	frappe.has_permission("Shopify Product Mapping", "write", doc=doc, throw=True)

	if not doc.erpnext_item_code:
		frappe.throw("Select an ERPNext Item Code before confirming this mapping.")

	doc.db_set("mapping_status", "Mapped")
	return "Mapped"
