#!/usr/bin/env python3
# job15 - post the status of the servers in a google chat space (webhook)
import paramiko
import requests
import json
from datetime import datetime

# webhook url of the space (Apps & integrations > Webhooks), keep it secret!
webhook_url = "https://chat.googleapis.com/v1/spaces/XXXX/messages?key=XXXX&token=XXXX"

servers = [
    {"name": "FTP", "host": "172.16.131.150"},
    {"name": "Web", "host": "172.16.131.148"},
    {"name": "SQL", "host": "172.16.131.147"},
]

ssh_port = 22
ssh_user = "monitor"
ssh_key = "/root/.ssh/id_ed25519"


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


def build_message():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"*Server status report - {now}*\n"]  # *text* = bold in google chat

    for server in servers:
        stats = get_stats(server["host"])
        if stats:
            lines.append(
                f"*{server['name']}*: CPU {stats['cpu']:.1f}% | RAM {stats['ram']:.1f}% | Disk {stats['disk']:.1f}%"
            )
        else:
            lines.append(f"*{server['name']}*: unreachable")

    return "\n".join(lines)


def send_message(text):
    payload = {"text": text}  # google chat wants a json with a "text" key

    try:
        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            data=json.dumps(payload)
        )
        print("status:", response.status_code)  # 200 = message posted
    except Exception as e:
        print("send fail:", e)


if __name__ == "__main__":
    message = build_message()
    print(message)
    send_message(message)
