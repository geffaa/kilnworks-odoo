# Kilnworks on Odoo
DB ?= kilnworks
MOD ?= kw_demo
RUN = docker compose run --rm odoo odoo -d $(DB) --db-filter=.*

.PHONY: up down logs demo test shell psql reset lint

up:            ## start the stack (Odoo on localhost:8069)
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f odoo

demo:          ## create the demo database with every Kilnworks module
	docker compose up -d db
	$(RUN) -i kw_demo --without-demo=all --stop-after-init --load-language=en_US
	docker compose up -d odoo

test:          ## run one module's tests in a throwaway database: make test MOD=kw_approval
	docker compose up -d db
	docker compose exec -T db dropdb -U odoo --if-exists test_$(MOD)
	docker compose run --rm odoo odoo -d test_$(MOD) -i $(MOD) --test-tags=/$(MOD) --test-enable --stop-after-init \
		--without-demo=all --log-level=test --workers=0 --db-filter=^test_$(MOD)$$; \
	status=$$?; docker compose exec -T db dropdb -U odoo --if-exists test_$(MOD); exit $$status

shell:
	docker compose run --rm odoo odoo shell -d $(DB) --no-http

psql:
	docker compose exec db psql -U odoo $(DB)

reset:         ## drop the demo database and rebuild it
	docker compose stop odoo
	docker compose exec -T db dropdb -U odoo --if-exists $(DB)
	$(MAKE) demo

lint:
	pre-commit run --all-files
