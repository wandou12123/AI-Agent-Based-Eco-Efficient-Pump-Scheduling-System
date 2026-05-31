"""本地集成测试脚本"""
import sys
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" - {detail}"
    print(line)


def main():
    # 1. Health
    r = httpx.get(f"{BASE}/api/health", timeout=10)
    check("健康检查", r.status_code == 200, r.text[:120])

    # 2. Login
    r = httpx.post(
        f"{BASE}/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=10,
    )
    body = r.json()
    token = body.get("data", {}).get("access_token") or body.get("access_token")
    check("管理员登录", r.status_code == 200 and bool(token), f"status={r.status_code}")

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Stations
    r = httpx.get(f"{BASE}/api/v1/stations", headers=headers, timeout=10)
    body = r.json()
    stations = body.get("data", body)
    check("泵站列表", r.status_code == 200 and len(stations) > 0, f"共 {len(stations)} 个泵站")
    sid = stations[0]["id"]

    # 4. Operating points
    r = httpx.get(f"{BASE}/api/v1/stations/{sid}/status", headers=headers, timeout=10)
    body = r.json()
    ops = body.get("data", body)
    check("工况数据", r.status_code == 200, f"{len(ops)} 条工况点")

    # 5. Create task
    r = httpx.post(
        f"{BASE}/api/v1/tasks",
        headers=headers,
        json={
            "station_id": sid,
            "objective_text": "最小化能耗",
            "constraints_json": {"station_id": sid, "min_flow": 200},
        },
        timeout=10,
    )
    body = r.json()
    task = body.get("data", body)
    tid = task["id"]
    check("创建调度任务", r.status_code == 200, f"task_id={tid}")

    # 6. Optimize (with Qwen LLM)
    print("正在执行优化（含千问 LLM 解释，约 10-30s）...")
    r = httpx.post(f"{BASE}/api/v1/tasks/{tid}/optimize", headers=headers, timeout=120)
    body = r.json()
    opt = body.get("data", body)
    plan = opt.get("plan", {})
    has_plan = bool(plan.get("plan"))
    explanation = opt.get("explanation") or ""
    check(
        "调度优化",
        r.status_code == 200 and has_plan,
        f"status={opt.get('status')}, feasible={plan.get('feasible')}",
    )
    check("LLM 解释生成", bool(explanation), explanation[:80])

    # 7. Safety
    safety = plan.get("safety", {})
    check("安全校验", "passed" in safety, f"passed={safety.get('passed')}")

    # 8. Conversations
    r = httpx.get(f"{BASE}/api/v1/conversations", headers=headers, timeout=10)
    check("会话列表", r.status_code == 200)

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== 合计: {passed}/{len(results)} 通过 ===")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
