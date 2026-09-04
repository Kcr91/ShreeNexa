# Live Trading Activation Checklist and SEBI Static IP Runbook

This runbook defines the mandatory verification checklist for promoting ShreeNexa Terminal from Paper Trading mode to Live Broker Execution (Epic 12, Spec §11.1).

## 1. Safety Invariants

1. **Closed-by-Default Execution Gate**:
   - `SHREENEXA_ENABLE_LIVE_TRADING` defaults to `false`.
   - The terminal operates in 100% simulated Paper Trading mode unless explicitly authorized and opted in.
   - Any live order placement attempted while this flag is `false` fails closed with `403 Forbidden` (`LiveTradingDisabledError`).

2. **SEBI Static IP Verification**:
   - In accordance with SEBI circulars and DhanHQ v2 API compliance requirements, all automated and interactive orders must originate from pre-declared, whitelisted static IP addresses.
   - ShreeNexa automatically resolves its public outbound egress IP at preflight before submitting any order.
   - If the resolved egress IP does not match either the configured **Primary Static IP** (AWS Lightsail Mumbai server) or the **Secondary Static IP** (authorized local workstation), order execution is immediately aborted with `StaticIPMismatchError`.
   - If network lookup or external IP discovery fails, the preflight **fails closed** (`Could not determine host outbound public IP address`).

3. **No Unattended Overrides in Production**:
   - `SHREENEXA_STATIC_IP_OVERRIDE` is strictly rejected and ignored when `ENVIRONMENT=production` or `APP_ENV=production`.
   - Production deployments always verify real egress IP through hardened discovery services (`api.ipify.org`, `ifconfig.me`, `checkip.amazonaws.com`).

---

## 2. Pre-Activation Checklist

Before setting `SHREENEXA_ENABLE_LIVE_TRADING=true`:

- [ ] **20 Reviewed Paper Market Days**: Terminal must complete at least 20 market sessions in paper execution mode with zero unaccounted fills or reconciler discrepancies.
- [ ] **Static IP Whitelist Registered in Dhan**:
  - Primary IP: Public IP of AWS Lightsail instance in `ap-south-1`.
  - Secondary IP: Dedicated static egress IP of backup workstation.
  - Verify via Dhan Web: `Settings > Profile & Security > Static IP Configuration`.
- [ ] **Kill Switch & Circuit Breaker Drill**:
  - Verify emergency freeze halts order placement within 100ms (`POST /api/v1/orders/ticket/place` returns `403 KillSwitchActiveError`).
- [ ] **Broker Truth Reconciliation Drill**:
  - Run `OrderReconciler` sync against `/v2/orders` and confirm position alignment.
- [ ] **Audit Trail Persistence**:
  - Confirm disk ledger write permissions at `data/audit/audit_events.jsonl`.
- [ ] **Credentials in Windows DPAPI / Secret Store**:
  - Plaintext `.env` files must not contain unencrypted production tokens.
  - Hydrate via `python -m app.dhan.token set`.

---

## 3. Emergency Cutoff Procedures

If unexpected market behavior, feed latency, or execution drift is detected:

1. **Immediate Panic Cutoff**:
   - Trigger the Panic button on the frontend terminal dashboard (or invoke `DELETE /v2/positions` via broker API).
2. **Deactivate Live Trading Flag**:
   - Set `SHREENEXA_ENABLE_LIVE_TRADING=false` in environment / container configuration and restart services.
3. **Engage Dhan Kill Switch**:
   - Call `DhanRestClient.manage_kill_switch(activate=True)` to block order placement at broker level.
