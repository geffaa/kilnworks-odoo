# Official Odoo 18 image plus what the test suite needs: the helper OCA tests import, and a real
# headless Chromium (the image is Ubuntu, whose chromium package is only a snap stub) with
# websocket-client, so browser tours actually run instead of being skipped.
FROM odoo:18.0
USER root
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
RUN pip3 install --no-cache-dir --break-system-packages \
        odoo-test-helper==2.1.1 websocket-client==1.8.0 playwright==1.47.0 \
    && python3 -m playwright install --with-deps chromium \
    && ln -sf "$(find /opt/pw-browsers -type f -name chrome -path '*chrome-linux*' | head -1)" /usr/local/bin/chromium \
    && chmod -R a+rX /opt/pw-browsers \
    && rm -rf /var/lib/apt/lists/*
USER odoo
