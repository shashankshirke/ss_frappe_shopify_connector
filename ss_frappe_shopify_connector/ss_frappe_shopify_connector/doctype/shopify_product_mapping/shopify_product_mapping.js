frappe.ui.form.on("Shopify Product Mapping", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.mapping_status === "Auto-Matched (Review)") {
			frm.add_custom_button(__("Confirm Mapping"), () => {
				frappe.call({
					method: "ss_frappe_shopify_connector.ss_frappe_shopify_connector.doctype.shopify_product_mapping.shopify_product_mapping.confirm_mapping",
					args: { name: frm.doc.name },
					freeze: true,
					callback: () => frm.reload_doc(),
				});
			}).addClass("btn-primary");
		}
	},
});
