# capulus-ansible

Ansible-Playbooks und Rollen für das Capulus-Homelab: provisioniert die Ubuntu-Hosts, die k3s-Cluster (TECH, PROD, ENTW), die Kiosk-Raspberry-Pis und die Host-Dienste. Die Workloads im Cluster rollt ArgoCD aus [capulus-core](https://github.com/pkr-lab/capulus-core) aus.

## Quickstart

```bash
make deps
make ping
make check
make install
```

`make help` listet alle Targets. Vault-Passwort wird bei jedem Lauf abgefragt (`VAULT_OPTS ?= --ask-vault-pass`).

Abhängigkeiten zu anderen Repos:

| Quelle | Verwendung | Pin |
|---|---|---|
| capulus-core | Quellen des alert-caller (`alert_caller_core_ref`) | Tag plus SHA-256 in `roles/alert_caller/defaults/main.yml` |
| capulus-core | Root-CA | Kopie in `files/homeserver-root-ca.pem`, CI vergleicht mit `pki/` in capulus-core |
| capulus-core | `argocd/bootstrap/*` wird aus der Rolle `argocd` erzeugt | `make render-bootstrap CORE_DIR=/pfad/zu/capulus-core` |

## Dokumentation

[pkr-lab-docs / capulus-ansible](https://github.com/pkr-lab/pkr-lab-docs/tree/main/capulus-ansible)

## Lizenz

Siehe [LICENSE](LICENSE).
