# GitHub Codespaces Migration - Deployment Checklist

## ✅ Pre-Deployment

- [ ] Review all configuration files in `.devcontainer/`
- [ ] Update `.env.example` with your organization's defaults
- [ ] Test docker-compose.yml works correctly locally
- [ ] Verify all required ports are documented

## ✅ Repository Setup

- [ ] Commit all Codespaces configuration files
  ```bash
  git add .devcontainer .vscode .github CODESPACES* scripts/
  git commit -m "feat: Add GitHub Codespaces support"
  git push origin main
  ```

- [ ] Update repository README.md with Codespaces badge
- [ ] Add CODESPACES.md to the repository
- [ ] Test the setup by creating a new codespace

## ✅ GitHub Settings

### Enable Prebuilds (Highly Recommended)
- [ ] Go to repository **Settings** → **Codespaces**
- [ ] Click **Set up prebuild**
- [ ] Configure prebuild:
  - Branch: `main` (and `develop` if applicable)
  - Region: Select your primary region
  - Trigger: On push + scheduled
  - Machine type: `8-core` or `16-core`

### Configure Secrets
- [ ] Go to repository **Settings** → **Secrets** → **Codespaces**
- [ ] Add secrets (if applicable):
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `LANGFUSE_SECRET_KEY`
  - `KEYCLOAK_CLIENT_SECRET`
  - Database passwords for production

### Set Policies
- [ ] Go to **Settings** → **Codespaces** → **Policies**
- [ ] Set maximum retention period (default: 30 days)
- [ ] Set idle timeout (recommended: 30 minutes)
- [ ] Configure allowed machine types
- [ ] Set spending limit (if needed)

## ✅ Testing

### Initial Test
- [ ] Create a new codespace from main branch
- [ ] Wait for initial build (3-5 minutes)
- [ ] Verify post-create script runs successfully
- [ ] Check all services start: `docker-compose ps`
- [ ] Run health check: `./scripts/health-check.sh`

### Service Verification
- [ ] Access OpenWebUI (port 3000) - Chat interface works
- [ ] Access LangGraph API (port 8000) - /docs loads
- [ ] Access n8n (port 5678) - Login works
- [ ] Access Grafana (port 3002) - Dashboards load
- [ ] Verify PostgreSQL connection
- [ ] Verify Redis connection
- [ ] Check Ollama models: `docker exec ollama ollama list`

### Development Workflow
- [ ] Edit a Python file in `services/langgraph-api/`
- [ ] Verify hot reload works
- [ ] Run a VS Code task from command palette
- [ ] Test debugging with launch configuration
- [ ] Install a new Python package
- [ ] Restart a service: `docker-compose restart langgraph-api`

## ✅ Prebuild Verification (if enabled)

- [ ] Wait for first prebuild to complete (check Actions tab)
- [ ] Create a new codespace after prebuild
- [ ] Verify startup time is < 1 minute
- [ ] Check prebuild logs for errors
- [ ] Monitor prebuild frequency and adjust if needed

## ✅ Documentation

- [ ] Review and update [CODESPACES.md](CODESPACES.md)
- [ ] Document any custom setup steps
- [ ] Add troubleshooting tips to docs
- [ ] Update team onboarding guide
- [ ] Create video walkthrough (optional)

## ✅ Team Rollout

### Communication
- [ ] Announce Codespaces availability to team
- [ ] Share quick start guide
- [ ] Schedule training session (optional)
- [ ] Create internal wiki/confluence page

### Support
- [ ] Set up support channel (Slack, Teams, etc.)
- [ ] Designate Codespaces champions
- [ ] Create FAQ document
- [ ] Monitor usage and gather feedback

## ✅ Optimization

### Performance
- [ ] Monitor codespace startup times
- [ ] Optimize Docker image layers
- [ ] Review and reduce prebuild frequency if needed
- [ ] Adjust timeout and retention policies based on usage
- [ ] Consider upgrading machine types for heavy workloads

### Cost Management
- [ ] Review Codespaces billing
- [ ] Set up spending limits
- [ ] Monitor usage per user/team
- [ ] Identify and stop idle codespaces
- [ ] Optimize prebuild schedule to reduce costs

### Developer Experience
- [ ] Gather developer feedback
- [ ] Add commonly used VS Code extensions
- [ ] Create custom tasks for frequent operations
- [ ] Document best practices
- [ ] Share productivity tips

## ✅ Advanced Configuration (Optional)

- [ ] Configure custom domain for port forwarding
- [ ] Set up VPN/private network access
- [ ] Integrate with SSO/SAML
- [ ] Add custom dotfiles repository
- [ ] Configure organization-wide prebuilds
- [ ] Set up multi-repo workspaces

## ✅ Monitoring & Maintenance

### Regular Checks
- [ ] Weekly: Review prebuild success rate
- [ ] Weekly: Check for failed codespace creates
- [ ] Monthly: Review usage and costs
- [ ] Monthly: Update dependencies in devcontainer
- [ ] Quarterly: Review and update documentation

### Alerts
- [ ] Set up alerts for prebuild failures
- [ ] Monitor codespace creation failures
- [ ] Track spending approaching limits
- [ ] Alert on unusually long startup times

## 🎉 Post-Deployment

- [ ] Celebrate successful migration! 🎊
- [ ] Collect team feedback after 1 week
- [ ] Iterate on configuration based on usage
- [ ] Document lessons learned
- [ ] Share success story with organization

---

## 📊 Success Metrics

Track these metrics to measure success:

- **Onboarding Time**: Time for new developer to be productive
- **Startup Time**: Time from codespace create to ready
- **Developer Satisfaction**: Survey score (1-10)
- **Usage Rate**: % of team using Codespaces
- **Cost per Developer**: Monthly spending per active user
- **Support Tickets**: Number of Codespaces-related issues

---

## 🆘 Rollback Plan

If issues arise:

1. **Immediate**: Keep local development option available
2. **Communication**: Notify team of known issues
3. **Documentation**: Update troubleshooting guide
4. **Fix Forward**: Iterate on configuration
5. **Last Resort**: Disable Codespaces, return to local dev

---

**Questions or issues? Open an issue on GitHub or contact the DevOps team.**
