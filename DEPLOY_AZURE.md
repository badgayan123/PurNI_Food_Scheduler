# Deploy PurNi Menu to Azure App Service

## Prerequisites

- [Azure account](https://azure.microsoft.com/free/)
- GitHub repo: `https://github.com/badgayan123/PurNI_Food_Scheduler`

---

## Step 1: Create Azure App Service

1. Go to [portal.azure.com](https://portal.azure.com)
2. Click **Create a resource** → search **Web App** → **Create**
3. Fill in:
   - **Subscription:** Your subscription
   - **Resource Group:** Create new (e.g. `purni-menu-rg`)
   - **Name:** `purni-menu` (or any unique name; becomes `purni-menu.azurewebsites.net`)
   - **Publish:** Code
   - **Runtime stack:** Python 3.11
   - **Operating System:** Linux
   - **Region:** Choose nearest (e.g. East US)
   - **Pricing plan:** **Free F1** (or create new → Free tier)
4. Click **Review + create** → **Create**

---

## Step 2: Configure Startup Command

1. Go to your App Service → **Configuration** → **Stack settings**
2. Scroll to **Startup Command**
3. Set it to:
   ```
   gunicorn backend.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
4. Click **Save**

---

## Step 3: Connect GitHub and Deploy

1. In your App Service → **Deployment Center**
2. **Source:** GitHub
3. Authorize Azure with GitHub if prompted
4. Select:
   - **Organization:** your GitHub username
   - **Repository:** `PurNI_Food_Scheduler`
   - **Branch:** `main`
5. **Build Provider:** GitHub Actions (recommended)
6. Click **Save**

Azure creates a workflow file and pushes it to your repo. The first deployment runs automatically.

---

## Step 4: Enable SCM_DO_BUILD (if needed)

If the app fails to start (missing modules):

1. Go to **Configuration** → **Application settings**
2. Add:
   - **Name:** `SCM_DO_BUILD_DURING_DEPLOYMENT`
   - **Value:** `true`
3. Click **Save**

---

## Step 5: Open Your App

After deployment (5–10 minutes):

- Go to `https://<your-app-name>.azurewebsites.net`
- Example: `https://purni-menu.azurewebsites.net`

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 503 / App won't start | Check **Log stream** or **Logs**; verify startup command and Python version |
| Module not found | Add `SCM_DO_BUILD_DURING_DEPLOYMENT=true` in Application settings |
| Slow first load | Normal on F1; app may sleep after inactivity |
| Data resets | F1 uses ephemeral storage; data is lost on restart/redeploy |

---

## GitHub Actions Workflow (auto-created)

Azure adds `.github/workflows/` with a deploy workflow. If you need to edit it, ensure:

- **Python version:** 3.11
- **Startup command** is set in Azure Portal (Step 2 above)

---

## Summary

| Setting | Value |
|---------|-------|
| Runtime | Python 3.11 |
| Plan | Free F1 |
| Startup | `gunicorn backend.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000` |
| Repo | `badgayan123/PurNI_Food_Scheduler` |
