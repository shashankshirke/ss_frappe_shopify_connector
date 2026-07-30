import frappe
from frappe.model.document import Document


class ShopifyProductMapping(Document):
	def validate(self):
		# Keep mapping_status in sync with whether an Item has been linked.
		# Auto-matched rows are left at "Auto-Matched (Review)" until a human
		# actually opens/saves the record to confirm it - at which point this
		# validate() promotes it to "Mapped". Manual edits go straight there too.
		if self.erpnext_item_code and self.mapping_status == "Unmapped":
			self.mapping_status = "Mapped"
		elif not self.erpnext_item_code:
			self.mapping_status = "Unmapped"
