  ```
2. Or add the following line to your `.env` file:
   ```
   MAINTENANCE_MODE=true
   ```
3. Restart the watcher container:
   ```bash
   docker compose restart alert_watcher
   ```
4. Re-enable alerts after maintenance by removing the variable and restarting:
   ```bash
   unset MAINTENANCE_MODE
   docker compose restart alert_watcher
   ```

---

## 🧮 Alert Cooldowns

To prevent spam, each alert type enforces a cooldown (default = 300 seconds).
If the condition persists beyond this window, alerts will refire after cooldown expiry.

---

## 🧰 Quick Reference

| Alert Type | Slack Color | Condition Trigger | Operator Action |
|-------------|--------------|-------------------|-----------------|
| High Error Rate | 🔴 Red | 5xx ratio exceeds threshold | Inspect backend logs, investigate errors |
| Failover | 🟡 Yellow | Pool switch detected | Check health of failed pool |
| Recovery | 🟢 Green | Primary pool restored | Verify system stability |

---

## 📘 Notes

- Alerts are formatted using Slack **Block Kit**.
- The alert watcher consumes logs from Nginx and uses rate thresholds to detect unhealthy pools.
- For chaos testing or failover simulation, induce temporary 5xx errors in one pool (e.g., by stopping one container) to trigger the alert sequence.
