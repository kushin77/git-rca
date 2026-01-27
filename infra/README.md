# Dev Sandbox (Docker Compose)

This folder contains a minimal docker-compose setup to run the MVP skeleton in a local sandbox.

Steps:

1. Build and start the sandbox:

```bash
docker-compose -f infra/docker-compose.yml up --build
```

2. Visit http://localhost:8080 and the API at http://localhost:8080/api/events

Notes:

- This is a developer convenience; production deployment should use proper image builds, secret management, and orchestration.
