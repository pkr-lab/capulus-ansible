# CLAUDE.md — Arbeitsregeln für capulus-ansible

Ansible-Playbooks und Rollen für das Capulus-Homelab: provisioniert die Ubuntu-Hosts, die k3s-Cluster (TECH, PROD, ENTW), die Kiosk-Raspberry-Pis und die Host-Dienste. Die Workloads rollt ArgoCD aus [capulus-core](https://github.com/pkr-lab/capulus-core) aus. Sprache im Repo ist **Deutsch** (Docs, Commit-Beschreibungen, PR-Texte). Regeln wie in capulus-core.

---

## Harte Regeln

- **Keine neuen Kommentare im Code.** Gilt für YAML, Jinja-Templates, Shell und Makefile. Bestehende Kommentare bleiben, bis die Stelle ohnehin überarbeitet wird; dann die Begründung ins Doc verschieben. Einzige Ausnahme: der Versions-Kommentar `# vX.Y.Z` hinter der Commit-SHA in `uses:`-Zeilen der Workflows (Renovate und Dependabot lesen ihn).
- **Doku liegt nicht in diesem Repo, sondern in [pkr-lab-docs](https://github.com/pkr-lab/pkr-lab-docs)** unter `capulus/capulus-ansible/`. Jede Codeänderung bekommt dort einen PR: Rollen-Doc unter `rollen/<rolle>.md`, Hintergründe (warum) unter `6-hintergruende/` (Rollen: `60020-ansible-rollen.md`). Konventionen stehen in der `CLAUDE.md` von pkr-lab-docs.
- **Vor dem Ändern einer Rolle das Rollen-Doc und den Hintergrund-Eintrag lesen.** Die meisten Eigenheiten existieren, weil der naheliegende Ansatz schon einmal gescheitert ist.
- **Vault-Dateien nie anfassen:** `group_vars/all.yml` und `group_vars/user_inventory_vault.yml` sind mit ansible-vault verschlüsselt. Nie entschlüsseln, ausgeben oder neu anlegen. Änderungen daran macht der Nutzer selbst (`make vault-edit`, `make user-inventory-edit`).
- **Niemals Klartext-Secrets committen.** Neue Geheimnisse gehören in den Vault. gitleaks läuft in der CI (`.gitleaks.toml`).
- **Nie direkt auf `main` arbeiten.** `main` ist geschützt, Änderungen gehen nur per PR hinein. Steht das Arbeitsverzeichnis auf `main`, vor der ersten Änderung einen neuen Branch anlegen (`git switch -c <typ>/<kurzbeschreibung>`, z. B. `feat/backup-retention`, `fix/ca-pin`) und nur dort arbeiten. Den Branch legt Claude an, Commit, Push und PR macht der Nutzer.
- `argocd/bootstrap/*` in capulus-core wird aus der Rolle `argocd` **generiert** (`make render-bootstrap CORE_DIR=<Pfad zu capulus-core>`). Dort nie von Hand ändern, sondern hier Template oder Defaults der Rolle anpassen und neu rendern (im Container meist nicht möglich → dem Nutzer sagen).

---

## Wo was liegt

| Pfad | Inhalt |
|---|---|
| `site.yml` | Hauptplaybook für den `homeserver` (TECH) |
| `worker-0.yml`, `worker-1.yml` | k3s-Agents und Watchdogs der Worker |
| `prod.yml`, `entw.yml` | PROD- und ENTW-Cluster in den KVM-VMs |
| `alarm-kiosks.yml`, `banana-pi-kiosks.yml`, `xibo-kiosks.yml` | Kiosk-Raspberry-Pis |
| `alert-caller.yml` | Telefon-Alarmierung (externe VM und Vereinsheim-Pi) |
| `render-bootstrap.yml` | erzeugt `argocd/bootstrap/` in capulus-core |
| `vaultwarden-restore.yml` | Wiederherstellung von Vaultwarden |
| `roles/<rolle>/` | `defaults/`, `tasks/`, `templates/`; Tags entsprechen dem Rollennamen mit Bindestrich |
| `inventory/hosts.yml`, `group_vars/`, `host_vars/` | Hosts und Variablen |
| `files/homeserver-root-ca.pem` | Kopie der Root-CA, Quelle der Wahrheit ist `pki/` in capulus-core |
| `requirements.yml` | Galaxy-Collections |

Abhängigkeiten zu capulus-core: die Quellen des alert-caller sind mit Tag und SHA-256 in `roles/alert_caller/defaults/main.yml` gepinnt (`alert_caller_core_ref`); wer den Tag erhöht, muss die Prüfsumme mit erneuern.

---

## Prüfen vor dem Commit

Die CI (`.github/workflows/ci.yml`) hat drei Pflicht-Jobs: `make lint`, Root-CA-Vergleich mit capulus-core, gitleaks.

```bash
pip install -q yamllint ansible-lint
make deps
make lint
cmp files/homeserver-root-ca.pem <(curl -fsSL https://raw.githubusercontent.com/pkr-lab/capulus-core/main/pki/homeserver-root-ca.pem)
```

- `ansible-playbook` gegen echte Hosts (`make check`, `make install`, `make <rolle>`) fragt das Vault-Passwort ab und erreicht das LAN nicht aus der Sandbox. Solche Schritte als Befehl für den Nutzer formulieren statt sie zu versuchen.
- Nur die betroffenen Teile prüfen. Bei Rollenänderungen den passenden Dry-Run-Befehl (`make <ziel>-check` bzw. `--tags <rolle> --check --diff`) vorschlagen.

---

## Code-Stil

- Ansible-Task-Namen deutsch und kleingeschrieben („ethtool installieren“), FQCN-Module (`ansible.builtin.…`).
- Variablen einer Rolle liegen in `roles/<rolle>/defaults/main.yml`, nicht verteilt in Tasks.
- YAML-Dateien enden mit genau einem Zeilenumbruch, keine Leerzeile am Ende (yamllint `empty-lines`).
- Neue Make-Targets bekommen eine `##`-Beschreibung (`make help` listet sie).
- `.ansible-lint` und `.yamllint` bestimmen den Rest; keine neuen Einträge in `skip_list`, ohne es dem Nutzer zu sagen.

---

## Commits und PRs

- **Claude committet und pusht nicht.** Commits, Pushes und PRs macht ausschließlich der Nutzer. Änderungen nur im Arbeitsverzeichnis vorbereiten, am Ende kurz zusammenfassen und einen passenden Commit-Text vorschlagen. Ausnahme nur, wenn der Nutzer es in der jeweiligen Anfrage ausdrücklich verlangt.
- Conventional Commits mit Scope = Rolle/Bereich, Beschreibung auf Deutsch: `feat(k3s): …`, `fix(common): …`, `docs(…): …`. Typen: feat fix docs chore refactor test ci build perf style revert.
  `feat`/`fix` lösen über semantic-release ein Release aus (zentraler Workflow in `pkr-lab/.github`, CHANGELOG.md und Tag `vX.Y.Z`). Der Commitlint-Check läuft auf PRs; lokal prüft `git config core.hooksPath .githooks` das Format.
- Ein PR = eine Änderung inkl. zugehöriger Doku. Renovate-PRs nicht manuell nachbauen.
