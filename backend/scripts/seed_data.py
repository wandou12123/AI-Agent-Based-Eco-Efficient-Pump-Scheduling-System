"""初始化演示数据"""
import pymysql
from app.core.config import get_settings

settings = get_settings()

conn = pymysql.connect(
    host=settings.MYSQL_HOST,
    user=settings.MYSQL_USER,
    password=settings.MYSQL_PASSWORD,
    database=settings.MYSQL_DATABASE,
    charset="utf8mb4",
)
cur = conn.cursor()

cur.execute(
    "INSERT IGNORE INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
    ("admin", "$2b$12$oSup02NPjzn2LRCp/BiAF.lnKDK9ae7RO5l/5RTd.mCQsdJcdMk7y", "admin"),
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
]
for u in units:
    cur.execute(
        "INSERT IGNORE INTO pump_units (id, station_id, unit_name, rated_power_kw, rated_flow) VALUES (%s,%s,%s,%s,%s)",
        u,
    )
for i, flow in enumerate([280, 295, 310], start=1):
    cur.execute(
        "INSERT IGNORE INTO operating_points (id, station_id, flow, head, power, ts) VALUES (%s,%s,%s,%s,%s,NOW())",
        (i, 1, flow, 11.5 + i * 0.1, 320 + i * 10),
    )

conn.commit()
cur.execute("SELECT username, role FROM users")
print("Users:", cur.fetchall())
cur.execute("SELECT id, name FROM pump_stations")
print("Stations:", cur.fetchall())
conn.close()
print("Seed done")
