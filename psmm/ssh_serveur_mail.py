#!/usr/bin/env python3
# job9 - send the admin a mail with the failed logins of yesterday
import mysql.connector
from mysql.connector import Error
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

db_host = "172.16.131.147"
db_port = 3306
db_user = "psmm_user"
db_pass = "********"
db_name = "psmm"

smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_user = "your.mail@laplateforme.io"
smtp_pass = "********"   # app password from google account, not the normal password
admin_email = "your.mail@laplateforme.io"

# one table per service
tables = {
    "MySQL": "mysql_login_errors",
    "FTP": "ftp_login_errors",
    "Web": "web_login_errors",
}


def get_yesterday_range():
    # yesterday 00:00:00 -> today 00:00:00
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    start = datetime.combine(yesterday, datetime.min.time())
    end = datetime.combine(today, datetime.min.time())
    return start, end


def fetch_errors(table, start, end):
    try:
        conn = mysql.connector.connect(
            host=db_host, port=db_port,
            user=db_user, password=db_pass,
            database=db_name
        )
        cursor = conn.cursor(dictionary=True)  # rows come back as dict

        query = f"""
            SELECT username, attempt_datetime, source_ip
            FROM {table}
            WHERE attempt_datetime >= %s AND attempt_datetime < %s
            ORDER BY attempt_datetime ASC
        """
        cursor.execute(query, (start, end))
        return cursor.fetchall()

    except Error as e:
        print(f"db fail on {table}:", e)
        return []

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def build_report(start, end):
    lines = [f"daily report {start.date()} to {end.date()}\n"]
    total = 0

    for label, table in tables.items():
        rows = fetch_errors(table, start, end)
        lines.append(f"\n{label}: {len(rows)} failed attempt(s)")
        for r in rows:
            lines.append(f"  {r['attempt_datetime']} | user: {r['username']} | ip: {r['source_ip']}")
        total += len(rows)

    lines.append(f"\ntotal: {total}")
    return "\n".join(lines)


def send_email(body):
    msg = MIMEText(body)
    msg["Subject"] = f"Daily Login Report - {datetime.now().date()}"
    msg["From"] = smtp_user
    msg["To"] = admin_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()   # encrypt the connection
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, admin_email, msg.as_string())
        print("email sent")
    except Exception as e:
        print("email fail:", e)


if __name__ == "__main__":
    start, end = get_yesterday_range()
    report = build_report(start, end)
    print(report)
    send_email(report)
