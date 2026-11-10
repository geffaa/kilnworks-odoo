<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
delegated: Odoo 18 Community + OCA modules (base_tier_validation, purchase/sale_tier_validation, queue_job), OWL 2 for custom client actions, QWeb for reports, PostgreSQL 16, Docker Compose. Chosen because the target job market asks for Odoo 17/18, Python, OWL and PostgreSQL, and Community covers every MVP feature.

## Users
Primary audience: reviewers of the portfolio (Upwork clients hiring an Odoo developer, tech leads at Indonesian ERP implementers) who spend 3–5 minutes on a catalog, repo or demo and judge whether modules feel native to Odoo and are built the way a senior would build them.
In-demo users (synthetic): owner/approver, head of production who buys raw materials, B2B sales, e-commerce ops watching Shopify sync.

## Product Purpose
A single Odoo 18 instance for a synthetic stoneware maker (Kilnworks, Kasongan) carrying six custom modules: approvals, Shopify connector, Midtrans payment provider, REST API with webhooks, ops dashboard with QWeb reports, and a module migrated from v16 to v18. Each module doubles as one Upwork Project Catalog. Success: modules install cleanly, tests pass in CI, demo is reachable, catalogs get Odoo invitations.

## Positioning
Extends OCA and core instead of re-implementing them (tier validation, queue_job, payment.provider pattern), and shows the work through tests, migration commits and a runnable demo rather than configuration screenshots.

## Operating Context
Lives inside the Odoo backend: app switcher, breadcrumbs, control panel, form sheet and chatter are the host's and stay untouched. Custom surfaces are OWL client actions inside that layout. Reviewers meet it through Upwork catalog media (GIF, screenshots), the GitHub README and a read-only demo login.

## Capabilities and Constraints
Odoo 18 Community only (no Studio, Approvals app or Spreadsheet). Sandbox credentials only (Shopify dev store, Midtrans sandbox). Currencies: IDR for B2B, USD for Shopify. Timezone Asia/Jakarta. Coretax/e-Faktur export is phase 2 and its format is unverified. Midtrans absence from core 18 is an assumption to verify.

## Brand Commitments
Kilnworks is a synthetic company; every material says "demo build on synthetic data". No client claims.

## Evidence on Hand
None yet: no screenshots, demo, video or client work exist. Market research links live in docs/PRD.md and docs/FEATURE-MAP.md. Do not fabricate testimonials, client logos or usage numbers.

## Product Principles
1. Native first: a reviewer who knows Odoo should not be able to tell where core ends and the module begins, except by its usefulness.
2. Reuse before writing: core and OCA are extended, never copied.
3. Every integration is idempotent, signed and retryable, and shows its failures to a human.
4. Proof over claims: tests, commits and a live demo carry the portfolio.

## Accessibility & Inclusion
WCAG 2.2 AA for custom OWL components; visible keyboard focus; strings translatable (English source, Indonesian translation).
