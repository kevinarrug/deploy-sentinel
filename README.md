# deploy-sentinel

Lightweight deployment monitoring and rollback automation for Docker containers.

---

## Installation

```bash
pip install deploy-sentinel
```

Or install from source:

```bash
git clone https://github.com/yourorg/deploy-sentinel.git && pip install -e .
```

---

## Usage

Define a simple config and let `deploy-sentinel` watch your containers, detect failures, and roll back automatically.

```python
from deploy_sentinel import Sentinel

sentinel = Sentinel(
    container="my-app",
    health_endpoint="http://localhost:8080/health",
    check_interval=10,       # seconds
    failure_threshold=3,     # consecutive failures before rollback
    rollback_image="my-app:stable"
)

sentinel.start()
```

Or use the CLI:

```bash
deploy-sentinel watch --container my-app \
  --health-url http://localhost:8080/health \
  --rollback-image my-app:stable
```

When `deploy-sentinel` detects that a container's health check has failed `n` consecutive times, it automatically stops the unhealthy container and restarts it using the specified rollback image.

---

## Features

- 🔍 Continuous health check monitoring via HTTP or TCP
- ⏪ Automatic rollback to a known-good Docker image
- 📣 Webhook notifications on rollback events
- 🐳 Works with Docker Engine API (no Swarm or Kubernetes required)

---

## Requirements

- Python 3.8+
- Docker Engine with socket access (`/var/run/docker.sock`)

---

## License

MIT © 2024 deploy-sentinel contributors