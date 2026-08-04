frappe.ui.form.on("Shopify Settings", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Generate Token Now"), () => {
				frappe.call({
					method: "ss_frappe_shopify_connector.ss_frappe_shopify_connector.doctype.shopify_settings.shopify_settings.generate_token_now",
					args: { store_url: frm.doc.name },
					freeze: true,
					freeze_message: __("Requesting access token from Shopify..."),
					callback: () => frm.reload_doc(),
				});
			});

			frm.add_custom_button(__("Fetch Products"), () => {
				frappe.confirm(
					__(
						"This will pull all products/variants from Shopify and create or update rows in Shopify Product Mapping. Continue?"
					),
					() => {
						frappe.call({
							method: "ss_frappe_shopify_connector.ss_frappe_shopify_connector.doctype.shopify_settings.shopify_settings.fetch_products_now",
							args: { store_url: frm.doc.name },
							freeze: true,
							freeze_message: __("Fetching products from Shopify..."),
							callback: (r) => {
								if (r.message) {
									frappe.set_route(
										"List",
										"Shopify Product Mapping",
										{ shopify_store: frm.doc.name }
									);
								}
							},
						});
					}
				);
			});
		}
	},
});
