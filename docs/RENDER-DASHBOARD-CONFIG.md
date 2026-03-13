# Render Dashboard Configuration - CRITICAL

## ⚠️ DISASTER: requirements.new.txt Override

**This has caused MULTIPLE production failures!**

### The Problem

Render Dashboard has a **manual "Build Command" override** that takes precedence over `render.yaml`.

If this setting says: `pip install -r requirements.new.txt`
- ALL deployments will use `requirements.new.txt` (even if it doesn't exist or is outdated)
- Changes to `requirements.txt` will be IGNORED
- Production will crash with `ModuleNotFoundError`

### The Fix

1. Go to **Render Dashboard** → Your CISK-Navigator service
2. Click **Settings** tab (left sidebar)
3. Scroll to **"Build & Deploy"** section
4. Look for **"Build Command"** field
5. If it contains `pip install -r requirements.new.txt`:
   - Click **Edit**
   - Either:
     - **DELETE the entire override** (recommended - will use render.yaml)
     - OR change to: `pip install -r requirements.txt`
6. Click **Save Changes**

### Verify Correct Configuration

**render.yaml** (correct):
```yaml
buildCommand: pip install -r requirements.txt
```

**Render Dashboard → Settings → Build Command**:
- Should be **EMPTY** (uses render.yaml)
- OR should say: `pip install -r requirements.txt`
- **NEVER**: `pip install -r requirements.new.txt`

### History of Failures

**Incident 1** (March 7, 2026):
- Someone created requirements.new.txt
- Set Render Dashboard to use it
- Later updates to requirements.txt were ignored
- Production failed

**Incident 2** (March 10, 2026):
- Added SSO with cryptography dependency
- Updated requirements.txt correctly
- Deployed → FAILED: ModuleNotFoundError: No module named 'cryptography'
- Cleared build cache → STILL FAILED
- Removed blank lines from requirements.txt → STILL FAILED
- Discovered: Render was using requirements.new.txt (old, incomplete)
- Root cause: Dashboard override pointing to requirements.new.txt

### Prevention Measures

**Automated safeguards now in place:**

1. **`.gitignore`**: Blocks requirements.new.txt from being committed
2. **Pre-commit hook**: Rejects any commit containing requirements.new.txt
3. **Pre-commit hook**: Ensures only ONE requirements file exists
4. **MEMORY.md**: Documents this disaster pattern

**Manual verification required:**

- Check Render Dashboard settings BEFORE every deploy
- Confirm Build Command is empty or uses requirements.txt
- Never create requirements.new.txt for any reason

### How to Deploy Safely

1. **Verify code locally**:
   ```bash
   # Install from requirements.txt
   pip install -r requirements.txt

   # Run Flask
   flask run --port 5003

   # Test all new imports/features
   ```

2. **Check git**:
   ```bash
   # Ensure only requirements.txt exists
   ls requirements*.txt
   # Should show ONLY: requirements.txt

   # Verify it's committed
   git diff requirements.txt
   # Should be empty (no uncommitted changes)
   ```

3. **Verify Render Dashboard**:
   - Settings → Build Command → Empty or `pip install -r requirements.txt`

4. **Deploy**:
   - Push to GitHub
   - Render auto-deploys
   - OR Manual Deploy → Deploy latest commit

5. **Monitor logs**:
   - Watch pip install output
   - Verify ALL packages install (especially new ones)
   - Watch Flask startup
   - Check for ModuleNotFoundError

### If Deployment Fails

**Symptom**: `ModuleNotFoundError` for a package that IS in requirements.txt

**Root cause**: Render Dashboard override or cache issue

**Fix**:
1. Check Dashboard → Settings → Build Command
2. Fix or remove override
3. Manual Deploy → **Clear build cache & deploy**
4. Watch logs to confirm correct requirements file is used

### Emergency Contact

If you see in logs:
```
-r requirements.new.txt (line X)
```

**STOP IMMEDIATELY** - Render is using the wrong file!

1. Fix Dashboard Build Command
2. Delete requirements.new.txt from repo if it exists
3. Redeploy with clear cache

---

**Last Updated**: 2026-03-10
**Status**: Safeguards implemented, awaiting Dashboard fix confirmation
