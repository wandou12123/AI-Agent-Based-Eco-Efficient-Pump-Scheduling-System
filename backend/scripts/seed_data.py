"""初始化演示数据（泵站、机组、工况时序）

用法（在 backend 目录下）：
    python scripts/seed_data.py

Docker 部署时：
    docker compose exec backend python scripts/seed_data.py

修改 seed 后请重新执行本脚本以刷新泵站 location 与演示数据。
"""
import os
import sys

# 将 backend 根目录加入 path，以便 import app.*
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import pymysql
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.security import hash_password


def main() -> None:
    settings = get_settings()

    conn = pymysql.connect(
        host=settings.MYSQL_HOST,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
        charset="utf8mb4",
    )
    cur = conn.cursor()

    users = [
        ("admin", hash_password("admin123"), "admin"),
        ("operator", hash_password("operator123"), "operator"),
        ("viewer", hash_password("viewer123"), "viewer"),
    ]
    for username, pwd_hash, role in users:
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash), role=VALUES(role)
            """,
            (username, pwd_hash, role),
        )

    stations = [
        (1, "东湖泵站", "滨江路66号", '{"design_flow": 500}'),
        (2, "西湖泵站", "杭州市西湖区", '{"design_flow": 350}'),
        (3, "城南泵站", "杭州市萧山区", '{"design_flow": 400}'),
        (4, "城北泵站", "杭州市拱墅区", '{"design_flow": 320}'),
        (5, "钱塘泵站", "杭州市钱塘区", '{"design_flow": 450}'),
    ]
    for sid, name, location, meta in stations:
        cur.execute(
            """
            INSERT INTO pump_stations (id, name, location, meta_json) VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE name=VALUES(name), location=VALUES(location), meta_json=VALUES(meta_json)
            """,
            (sid, name, location, meta),
        )

    units = [
        # 东湖泵站 — 5 台
        (1, 1, "1号机组", 150, 100),
        (2, 1, "2号机组", 180, 120),
        (3, 1, "3号机组", 200, 150),
        (4, 1, "4号机组", 220, 160),
        (5, 1, "5号机组", 240, 180),
        # 西湖泵站 — 4 台
        (6, 2, "1号机组", 140, 90),
        (7, 2, "2号机组", 170, 110),
        (8, 2, "3号机组", 190, 130),
        (9, 2, "4号机组", 205, 140),
        # 城南泵站 — 4 台
        (10, 3, "1号机组", 160, 105),
        (11, 3, "2号机组", 185, 125),
        (12, 3, "3号机组", 210, 145),
        (13, 3, "4号机组", 230, 165),
        # 城北泵站 — 3 台
        (14, 4, "1号机组", 130, 85),
        (15, 4, "2号机组", 155, 95),
        (16, 4, "3号机组", 175, 115),
        # 钱塘泵站 — 4 台
        (17, 5, "1号机组", 165, 110),
        (18, 5, "2号机组", 195, 135),
        (19, 5, "3号机组", 215, 150),
        (20, 5, "4号机组", 235, 170),
    ]
    for uid, sid, name, power, flow in units:
        cur.execute(
            """
            INSERT INTO pump_units (id, station_id, unit_name, rated_power_kw, rated_flow)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                station_id=VALUES(station_id),
                unit_name=VALUES(unit_name),
                rated_power_kw=VALUES(rated_power_kw),
                rated_flow=VALUES(rated_flow)
            """,
            (uid, sid, name, power, flow),
        )

    base = datetime.now().replace(second=0, microsecond=0)
    station_flows = {
        1: [260, 275, 290, 305, 320, 335, 328, 310, 295, 280, 270, 285],
        2: [180, 190, 200, 210, 205, 195, 188, 192, 198, 203],
        3: [220, 235, 250, 265, 258, 242, 230, 245, 252, 238, 228, 240],
        4: [150, 158, 165, 172, 168, 160, 155, 162, 170, 175],
        5: [280, 295, 310, 325, 318, 305, 290, 300, 312, 288, 275, 302],
    }
    op_id = 1
    for station_id, flows in station_flows.items():
        for i, flow in enumerate(flows):
            ts = base - timedelta(minutes=(len(flows) - i) * 10)
            head = 11.0 + station_id * 0.3 + (i % 5) * 0.12
            power = 250 + station_id * 30 + i * 7
            cur.execute(
                """
                INSERT IGNORE INTO operating_points (id, station_id, flow, head, power, ts)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (op_id, station_id, flow, head, power, ts),
            )
            op_id += 1

    conn.commit()
    cur.execute("SELECT username, role FROM users WHERE username IN ('admin','operator','viewer')")
    print("Users:", cur.fetchall())
    cur.execute("SELECT id, name, location FROM pump_stations ORDER BY id")
    print("Stations:", cur.fetchall())
    cur.execute("SELECT station_id, COUNT(*) FROM pump_units GROUP BY station_id ORDER BY station_id")
    print("Units per station:", cur.fetchall())
    cur.execute("SELECT COUNT(*) FROM pump_units")
    print("Total units:", cur.fetchone()[0])
    conn.close()
    print("Seed done — 演示账号 admin/admin123 operator/operator123 viewer/viewer123")


if __name__ == "__main__":
    main()
