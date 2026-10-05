#!/usr/bin/env python3
# job12 - check cpu / ram / disk and send a mail if a limit is passed
# cron runs it every 5 minutes
import paramiko
import smtplib
from email.mime.text import MIMEText

# limits, change them here
cpu_threshold = 70
disk_threshold = 90
ram_threshold = 80

servers = [
    {"name": "FTP", "host": "172.16.131.150"},
    {"name": "Web", "host": "172.16.131.148"},
    {"name": "SQL", "host": "172.16.131.147"},
]

ssh_port = 22
ssh_user = "monitor"
ssh_key = "/root/.ssh/id_ed25519"

smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_user = "your.mail@laplateforme.io"
smtp_pass = "********"
admin_email = "your.mail@laplateforme.io"


def get_stats(host):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, port=ssh_port, username=ssh_user, key_filename=ssh_key)

        stdin, stdout, stderr = client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        cpu = float(stdout.read().decode().strip() or 0)

        stdin, stdout, stderr = client.exec_command("free | grep Mem | awk '{print ($3/$2) * 100.0}'")
        ram = float(stdout.read().decode().strip() or 0)

        stdin, stdout, stderr = client.exec_command("df / | tail -1 | awk '{print $5}' | tr -d '%'")
        disk = float(stdout.read().decode().strip() or 0)

        return {"cpu": cpu, "ram": ram, "disk": disk}

    except Exception as e:
        print(f"ssh fail on {host}:", e)
        return None

    finally:
        client.close()


def check_thresholds(server_name, stats):
    # returns a list of warning messages (empty list = everything ok)
    warnings = []

    if stats["cpu"] > cpu_threshold:
        warnings.append(f"{server_name}: CPU at {stats['cpu']:.1f}% (limit {cpu_threshold}%)")

    if stats["ram"] > ram_threshold:
        warnings.append(f"{server_name}: RAM at {stats['ram']:.1f}% (limit {ram_threshold}%)")

    if stats["disk"] > disk_threshold:
        warnings.append(f"{server_name}: Disk at {stats['disk']:.1f}% (limit {disk_threshold}%)")

    return warnings


def send_alert(warnings):
    body = "Threshold(s) exceeded:\n\n" + "\n".join(warnings)

    msg = MIMEText(body)
    msg["Subject"] = "ALERT - server resource threshold exceeded"
    msg["From"] = smtp_user
    msg["To"] = admin_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, admin_email, msg.as_string())
        print("alert email sent")
    except Exception as e:
        print("email fail:", e)


if __name__ == "__main__":
    all_warnings = []

    for server in servers:
        stats = get_stats(server["host"])
        if stats:
            print(f"{server['name']} -> cpu: {stats['cpu']:.1f}% ram: {stats['ram']:.1f}% disk: {stats['disk']:.1f}%")
            warnings = check_thresholds(server["name"], stats)
            all_warnings.extend(warnings)

    if all_warnings:
        send_alert(all_warnings)
    else:
        print("all servers under thresholds, no email needed")
