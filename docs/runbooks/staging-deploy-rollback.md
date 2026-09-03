# Runbook: Staging Deployment, Port Audit, and Rollback (F13.2)

## Purpose
This runbook provides the authoritative operational procedure for provisioning, deploying, verifying network policies, and rolling back the ShreeNexa production stack on AWS Lightsail Mumbai (`ap-south-1`).

---

## 1. Prerequisites & Host Provisioning

1. Ensure AWS Lightsail Mumbai instance (Ubuntu 24.04 LTS, 2GB or 4GB plan) is initialized.
2. Execute the automated provisioning script:
   ```bash
   sudo /opt/shreenexa/infra/lightsail/provision.sh
   ```
3. Confirm system services and directories:
   ```bash
   id shreenexa # UID 10001
   ls -la /opt/shreenexa
   ```

---

## 2. Public Network Policy & Port Reachability Audit

> **Proof Requirement**: "Only intended public ports are reachable."

Run a port scan from an external machine or run an audit locally:
```bash
# Verify UFW active rules:
sudo ufw status verbose
```
Expected output:
```text
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere (SSH)
80/tcp                     ALLOW IN    Anywhere (HTTP)
443/tcp                    ALLOW IN    Anywhere (HTTPS)
5432/tcp                   DENY IN     Anywhere
6379/tcp                   DENY IN     Anywhere
8000/tcp                   DENY IN     Anywhere
8001/tcp                   DENY IN     Anywhere
8080/tcp                   DENY IN     Anywhere
8081/tcp                   DENY IN     Anywhere
8082/tcp                   DENY IN     Anywhere
```

Verify external reachability using `nmap` or `nc`:
```bash
# External probe test
nmap -Pn -p 22,80,443,5432,6379,8000,8001,8080 <LIGHTSAIL_PUBLIC_IP>
```
- Ports 80, 443, 22 must report `open`.
- Ports 5432, 6379, 8000, 8001, 8080, 8081, 8082 must report `filtered` or `closed`.

---

## 3. Zero-Downtime Blue/Green Staging Deployment

The API runs as stateless Blue (`127.0.0.1:8000`) and Green (`127.0.0.1:8001`) instances behind Caddy. Background daemons (`engine`, `feedd`, `worker`) run under persistent systemd supervision and are **never restarted** during API deployment.

### Step 3.1: Check Currently Active Color
```bash
python3 -c "
from pathlib import Path
from infra.lightsail.blue_green import get_active_color
content = Path('/etc/caddy/Caddyfile').read_text()
print('Active Color:', get_active_color(content))
"
```

### Step 3.2: Pull Candidate Image & Start Inactive Container
If active is `blue` (8000), target candidate is `green` (8001):
```bash
docker pull shreenexa/api:candidate
docker run -d --name shreenexa-api-green \
  --network shreenexa-prod-net \
  --user 10001:10001 \
  --cpus 1.0 --memory 512m \
  -p 127.0.0.1:8001:8000 \
  --env-file /opt/shreenexa/config/prod.env \
  shreenexa/api:candidate
```

### Step 3.3: Pre-Traffic Candidate Health Gate
Probe candidate container health before routing traffic:
```bash
curl -f http://127.0.0.1:8001/healthz || exit 1
```

### Step 3.4: Flip Caddy Upstream & Reload
Use the controller script to atomically update Caddyfile and trigger zero-downtime reload:
```bash
python3 -c "
from pathlib import Path
from infra.lightsail.blue_green import promote_candidate
res = promote_candidate(Path('/etc/caddy/Caddyfile'))
print(res)
assert res.success
"
sudo systemctl reload caddy
```

### Step 3.5: Drain & Terminate Previous Instance
Allow 15 seconds for inflight WebSocket/HTTP requests on the previous instance to complete, then terminate:
```bash
sleep 15
docker stop -t 10 shreenexa-api-blue
docker rm shreenexa-api-blue
```

---

## 4. Emergency Rollback Protocol

If errors, latency spikes, or regression anomalies are observed after promotion:

1. Start the previous color immediately (if stopped):
   ```bash
   docker run -d --name shreenexa-api-blue \
     -p 127.0.0.1:8000:8000 \
     --env-file /opt/shreenexa/config/prod.env \
     shreenexa/api:previous
   ```
2. Execute rollback:
   ```bash
   python3 -c "
   from pathlib import Path
   from infra.lightsail.blue_green import rollback
   res = rollback(Path('/etc/caddy/Caddyfile'))
   print(res)
   assert res.success
   "
   sudo systemctl reload caddy
   ```
3. Stop and prune the faulty candidate:
   ```bash
   docker stop -t 5 shreenexa-api-green
   docker rm shreenexa-api-green
   ```
4. Verify primary ingress is restored:
   ```bash
   curl -i https://<DOMAIN>/healthz
   ```
