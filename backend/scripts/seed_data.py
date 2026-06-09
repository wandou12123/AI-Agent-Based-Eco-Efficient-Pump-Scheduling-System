"""初始化演示数据（泵站、机组、工况时序）"""
import pymysql
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.security import hash_password

settings = get_settings()

conn = pymysql.connect(
    host=settings.MYSQL_HOST,
    user=settings.MYSQL_USER,
    password=settings.MYSQL_PASSWORD,
    database=settings.MYSQL_DATABASE,
    charset="utf8mb4",
)
cur = conn.cursor()

# 演示账号：admin/admin123, operator/operator123, viewer/viewer123
users = [
    ("admin", hash_password("admin123"), "admin"),
    ("operator", hash_password("operator123"), "operator"),
    ("viewer", hash_password("viewer123"), "viewer"),
]
for username, pwd_hash, role in users:
    cur.execute(
        "INSERT IGNORE INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
        (username, pwd_hash, role),
    )

cur.execute(
    "INSERT IGNORE INTO pump_stations (id, name, location, meta_json) VALUES (%s, %s, %s, %s)",
    (1, "东湖泵站", "浙江省杭州市", '{"design_flow": 500}'),
)
units = [
    (1, 1, "1号机组", 150, 100),
    (2, 1, "2号机组", 180, 120),
    (3, 1, "3号机组", 200, 150),
    (4, 1, "4号机组", 220, 160),
    (5, 1, "5号机组", 240, 180),
]
for u in units:
    cur.execute(
        "INSERT IGNORE INTO pump_units (id, station_id, unit_name, rated_power_kw, rated_flow) VALUES (%s,%s,%s,%s,%s)",
        u,
    )

# 12 条工况时序（近 2 小时，每 10 分钟一条）
base = datetime.now().replace(second=0, microsecond=0)
flows = [260, 275, 290, 305, 320, 335, 328, 310, 295, 280, 270, 285]
for i, flow in enumerate(flows):
    ts = base - timedelta(minutes=(len(flows) - i) * 10)
    head = 11.2 + (i % 5) * 0.15
    power = 300 + i * 8
    cur.execute(
        """
        INSERT IGNORE INTO operating_points (id, station_id, flow, head, power, ts)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (i + 1, 1, flow, head, power, ts),
    )

conn.commit()
cur.execute("SELECT username, role FROM users")
print("Users:", cur.fetchall())
cur.execute("SELECT COUNT(*) FROM operating_points WHERE station_id=1")
print("Operating points:", cur.fetchone()[0])
conn.close()
print("Seed done — 演示账号 admin/admin123 operator/operator123 viewer/viewer123")
