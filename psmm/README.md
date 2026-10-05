# PSMM - Python, Shell, MariaDB, Mail

Projet "Rapport du Commandeur Data" (La Plateforme_) : centraliser les erreurs de connexion
des serveurs FTP, Web et SQL dans une base MariaDB, avec alertes par mail et Google Chat.

Le rapport complet (walkthrough, commandes, résultats) est dans `Rapport_PSMM.docx`.

## Architecture

| Machine | Rôle | IP |
|---|---|---|
| VM de contrôle | lance tous les scripts | 172.16.131.152 |
| VM FTP (ProFTPD) | serveur FTP | 172.16.131.150 |
| VM Web (Nginx) | site avec auth basic | 172.16.131.148 |
| VM SQL (MariaDB) | base `psmm` | 172.16.131.147 |

## Scripts

| Job | Fichier | Rôle |
|---|---|---|
| 03 | `ssh_login.py` | connexion SSH + commande |
| 04 | `ssh_login_sudo.py` | idem avec sudo |
| 05 | `ssh_mysql.py` | test de connexion MariaDB |
| 06 | `ssh_mysql_error.py` | erreurs de connexion MariaDB -> base |
| 07 | `ssh_ftp_error.py` | erreurs de connexion FTP -> base |
| 08 | `ssh_web_error.py` | erreurs de connexion Web -> base |
| 09 | `ssh_serveur_mail.py` | mail quotidien (tentatives de la veille) |
| 10 | `ssh_cron_backup.py` | sauvegarde toutes les 3h, 7 conservées |
| 11 | `ssh_system_status.py` | RAM / CPU / disque, 72h d'historique |
| 12 | `ssh_system_mail.py` | alerte mail si seuil dépassé (toutes les 5 min) |
| 13 | `ssh_system_mail_limited.py` | idem, max 1 mail par heure |
| 14 | `ssh_update.py` | mises à jour via ALCASAR (**non terminé, non testé**) |
| 15 | `ssh_chat_notify.py` | état des serveurs dans Google Chat |

## Configuration avant de lancer

Les secrets sont remplacés par des valeurs à changer **en local** (ne jamais les commiter) :

- `********` : tous les mots de passe (base de données, sudo, mot de passe d'application du mail, ALCASAR)
- `webhook_url` (`XXXX`) : URL du webhook Google Chat

## Planification (crontab)

```
0 */3 * * * /usr/bin/python3 /root/scripts/ssh_cron_backup.py >> /root/scripts/backup.log 2>&1
*/5 * * * * /usr/bin/python3 /root/scripts/ssh_system_mail_limited.py >> /root/scripts/system_mail.log 2>&1
0 6 * * * /usr/bin/python3 /root/scripts/ssh_serveur_mail.py >> /root/scripts/daily_mail.log 2>&1
```
