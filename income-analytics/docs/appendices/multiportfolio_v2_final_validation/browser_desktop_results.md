# Desktop browser validation

Status: `NOT_RUN_ENVIRONMENT_LIMITATION`.

The available in-app browser was already at `http://127.0.0.1:8000/#entender` and returned `ERR_CONNECTION_REFUSED`. Launching an isolated local server was rejected by the execution policy. No Playwright, Cypress, Selenium, or browser-test dependency is installed. I did not bypass controls, expose a server, or add a new browser framework. ASGI `TestClient` route checks and existing frontend Node tests ran separately; they do not certify desktop UI behavior.
