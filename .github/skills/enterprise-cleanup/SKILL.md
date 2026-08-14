---
name: enterprise-cleanup
description: Clean up Docker resources unused files prune containers volumes images temporary data cache optimization disk space documentation consolidation script removal
argument-hint: "[docker|files|docs|all] - clean up Docker resources, temp files, redundant docs, or everything"
---

# Enterprise Cleanup

Clean up Docker resources, temporary files, build artifacts, redundant documentation, unused scripts, and unused dependencies to keep the project lean and performant.

## When to Use

- When disk space is running low
- After extended development sessions with many container rebuilds
- Before committing to ensure no temp/generated files are tracked
- During periodic maintenance of the development environment
- When Docker builds are slow due to cache bloat
- When documentation has grown redundant or stale across multiple files
- When scripts reference outdated ports, paths, or are no longer wired into CI

## Procedure

### 1. Docker Resource Cleanup

#### Stop and remove orphaned containers

```bash
docker-compose down --remove-orphans
```

#### Remove stopped containers

```bash
docker container prune -f
```

#### Remove unused images (dangling only — safe)

```bash
docker image prune -f
```

#### Remove unused volumes (WARNING: destroys data)

Only if explicitly requested:

```bash
docker volume prune -f
```

#### Remove unused networks

```bash
docker network prune -f
```

#### Show disk usage summary

```bash
docker system df
```

### 2. Application Temp File Cleanup

#### Remove Python cache files

```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
```

On Windows (PowerShell):

```powershell
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
```

#### Remove Node.js temp files

```bash
find . -name "node_modules" -type d -not -path "./services/ui-console/node_modules" -exec rm -rf {} + 2>/dev/null
```

#### Remove pytest cache

```bash
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
```

#### Remove coverage reports

```bash
rm -rf htmlcov/ .coverage coverage.xml
```

### 3. Git Cleanup

#### Remove untracked files (dry run first)

```bash
git clean -n -d
```

#### Remove merged local branches

```bash
git branch --merged main | grep -v "main" | xargs -r git branch -d
```

#### Optimize git repository

```bash
git gc --prune=now
```

### 4. Log File Cleanup

#### Truncate application log files

```bash
find . -name "*.log" -type f -exec truncate -s 0 {} \;
```

#### Clear Docker container logs

```bash
docker-compose logs --no-log-prefix --tail=0
```

### 5. Documentation Cleanup / Compaction

Identify and consolidate redundant documentation files. Common patterns:

#### Consolidate overlapping docs

If multiple root-level `.md` files cover the same topic (e.g., Codespaces setup), merge them into one canonical file and delete the rest.

Consolidation rules:

- **Codespaces**: `CODESPACES.md` + `CODESPACES_SETUP.md` + `CODESPACES_DEPLOYMENT_CHECKLIST.md` → single `CODESPACES.md`
- **docs/README.md**: If it duplicates the root `README.md`, replace with a short index pointing to `ARCHITECTURE.md`, `GET_STARTED.md`, and root README
- **docs/GET_STARTED.md**: If auto-generated and duplicates root README quick start, remove it (content already in `README.md` and `INSTALL.md`)

#### Remove stale documentation

Delete docs that are:

- One-time migration checklists no longer relevant (e.g., deployment checklist after rollout)
- Auto-generated files whose content is already in the root README
- Sub-directory README files that only repeat root-level content

#### Update cross-references

After removing files, grep for broken links:

```bash
grep -rn "CODESPACES_SETUP\|CODESPACES_DEPLOYMENT\|GET_STARTED\|scripts/README" *.md docs/ .github/
```

On Windows (PowerShell):

```powershell
Get-ChildItem -Recurse -Filter "*.md" | Select-String -Pattern "CODESPACES_SETUP|CODESPACES_DEPLOYMENT|GET_STARTED|scripts/README"
```

### 6. Script Cleanup

Identify and remove scripts that are:

- **Stale**: Reference outdated ports, paths, or services that no longer match `docker-compose.yml`
- **Orphaned**: Not referenced by CI workflows (`.github/workflows/`), VS Code tasks (`.vscode/tasks.json`), or documentation
- **Redundant**: Duplicate functionality already provided by VS Code tasks or docker-compose commands

#### Checklist

1. Compare script ports/URLs against `docker-compose.yml` service definitions
2. Search CI workflows for script references: `grep -r "scripts/" .github/workflows/`
3. Search VS Code tasks: `grep -r "scripts/" .vscode/tasks.json`
4. Remove scripts that fail all three checks (not in CI, not in tasks, uses wrong ports)
5. Keep `scripts/` directory README only if it documents actively-used scripts

### 7. Verify Clean State

After cleanup, verify:

1. **Docker**: Run `docker system df` to confirm reduced usage
2. **Disk**: Check that no large temp files remain with `du -sh */ | sort -rh | head -10`
3. **Git**: Run `git status` to ensure working tree is clean
4. **Services**: Run `docker-compose ps` to verify expected containers are still running
5. **Docs**: Confirm no broken internal links with `grep -rn "](.*\.md)" docs/ README.md | grep -v http`
6. **Scripts**: Confirm remaining scripts match current service ports

### 8. Generate Cleanup Report

Output a summary:

| Resource          | Before | After | Freed |
| ----------------- | ------ | ----- | ----- |
| Docker images     | —      | —     | —     |
| Docker containers | —      | —     | —     |
| Docker volumes    | —      | —     | —     |
| Python cache      | —      | —     | —     |
| Node modules      | —      | —     | —     |
| Log files         | —      | —     | —     |
| Docs removed      | —      | —     | —     |
| Scripts removed   | —      | —     | —     |
| **Total**         | —      | —     | —     |
