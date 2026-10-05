#!/usr/bin/env python3
# job6 - read mariadb logs, find failed logins, save them in the database
import paramiko
import re
import mysql.connector
from mysql.connector import Error

ssh_host = "172.16.131.147"
ssh_port = 22
ssh_user = "monitor"
ssh_key = "/root/.ssh/id_ed25519"

db_host = "172.16.131.147"
db_port = 3306
db_user = "psmm_user"
db_pass = "********"
db_name = "psmm"

# matches lines like:
# 2026-10-01 11:55:51 38 [Warning] Access denied for user 'wronguser'@'172.16.131.152'
# (?P<name>...) = named group, so we can do match.group("username") after
log_pattern = re.compile(
    r"(?P<datetime>\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}:\d{2})\s+\d+\s+\[Warning\]\s+"
    r"Access denied for user '(?P<username>[^']+)'@'(?P<ip>[^']+)'"
)


def get_log_content():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(ssh_host, port=ssh_port, username=ssh_user, key_filename=ssh_key)

        # mariadb logs go to journald (no normal file), sudo is passwordless for journalctl
        cmd = "sudo journalctl -u mariadb --no-pager"
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
            found.append({
                "datetime": match.group("datetime"),
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

        # %s = placeholders, safer than building the sql string by hand
        query = """
            INSERT INTO mysql_login_errors (username, attempt_datetime, source_ip)
            VALUES (%s, %s, %s)
        """

        for e in errors:
            cursor.execute(query, (e["username"], e["datetime"], e["ip"]))

        conn.commit()  # without commit nothing is saved
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
