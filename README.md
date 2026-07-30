# SS Frappe Shopify Connector

A small Frappe app that manages Shopify OAuth access tokens: you enter a
store's `store_url`, `client_id`, and `client_secret`, and the app takes
care of generating and auto-refreshing the access token before it expires.

## Doctypes

- **Shopify Settings** — one record per Shopify store. Holds `store_url`,
  `client_id`, `client_secret`, and the current `access_token` +
  `token_expires_at`. Includes a "Generate Token Now" button for a manual
  first-time fetch.
- **Shopify Logs** — a log of every refresh attempt (success or failure),
  linked to the store, for auditing/troubleshooting.

## How it works

1. Create a **Shopify Settings** record with your store URL, client ID,
   and client secret, then save it.
2. Click **Generate Token Now** to fetch the first token (or just wait for
   the scheduler).
3. A scheduled job (`tasks.refresh_expiring_tokens`) runs every 15 minutes,
   checks every enabled store, and refreshes any token that is within
   1 hour of expiry (or missing/expired).
4. Every refresh attempt — success or failure — is recorded in **Shopify
   Logs**.
5. Any other doctype/module you build later should call:

   ```python
   from ss_frappe_shopify_connector.api import get_access_token

   token = get_access_token("xxx.myshopify.com")
   ```

   This always returns a valid token, refreshing it first if needed, so
   you never have to think about expiry in your own code.

## Installation

```bash
bench get-app ss_frappe_shopify_connector /path/to/this/folder
bench --site your-site install-app ss_frappe_shopify_connector
```

Or, if pushed to a git repo:

```bash
bench get-app https://github.com/yourorg/ss_frappe_shopify_connector.git
bench --site your-site install-app ss_frappe_shopify_connector
```

## Security notes

- `client_secret` and `access_token` are stored using Frappe's `Password`
  fieldtype, which encrypts them at rest.
- Both doctypes are restricted to the **System Manager** role by default —
  adjust permissions as needed for your setup.
- Rotate any credentials you may have shared or pasted elsewhere (chat,
  tickets, etc.) before going to production.
