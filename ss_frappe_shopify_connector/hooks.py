app_name = "ss_frappe_shopify_connector"
app_title = "SS Frappe Shopify Connector"
app_publisher = "Your Company"
app_description = "Shopify OAuth access token manager for Frappe"
app_email = "you@example.com"
app_license = "MIT"

# Scheduled Tasks
# ---------------
# Checked every 15 minutes so tokens that fall inside the 1-hour-to-expiry
# window are always caught well before they actually expire.
scheduler_events = {
	"cron": {
		"*/15 * * * *": [
			"ss_frappe_shopify_connector.tasks.refresh_expiring_tokens"
		]
	}
}
