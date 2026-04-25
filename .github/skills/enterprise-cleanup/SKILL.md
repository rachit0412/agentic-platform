---
name: enterprise-cleanup
description: Clean up Docker resources unused files prune containers volumes images temporary data cache optimization disk space
argument-hint: "[docker|files|all] - clean up Docker resources, temp files, or everything"
---

# Enterprise Cleanup

Clean up Docker resources, temporary files, build artifacts, and unused dependencies to keep the project lean and performant.

## When to Use

- When disk space is running low
- After extended development sessions with many container rebuilds
- Before committing to ensure no temp/generated files are tracked
- During periodic maintenance of the development environment
- When Docker builds are slow due to cache bloat

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

### 5. Verify Clean State

After cleanup, verify:

1. **Docker**: Run `docker system df` to confirm reduced usage
2. **Disk**: Check that no large temp files remain with `du -sh */ | sort -rh | head -10`
3. **Git**: Run `git status` to ensure working tree is clean
4. **Services**: Run `docker-compose ps` to verify expected containers are still running

### 6. Generate Cleanup Report

Output a summary:

| Resource          | Before | After | Freed |
| ----------------- | ------ | ----- | ----- |
| Docker images     | —      | —     | —     |
| Docker containers | —      | —     | —     |
| Docker volumes    | —      | —     | —     |
| Python cache      | —      | —     | —     |
| Node modules      | —      | —     | —     |
| Log files         | —      | —     | —     |
| **Total**         | —      | —     | —     |
