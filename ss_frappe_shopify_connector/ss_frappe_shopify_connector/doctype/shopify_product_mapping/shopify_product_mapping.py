import frappe
from frappe.model.document import Document


class ShopifyProductMapping(Document):
	def validate(self):
		# Keep mapping_status in sync with whether an Item has been linked.
		# Any row that has an ERPNext Item Code and is saved through the UI
		# (whether that's a fresh manual mapping or a human confirming an
		# "Auto-Matched (Review)" row) is treated as reviewed and promoted
		# to "Mapped". If the Item Code is ever cleared, it drops back to
		# "Unmapped" rather than silently keeping a stale "Mapped" status.
		if self.erpnext_item_code:
			self.mapping_status = "Mapped"
		else:
			self.mapping_status = "Unmapped"
