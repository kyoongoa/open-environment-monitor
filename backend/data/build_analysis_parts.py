import argparse
import datetime as dt
import math
import os
from collections import defaultdict

import pymysql


GOOD_LEVELS = {"优", "良"}
POLLUTANTS = ["pm25", "pm10", "so2", "no2", "co", "o3"]


PART_TABLES = [
    "part1",
    "part2",
    "part3",
    "part4",
    "part5",
    "part6",
    "part7",
    "part8",
    "part9",
    "part10",
    "part11",
    "part12",
    "part13",
    "part14",
    "part15",
    "part16",
    "part17",
    "part18",
    "part19",
    "part20",
    "part21",
    "part22",
    "part23",
    "part24",
    "part25",
]


def load_db_config():
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", ""),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "environment_monitoring"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
    }


def to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value):
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def date_to_obj(value):
    if value is None:
        return None
    if isinstance(value, dt.date):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    return dt.datetime.strptime(text, "%Y-%m-%d").date()


def weather_base_label(raw_text):
    text = (raw_text or "").strip()
    if not text:
        return "未知"
    return text.split("~")[0]


def avg(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def sample_points(points, max_points):
    if len(points) <= max_points:
        return points
    step = max(1, len(points) // max_points)
    sampled = points[::step]
    if len(sampled) > max_points:
        sampled = sampled[:max_points]
    return sampled


def pearson_corr(xs, ys):
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - x_mean) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - y_mean) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def build_part_rows(pm_rows, weather_rows):
    pm_daily_acc = defaultdict(lambda: defaultdict(list))
    pm_daily_quality = defaultdict(list)
    for row in pm_rows:
        city = (row.get("city") or "").strip()
        record_date = date_to_obj(row.get("record_date"))
        if not city or record_date is None:
            continue

        quality_level = (row.get("quality_level") or "").strip()
        aqi_index_raw = row.get("aqi_index")
        if quality_level.replace(".", "", 1).isdigit() and not str(aqi_index_raw).replace(".", "", 1).isdigit():
            quality_level, aqi_index_raw = str(aqi_index_raw), quality_level

        key = (city, record_date)
        pm_daily_quality[key].append(quality_level)
        pm_daily_acc[key]["aqi_index"].append(to_int(aqi_index_raw))
        pm_daily_acc[key]["pm25"].append(to_float(row.get("pm25")))
        pm_daily_acc[key]["pm10"].append(to_float(row.get("pm10")))
        pm_daily_acc[key]["so2"].append(to_float(row.get("so2")))
        pm_daily_acc[key]["no2"].append(to_float(row.get("no2")))
        pm_daily_acc[key]["co"].append(to_float(row.get("co")))
        pm_daily_acc[key]["o3"].append(to_float(row.get("o3")))

    pm_daily_rows = []
    for key, metrics in pm_daily_acc.items():
        city, record_date = key
        quality_counts = defaultdict(int)
        for q in pm_daily_quality[key]:
            quality_counts[q] += 1
        major_quality = max(quality_counts.items(), key=lambda item: item[1])[0] if quality_counts else "未知"

        daily_item = {
            "city": city,
            "record_date": record_date,
            "quality_level": major_quality,
            "aqi_index": round(avg(metrics["aqi_index"]) or 0, 2),
            "pm25": round(avg(metrics["pm25"]) or 0, 2),
            "pm10": round(avg(metrics["pm10"]) or 0, 2),
            "so2": round(avg(metrics["so2"]) or 0, 2),
            "no2": round(avg(metrics["no2"]) or 0, 2),
            "co": round(avg(metrics["co"]) or 0, 2),
            "o3": round(avg(metrics["o3"]) or 0, 2),
        }
        pm_daily_rows.append(daily_item)

    pm_daily_rows.sort(key=lambda x: (x["record_date"], x["city"]))

    weather_daily = {}
    for row in weather_rows:
        city = (row.get("city") or "").strip()
        record_date = date_to_obj(row.get("record_date"))
        if not city or record_date is None:
            continue
        key = (city, record_date)
        if key not in weather_daily:
            weather_daily[key] = {
                "weather": weather_base_label(row.get("weather")),
                "aqi": to_int(row.get("aqi")),
                "wind_direction": (row.get("wind_direction") or "未知").strip() or "未知",
                "wind_power": (row.get("wind_power") or "未知").strip() or "未知",
                "max_temperature": to_float(row.get("max_temperature")),
                "min_temperature": to_float(row.get("min_temperature")),
            }

    joined_rows = []
    for item in pm_daily_rows:
        key = (item["city"], item["record_date"])
        weather_item = weather_daily.get(key)
        if not weather_item:
            continue
        max_t = weather_item["max_temperature"]
        min_t = weather_item["min_temperature"]
        temp_mid = None
        if max_t is not None and min_t is not None:
            temp_mid = (max_t + min_t) / 2.0

        joined_rows.append(
            {
                "city": item["city"],
                "record_date": item["record_date"],
                "pm25": item["pm25"],
                "aqi_index": item["aqi_index"],
                "weather": weather_item["weather"],
                "aqi_weather": weather_item["aqi"],
                "wind_direction": weather_item["wind_direction"],
                "wind_power": weather_item["wind_power"],
                "temp_mid": temp_mid,
            }
        )

    parts = {}

    # 01
    acc = defaultdict(list)
    for r in pm_daily_rows:
        acc[r["city"]].append(r["aqi_index"])
    parts["part1"] = [(city, round(avg(vals) or 0, 2)) for city, vals in sorted(acc.items())]

    # 02
    acc = defaultdict(list)
    for r in pm_daily_rows:
        acc[r["city"]].append(r["pm25"])
    parts["part2"] = [(city, round(avg(vals) or 0, 2)) for city, vals in sorted(acc.items())]

    # 03
    city_total = defaultdict(int)
    city_level = defaultdict(int)
    for r in pm_daily_rows:
        city_total[r["city"]] += 1
        city_level[(r["city"], r["quality_level"])] += 1
    rows = []
    for (city, level), cnt in sorted(city_level.items()):
        ratio = (cnt / city_total[city] * 100.0) if city_total[city] else 0.0
        rows.append((f"{city}|{level}", round(ratio, 2)))
    parts["part3"] = rows

    # 04
    acc = defaultdict(int)
    for r in pm_daily_rows:
        if r["quality_level"] not in GOOD_LEVELS:
            acc[r["city"]] += 1
    parts["part4"] = [(city, value) for city, value in sorted(acc.items())]

    # 05
    acc = defaultdict(list)
    for r in pm_daily_rows:
        ym = r["record_date"].strftime("%Y-%m")
        acc[(r["city"], ym)].append(r["pm25"])
    rows = []
    for (city, ym), vals in sorted(acc.items(), key=lambda x: (x[0][0], x[0][1])):
        rows.append((f"{city}|{ym}", round(avg(vals) or 0, 2)))
    parts["part5"] = rows

    # 06
    parts["part6"] = [
        (f"{r['city']}|{r['record_date'].isoformat()}", round(r["aqi_index"] or 0, 2)) for r in pm_daily_rows
    ]

    # 07
    parts["part7"] = [
        (f"{r['city']}|{r['record_date'].isoformat()}", round(r["pm25"] or 0, 2)) for r in pm_daily_rows
    ]

    # 08
    acc = defaultdict(list)
    for r in pm_daily_rows:
        acc[r["record_date"].year].append(r["aqi_index"])
    parts["part8"] = [
        (str(year), round(avg(values) or 0, 2)) for year, values in sorted(acc.items())
    ]

    # 09
    acc = defaultdict(list)
    for r in pm_daily_rows:
        acc[r["record_date"].year].append(r["pm25"])
    parts["part9"] = [
        (str(year), round(avg(values) or 0, 2)) for year, values in sorted(acc.items())
    ]

    # 10
    year_total = defaultdict(int)
    year_good = defaultdict(int)
    for r in pm_daily_rows:
        year = r["record_date"].year
        year_total[year] += 1
        if r["quality_level"] in GOOD_LEVELS:
            year_good[year] += 1
    rows = []
    for year in sorted(year_total.keys()):
        ratio = year_good[year] / year_total[year] * 100.0 if year_total[year] else 0.0
        rows.append((str(year), round(ratio, 2)))
    parts["part10"] = rows

    # 11
    acc = defaultdict(list)
    for r in pm_daily_rows:
        acc[r["record_date"].month].append(r["aqi_index"])
    parts["part11"] = [
        (f"{month:02d}", round(avg(values) or 0, 2)) for month, values in sorted(acc.items())
    ]

    # 12
    acc = defaultdict(list)
    for r in pm_daily_rows:
        acc[r["record_date"].month].append(r["pm25"])
    parts["part12"] = [
        (f"{month:02d}", round(avg(values) or 0, 2)) for month, values in sorted(acc.items())
    ]

    # 13
    acc = defaultdict(list)
    for r in pm_daily_rows:
        quarter = (r["record_date"].month - 1) // 3 + 1
        acc[quarter].append(r["aqi_index"])
    parts["part13"] = [
        (f"Q{quarter}", round(avg(values) or 0, 2)) for quarter, values in sorted(acc.items())
    ]

    # 14
    acc = defaultdict(list)
    for r in pm_daily_rows:
        quarter = (r["record_date"].month - 1) // 3 + 1
        acc[quarter].append(r["pm25"])
    parts["part14"] = [
        (f"Q{quarter}", round(avg(values) or 0, 2)) for quarter, values in sorted(acc.items())
    ]

    # 15
    acc = defaultdict(list)
    for r in pm_daily_rows:
        month = f"{r['record_date'].month:02d}"
        for pollutant in POLLUTANTS:
            acc[(pollutant.upper(), month)].append(r[pollutant])
    rows = []
    for key, values in sorted(acc.items(), key=lambda x: (x[0][0], x[0][1])):
        pollutant, month = key
        rows.append((f"{pollutant}|{month}", round(avg(values) or 0, 3)))
    parts["part15"] = rows

    # 16
    acc = defaultdict(list)
    for r in joined_rows:
        acc[r["weather"]].append(r["pm25"])
    parts["part16"] = [
        (weather, round(avg(values) or 0, 2)) for weather, values in sorted(acc.items())
    ]

    # 17
    acc = defaultdict(list)
    for r in joined_rows:
        if r["aqi_weather"] is not None:
            acc[r["weather"]].append(r["aqi_weather"])
    parts["part17"] = [
        (weather, round(avg(values) or 0, 2)) for weather, values in sorted(acc.items())
    ]

    # 18
    acc = defaultdict(list)
    for r in joined_rows:
        acc[r["wind_direction"]].append(r["pm25"])
    parts["part18"] = [
        (wind_direction, round(avg(values) or 0, 2)) for wind_direction, values in sorted(acc.items())
    ]

    # 19
    acc = defaultdict(list)
    for r in joined_rows:
        acc[r["wind_power"]].append(r["pm25"])
    parts["part19"] = [
        (wind_power, round(avg(values) or 0, 2)) for wind_power, values in sorted(acc.items())
    ]

    # 20
    points = []
    for r in joined_rows:
        if r["temp_mid"] is None or r["pm25"] is None:
            continue
        points.append((round(r["temp_mid"], 1), round(r["pm25"], 2)))
    points.sort(key=lambda x: x[0])
    points = sample_points(points, 1200)
    parts["part20"] = [(str(x), y) for x, y in points]

    # 21
    acc = defaultdict(list)
    for r in pm_daily_rows:
        ym = r["record_date"].strftime("%Y-%m")
        for pollutant in POLLUTANTS:
            acc[(pollutant.upper(), ym)].append(r[pollutant])
    rows = []
    for key, values in sorted(acc.items(), key=lambda x: (x[0][0], x[0][1])):
        pollutant, ym = key
        rows.append((f"{pollutant}|{ym}", round(avg(values) or 0, 3)))
    parts["part21"] = rows

    # 22
    corr_rows = []
    for p1 in POLLUTANTS:
        for p2 in POLLUTANTS:
            xs = []
            ys = []
            for r in pm_daily_rows:
                v1 = r[p1]
                v2 = r[p2]
                if v1 is None or v2 is None:
                    continue
                xs.append(float(v1))
                ys.append(float(v2))
            corr_rows.append((f"{p1.upper()}|{p2.upper()}", round(pearson_corr(xs, ys), 4)))
    parts["part22"] = corr_rows

    # 23
    points = [(r["pm25"], r["pm10"]) for r in pm_daily_rows if r["pm25"] is not None and r["pm10"] is not None]
    points.sort(key=lambda x: x[0])
    points = sample_points(points, 1600)
    parts["part23"] = [(str(round(x, 3)), round(y, 3)) for x, y in points]

    # 24
    points = [(r["pm25"], r["no2"]) for r in pm_daily_rows if r["pm25"] is not None and r["no2"] is not None]
    points.sort(key=lambda x: x[0])
    points = sample_points(points, 1600)
    parts["part24"] = [(str(round(x, 3)), round(y, 3)) for x, y in points]

    # 25
    points = [(r["pm25"], r["o3"]) for r in pm_daily_rows if r["pm25"] is not None and r["o3"] is not None]
    points.sort(key=lambda x: x[0])
    points = sample_points(points, 1600)
    parts["part25"] = [(str(round(x, 3)), round(y, 3)) for x, y in points]

    return parts


def create_part_table(cursor, table_name):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(255) NOT NULL,
            `value` DOUBLE NULL,
            PRIMARY KEY (`id`),
            KEY `idx_name` (`name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    cursor.execute(f"TRUNCATE TABLE `{table_name}`")


def bulk_insert(cursor, table_name, rows):
    if not rows:
        return 0
    sql = f"INSERT INTO `{table_name}` (`name`, `value`) VALUES (%s, %s)"
    cursor.executemany(sql, rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="根据 pm25_data 和 weather_data 生成 25 张分析 part 表")
    parser.parse_args()

    conn = pymysql.connect(**load_db_config())
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT record_date, quality_level, aqi_index, pm25, pm10, so2, no2, co, o3, city
                FROM pm25_data
                """
            )
            pm_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT record_date, weather, wind_direction, wind_power, aqi, max_temperature, min_temperature, city
                FROM weather_data
                """
            )
            weather_rows = cursor.fetchall()

            parts = build_part_rows(pm_rows, weather_rows)
            for table_name in PART_TABLES:
                create_part_table(cursor, table_name)
                inserted = bulk_insert(cursor, table_name, parts.get(table_name, []))
                print(f"{table_name}: {inserted} rows")

        conn.commit()
        print("25 张 part 表构建完成。")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
