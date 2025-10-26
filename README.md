# Blue-Green Deployment with Nginx and Docker Compose

## Overview
This setup demonstrates a Blue/Green deployment strategy using two identical Node.js services behind Nginx.  
- **Blue** = Active instance  
- **Green** = Backup instance  

Nginx routes traffic to Blue by default and automatically switches to Green when Blue fails, ensuring zero downtime.

---

## How to Run

### 1️ Clone and Setup
```bash
git clone https://github.com/<your-username>/blue-green-deployment.git
cd blue-green-deployment
cp .env.example .env
```
### 2 Configure .env

Edit .env to match:
```bash
BLUE_IMAGE=yimikaade/wonderful:blue
GREEN_IMAGE=yimikaade/wonderful:green
ACTIVE_POOL=blue
RELEASE_ID_BLUE=1.0.0
RELEASE_ID_GREEN=1.0.1
PORT=3000
```
### 3️ Start
docker-compose up -d

### 4️ Test Endpoints

Main app (via Nginx): http://localhost:8080/version

Blue direct: http://localhost:8081/version

Green direct: http://localhost:8082/version

- Baseline (Blue active)
```bash
curl -X GET <http://localhost:8080/version> 
```
Response → 200, headers show:
```
X-App-Pool: blue ($APP_POOL)
X-Release-Id: $RELEASE_ID
...
```
consecutive requests: all 200, all indicate blue.

Now induce downtime on the active app (Blue):
```bash
curl -X POST <http://localhost:8081/chaos/start?mode=error> 
 ``` 
Immediate switch to Green
```bash
curl -X GET <http://localhost:8080/version> 
```
Response → 200 with headers:
```
X-App-Pool: green ($APP_POOL)
X-Release-Id: $RELEASE_ID
...
```
4.   Stability under failure
Requests to http://localhost:8080/version within ~10s:

### 5️ Simulate Failover

- Trigger chaos on Blue:
```bash
curl -X POST http://localhost:8081/chaos/start?mode=error
```
- Watch Nginx automatically switch to Green:
```bash
watch -n 2 'curl -s -i http://localhost:8080/version | grep X-App-Pool'
```

- Stop chaos:
```bash
curl -X POST http://localhost:8081/chaos/stop
```
