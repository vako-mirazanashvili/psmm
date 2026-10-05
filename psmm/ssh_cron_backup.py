#!/usr/bin/env python3
# job10 - local backup of the database, keep only the 7 last ones
# cron runs it every 3 hours
import subprocess
from datetime import datetime
import os
import glob

db_host = "172.16.131.147"
db_user = "psmm_user"
db_pass = "********"
db_name = "psmm"

backup_dir = "/root/backups"
keep_count = 7  # how many backups we keep


def make_backup():
    now = datetime.now().strftime("%Y%m%d_%H%M%S")  # timestamp in the file name
    filename = f"{backup_dir}/psmm_backup_{now}.sql"

    # mysqldump writes all the sql needed to rebuild the database
    cmd = [
        "mysqldump",
        "-h", db_host,
        "-u", db_user,
        f"-p{db_pass}",
        db_name
    ]

    try:
        with open(filename, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)

        if result.returncode == 0:
            print(f"backup saved: {filename}")
        else:
            print("backup failed:", result.stderr.decode())

    except Exception as e:
        print("error making backup:", e)


def cleanup_old_backups():
    # names contain the date, so sorted = oldest first
    files = sorted(glob.glob(f"{backup_dir}/psmm_backup_*.sql"))

    if len(files) > keep_count:
        to_delete = files[:len(files) - keep_count]
        for f in to_delete:
            os.remove(f)
            print(f"deleted old backup: {f}")


if __name__ == "__main__":
    make_backup()
    cleanup_old_backups()
