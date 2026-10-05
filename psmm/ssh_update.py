#!/usr/bin/env python3
# job14 - NOT FINISHED / NOT TESTED (see the report)
# idea: login to alcasar -> apt update/upgrade on the 3 servers
#       -> mail if a reboot is needed -> logout from alcasar
import re
import hashlib
import requests
import paramiko
import smtplib
from email.mime.text import MIMEText

alcasar_host = "alcasar.laplateforme.io"
alcasar_port = 3991
alcasar_user = "your.mail@laplateforme.io"
alcasar_pass = "********"
ident = "00"   # same value as chilliController.ident in ChilliLibrary.js
base_url = f"https://{alcasar_host}:{alcasar_port}/json/"

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


def alcasar_login():
    # returns (session, logged_in_by_us) or (None, False) if it fails
    session = requests.Session()

    try:
        # 1) ask the status, alcasar gives a challenge if we are not logged in
        r = session.get(base_url + "status", params={"callback": "x"})

        # clientState 1 = already authenticated (this is what we got with the NAT network)
        if '"clientState":1' in r.text:
            print("already authenticated, no login needed")
            return session, False

        m = re.search(r'"challenge":"([0-9a-fA-F]+)"', r.text)
        if not m:
            print("no challenge found in the answer:", r.text[:200])
            return None, False
        challenge = m.group(1)

        # 2) same calculation as the javascript (CHAP):
        #    md5( ident + password in hex + challenge )
        data = bytes.fromhex(ident + alcasar_pass.encode().hex() + challenge)
        response = hashlib.md5(data).hexdigest()

        # 3) send the login with username + response (the password is never sent)
        r = session.get(base_url + "logon", params={
            "username": alcasar_user,
            "response": response,
            "callback": "x"
        })

        if '"clientState":1' in r.text:
            print("alcasar login ok")
            return session, True

        print("alcasar login failed:", r.text[:200])
        return None, False

    except Exception as e:
        print("alcasar connect fail:", e)
        return None, False


def alcasar_logout(session):
    try:
        session.get(base_url + "logoff", params={"callback": "x"})
        print("disconnected from alcasar")
    except Exception as e:
        print("alcasar disconnect fail:", e)


def update_server(host):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, port=ssh_port, username=ssh_user, key_filename=ssh_key)

        stdin, stdout, stderr = client.exec_command("sudo apt update")
        stdout.read()  # wait until it is finished

        stdin, stdout, stderr = client.exec_command("sudo apt upgrade -y")
        output = stdout.read().decode()
        print(output[-300:])  # only the end, the full output is huge

        # debian creates this file when a reboot is needed
        stdin, stdout, stderr = client.exec_command("test -f /var/run/reboot-required && echo YES || echo NO")
        reboot_needed = stdout.read().decode().strip()

        return reboot_needed == "YES"

    except Exception as e:
        print(f"update fail on {host}:", e)
        return False

    finally:
        client.close()


def send_reboot_alert(servers_needing_reboot):
    body = "These servers need a reboot after updates:\n\n" + "\n".join(servers_needing_reboot)

    msg = MIMEText(body)
    msg["Subject"] = "ALERT - servers need reboot after update"
    msg["From"] = smtp_user
    msg["To"] = admin_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, admin_email, msg.as_string())
        print("reboot alert email sent")
    except Exception as e:
        print("email fail:", e)


if __name__ == "__main__":
    session, logged_in_by_us = alcasar_login()

    if session:
        servers_needing_reboot = []

        for server in servers:
            print(f"updating {server['name']}...")
            if update_server(server["host"]):
                servers_needing_reboot.append(server["name"])

        if servers_needing_reboot:
            send_reboot_alert(servers_needing_reboot)
        else:
            print("no reboots needed")

        # logout only if we did the login ourselves
        if logged_in_by_us:
            alcasar_logout(session)
    else:
        print("could not connect to alcasar, skipping updates")
