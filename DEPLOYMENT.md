# 🚀 CISK Navigator Deployment Guide

Complete guide to deploying CISK Navigator to various cloud platforms.

## Quick Start (5 Minutes)

The fastest way to deploy is using Railway.app with GitHub:

1. Push code to GitHub
2. Connect Railway to your GitHub repo
3. Deploy automatically

---

## Platform Comparison

| Platform | Difficulty | Cost | Best For |
|----------|-----------|------|----------|
| **Railway.app** | ⭐ Easiest | Free tier | Quick deployment, auto-deploy from GitHub |
| **Render.com** | ⭐⭐ Easy | Free tier | Reliable, good free tier |
| **Vercel/Netlify** | ⭐⭐ Easy | Free | Serverless, unlimited bandwidth |
| **Heroku** | ⭐⭐ Medium | $5-7/mo | Classic option, good docs |

---

## Step 1: Push to GitHub

First, push your code to GitHub (if not already done):

```bash
cd /Users/mounir.dous/projects/CISK-Navigator

# Initialize git (skip if already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - CISK Navigator"

# Create a new repository on GitHub (https://github.com/new)
# Then connect it (replace YOUR_USERNAME):
git remote add origin https://github.com/YOUR_USERNAME/cisk-navigator.git
git branch -M main
git push -u origin main
```

**Important:** Make sure these files exist in your repo:
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version (python-3.11.x)
- `Procfile` - Deployment command (`web: gunicorn app:app`)

---

## Option 1: Railway.app (Recommended)

**Why Railway?** Easiest deployment with automatic GitHub integration.

### Steps:

1. **Go to Railway.app**
   - Visit: https://railway.app
   - Sign up with GitHub (free, no credit card required)

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `cisk-navigator` repository

3. **Automatic Deployment**
   - Railway automatically detects Python app
   - Installs dependencies from `requirements.txt`
   - Runs command from `Procfile`
   - Generates public URL (e.g., `https://cisk-navigator-production.up.railway.app`)

4. **Get Your URL**
   - Click "Settings" → "Domains"
   - Copy your public URL
   - Share it with users!

**That's it!** Every git push to main will auto-deploy.

---

## Option 2: Render.com

Good alternative to Railway with similar ease of use.

### Steps:

1. **Sign Up**
   - Go to https://render.com
   - Sign up with GitHub

2. **New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select `cisk-navigator`

3. **Configure**
   - **Name:** cisk-navigator
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Free

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (2-3 minutes)
   - Get your URL: `https://cisk-navigator.onrender.com`

---

## Option 3: Vercel/Netlify (Serverless)

For serverless deployment with unlimited bandwidth.

### Vercel Steps:

1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Deploy:
   ```bash
   cd /Users/mounir.dous/projects/CISK-Navigator
   vercel
   ```

3. Follow prompts and get your URL

### Note:
Vercel/Netlify require a serverless adapter. Railway/Render are simpler for Flask apps.

---

## Option 4: Heroku

Classic platform, requires credit card (but free tier available).

### Steps:

1. **Install Heroku CLI**
   ```bash
   brew tap heroku/brew && brew install heroku
   ```

2. **Login**
   ```bash
   heroku login
   ```

3. **Create App**
   ```bash
   cd /Users/mounir.dous/projects/CISK-Navigator
   heroku create cisk-navigator
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

5. **Open**
   ```bash
   heroku open
   ```

**Cost:** Free tier available, or $5-7/month for better performance.

---

## Analytics Tracking

Add analytics tracking to generated HTML files via YAML metadata.

### Google Analytics (GA4)

Add to your YAML file:

```yaml
meta:
  title: "My Navigator"
  version: "1.0"
  tracking_code: |
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-XXXXXXXXXX');
    </script>
```

**Setup:**
1. Go to https://analytics.google.com/
2. Create a new property
3. Get your Measurement ID (starts with `G-`)
4. Replace `G-XXXXXXXXXX` with your actual ID

### Plausible Analytics (Privacy-Friendly)

```yaml
meta:
  tracking_code: |
    <script defer data-domain="yourdomain.com" src="https://plausible.io/js/script.js"></script>
```

### Custom Analytics

Add any HTML/JavaScript tracking code:

```yaml
meta:
  tracking_code: |
    <!-- Your custom tracking code here -->
    <script>
      // Custom analytics
    </script>
```

---

## Environment Variables

If your app needs environment variables:

### Railway:
1. Project Settings → Variables
2. Add key-value pairs

### Render:
1. Dashboard → Environment
2. Add variables

### Heroku:
```bash
heroku config:set KEY=value
```

---

## Troubleshooting

### App Won't Start

**Check logs:**
- Railway: Dashboard → Logs
- Render: Dashboard → Logs
- Heroku: `heroku logs --tail`

**Common issues:**
1. Missing `Procfile`
2. Wrong Python version in `runtime.txt`
3. Missing dependencies in `requirements.txt`

### Port Binding Error

Make sure `app.py` uses environment port:
```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port)
```

### Static Files Not Loading

Check that templates and static folders are committed to git.

---

## Custom Domain

### Railway:
1. Settings → Domains → Add Custom Domain
2. Add CNAME record to your DNS

### Render:
1. Dashboard → Custom Domains
2. Follow DNS instructions

---

## Updating Your Deployment

After making changes:

```bash
git add .
git commit -m "Update description"
git push origin main
```

Railway/Render will automatically redeploy!

---

## Need Help?

- Check logs in your platform's dashboard
- Verify all config files exist (requirements.txt, Procfile, runtime.txt)
- Test locally first: `python app.py`
- Check GitHub Issues: https://github.com/YOUR_USERNAME/cisk-navigator/issues

---

**Questions?** Open an issue on GitHub or refer to:
- Railway docs: https://docs.railway.app
- Render docs: https://render.com/docs
- Heroku docs: https://devcenter.heroku.com
