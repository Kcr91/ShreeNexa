# Environment Audit

Audit date: 2026-08-31

Workspace: `F:\ShreeNexa`

Policy: read-only audit; no software or dependencies were installed or updated.

| Area | Command used | Detected version or status | Result | Required next action |
|---|---|---|---|---|
| Workspace | `(Get-Location).Path` | Exactly `F:\ShreeNexa` | Pass | None. |
| Windows | `Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'`; `[System.Environment]::OSVersion.VersionString` | Windows 10 Home 22H2, build 19045.7663, x64 | Pass | None. CIM was unavailable without additional permission, so read-only registry and .NET fallbacks were used. |
| Disk C: | `[System.IO.DriveInfo]::GetDrives()` | 35.03 GB free of 118 GB | Pass | Monitor free space as container images and development tooling are added. |
| Disk F: | `[System.IO.DriveInfo]::GetDrives()` | 126.50 GB free of 200 GB | Pass | None. |
| Python | `python --version` | Python 3.14.5 at `C:\Python314\python.exe` | Pass | None. |
| pip | `python -m pip --version`; `pip --version` | pip 26.2.1 for Python 3.14; executable at `C:\Python314\Scripts\pip.exe` | Pass | None. |
| Node.js | `node --version` | Node.js v24.15.0 at `C:\nvm4w\nodejs\node.exe` | Pass | None. |
| npm | `npm --version`; `npm.cmd --version` | npm 11.12.1; `npm.ps1` is blocked by the current PowerShell execution policy, while `npm.cmd` works | Warning | Use `npm.cmd` in PowerShell or review the execution policy separately before npm-based work. |
| Git | `git --version` | git 2.54.0.windows.1 at `C:\Program Files\Git\cmd\git.exe` | Pass | None. |
| Git identity | `git config --get user.name`; `git config --get user.email` | `Chandresh Khunt`; `chandreshkhunt91@gmail.com` | Pass | None. |
| Docker Desktop | `docker --version`; `Test-Path "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"` | Docker CLI is not on PATH; Docker Desktop executable not found | Blocker | Before container-based local services are required, install Docker Desktop in a separate approved task. Do not install it as part of M0.1. |
| Docker Compose | `docker compose version` | Unavailable because Docker is not installed | Blocker | Install Docker Desktop in a separate approved task if Docker is the selected local-services path. |
| Docker engine | `docker info --format '{{.ServerVersion}}'` | Unavailable because Docker is not installed | Blocker | Start and verify Docker Desktop after a separately approved installation. |
| WSL | `wsl --status`; `wsl --version`; `wsl --list --verbose`; inspect `HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss` | `wsl.exe` is on PATH at `C:\Windows\system32\wsl.exe`; no Linux distribution is registered; this inbox WSL does not support `wsl --version` | Warning | Only if WSL is selected instead of Docker, install and verify a Linux distribution in a separate approved task. |
| Required executables on PATH | `Get-Command python,pip,node,npm,git,docker,wsl` | Python, pip, Node.js, npm, Git, and WSL found; Docker missing | Warning | Resolve the Docker or WSL local-services prerequisite before it is needed. |

## Summary

The core language and source-control tools are available. Docker Desktop and Docker Compose are absent, and WSL has no registered Linux distribution. The approved architecture requires choosing and preparing one local-services path before Postgres and Redis development begins. M0.1 intentionally performs no installation.
