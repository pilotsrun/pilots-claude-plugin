# Domains

## What this covers

Serving an app on a hostname the user owns. Not covered: the URL every service already has, which is minted automatically and never changes (deploy.md).

## The command to copy

    pilot domain add app.example.com web

MCP: `domains` lists what exists and whether each is verified. ADDING one is the user's command, because it needs a DNS record only they can create.

## What happens

1. `pilot domain add` records the hostname and prints the DNS record to create.
2. The user creates the record at their registrar.
3. Verification passes, and a certificate is issued for the name.
4. The service serves on both its own URL and the custom domain. The original URL keeps working.

## The rules

| Rule | Why |
| --- | --- |
| the user adds the domain | it needs a DNS record at their registrar |
| a name under the fleet's own domain is refused | that name is already minted for them; accepting it would let one tenant claim another's URL |
| verification comes before a certificate | an unverified name would spend the fleet's shared certificate rate limit on a name nobody owns |

## Each answer and what to do

| Answer | Meaning | Do |
| --- | --- | --- |
| `verified: false` | the DNS record is not visible yet | tell the user which record to create; DNS takes minutes |
| `bad_request` about the fleet domain | the hostname is under the fleet's own apex | use a name the user owns |

## A domain for the whole team

Every machine and service of a team can be addressed under one domain the team owns, instead of the fleet's: `<name>.apps.example.com` and `<port>-<name>.apps.example.com`.

    pilot org domain set apps.example.com

MCP: `team_domain` reads it, `team_domain_set` sets it, `team_domain_remove` removes it. The answer lists two records for the user to create, DNS only (not proxied):

| Record | Points at | Why |
| --- | --- | --- |
| `*.apps.example.com` CNAME | the fleet's API hostname | sends every name under the domain to the fleet |
| `_acme-challenge.apps.example.com` CNAME | `apps.example.com._acme.<fleet domain>` | lets the fleet obtain and renew the wildcard certificate without access to the team's zone |

Addresses move to the domain once both resolve. Every `<name>.<fleet domain>` address keeps working. Only the team's own machines and services answer under its domain, and no other team can take it or attach a custom domain under it. Setting the same domain again checks the records again.

## Do not

- Do not add a domain for the user. Print the command and the record.
- Do not wait in a loop for verification. DNS propagation is not something to poll through.
