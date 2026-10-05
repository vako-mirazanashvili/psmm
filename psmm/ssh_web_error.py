#!/usr/bin/env python3
# job8 - same idea for the web server (nginx access.log, status 401 = bad login)
import paramiko
import re
import mysql.connector
from mysql.connector import Error
from datetime import datetime

ssh_host = "172.16.131.148"   # web server
ssh_port = 22
ssh_user = "monitor"
ssh_key = "/root/.ssh/id_ed25519"
log_path = "/var/log/nginx/access.log"

db_host = "172.16.131.147"
db_port = 3306
db_user = "psmm_user"
db_pass = "********"
db_name = "psmm"

# matches lines like:
# 172.16.131.152 - wronguser [01/Oct/2026:13:01:32 +0200] "GET / HTTP/1.1" 401 172 "-" "curl/8.14.1"
log_pattern = re.compile(
    r"(?P<ip>[\d.]+)\s+-\s+(?P<username>\S+)\s+"
    r"\[(?P<datetime>\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})\s+\S+\]\s+"
    r'".*?"\s+401\s+'
)


def get_log_content():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(ssh_host, port=ssh_port, username=ssh_user, key_filename=ssh_key)

        cmd = f"sudo cat {log_path}"
        stdin, stdout, stderr = client.exec_command(cmd)

        content = stdout.read().decode()
        err = stderr.read().decode()

        if err:
            print("warning:", err)

        return content

    except Exception as e:
        print("ssh fail:", e)
        return None

    finally:
        client.close()


def parse_errors(log_content):
    found = []

    for line in log_content.splitlines():
        match = log_pattern.search(line)
        if match:
            # nginx date (01/Oct/2026:13:01:32) is not a mysql date, so we convert it
            raw_dt = match.group("datetime")
            parsed_dt = datetime.strptime(raw_dt, "%d/%b/%Y:%H:%M:%S")
            mysql_dt = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")

            found.append({
                "datetime": mysql_dt,
                "username": match.group("username"),
                "ip": match.group("ip")
            })

    return found


def save_to_db(errors):
    if not errors:
        print("nothing found, skip db insert")
        return

    try:
        conn = mysql.connector.connect(
            host=db_host, port=db_port,
            user=db_user, password=db_pass,
            database=db_name
        )
        cursor = conn.cursor()

        query = """
            INSERT INTO web_login_errors (username, attempt_datetime, source_ip)
            VALUES (%s, %s, %s)
        """

        for e in errors:
            cursor.execute(query, (e["username"], e["datetime"], e["ip"]))

        conn.commit()
        print(f"inserted {len(errors)} rows")

    except Error as e:
        print("db fail:", e)

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    content = get_log_content()

    if content:
        errors = parse_errors(content)
        print(f"found {len(errors)} failed login lines")
        save_to_db(errors)
