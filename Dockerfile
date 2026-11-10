# Official Odoo 18 image plus the test helper OCA modules import when tests are enabled.
FROM odoo:18.0
USER root
RUN pip3 install --no-cache-dir --break-system-packages odoo-test-helper==2.1.1
USER odoo
