#!/usr/bin/env python3
# job11 - get cpu / ram / disk of each server, save in the database, keep 72h
import paramiko
import mysql.connector
from mysql.connector import Error

servers = [
    {"name": "FTP", "host": "172.16.131.150"},
    {"name": "Web", "host": "172.16.131.148"},
    {"name": "SQL", "host": "172.16.131.147"},
]

ssh_port = 22
ssh_user = "monitor"
ssh_key = "/root/.ssh/id_ed25519"

db_host = "172.16.131.147"
db_port = 3306
db_user = "psmm_user"
db_pass = "********"
db_name = "psmm"

retention_hours = 72


def get_stats(host):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, port=ssh_port, username=ssh_user, key_filename=ssh_key)

        # cpu: user% + system% from top
        stdin, stdout, stderr = client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        cpu = float(stdout.read().decode().strip() or 0)

        # ram: used / total * 100
        stdin, stdout, stderr = client.exec_command("free | grep Mem | awk '{print ($3/$2) * 100.0}'")
        ram = float(stdout.read().decode().strip() or 0)

        # disk: percent used of /, we remove the % sign
        stdin, stdout, stderr = client.exec_command("df / | tail -1 | awk '{print $5}' | tr -d '%'")
        disk = float(stdout.read().decode().strip() or 0)

        return {"cpu": cpu, "ram": ram, "disk": disk}

    except Exception as e:
        print(f"ssh fail on {host}:", e)
        return None

    finally:
        client.close()


def save_stats(server_name, stats):
    try:
        conn = mysql.connector.connect(
            host=db_host, port=db_port,
            user=db_user, password=db_pass,
            database=db_name
        )
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO system_status (server_name, cpu_usage, ram_usage, disk_usage) VALUES (%s, %s, %s, %s)",
            (server_name, stats["cpu"], stats["ram"], stats["disk"])
        )
        conn.commit()
        print(f"saved stats for {server_name}")

    except Error as e:
        print("db fail:", e)

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def cleanup_old():
    # delete rows older than 72h
    try:
        conn = mysql.connector.connect(
            host=db_host, port=db_port,
            user=db_user, password=db_pass,
            database=db_name
        )
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM system_status WHERE recorded_at < NOW() - INTERVAL %s HOUR",
            (retention_hours,)
        )
        conn.commit()
        print(f"cleaned up {cursor.rowcount} old row(s)")

    except Error as e:
        print("cleanup fail:", e)

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    for server in servers:
        stats = get_stats(server["host"])
        if stats:
            print(f"{server['name']} -> cpu: {stats['cpu']:.1f}% ram: {stats['ram']:.1f}% disk: {stats['disk']:.1f}%")
            save_stats(server["name"], stats)

    cleanup_old()
