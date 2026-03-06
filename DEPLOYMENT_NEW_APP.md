# Deploying CISK Navigator NEW App to Render

This guide covers deploying the **NEW data collection app** (not the visualization tool) to Render.

## Prerequisites

- GitHub account with this repository pushed
- Render.com account (free tier available)

## Quick Deploy

### Option 1: Using render.yaml (Automatic - Deploys BOTH Apps)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Add new app deployment config"
   git push origin main
   ```

2. **Connect to Render**:
   - Go to https://render.com/
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml` and create both services:
     - `cisk-navigator-viz` (OLD visualization app)
     - `cisk-navigator-app` (NEW data collection app)

3. **Access Your Apps**:
   - OLD app: `https://cisk-navigator-viz.onrender.com`
   - NEW app: `https://cisk-navigator-app.onrender.com`

### Option 2: Manual Deploy (NEW App Only)

If you only want to deploy the NEW app:

1. **Push to GitHub** (if not done already)

2. **Create New Web Service on Render**:
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `CISK-Navigator`

3. **Configure the Service**:
   ```
   Name: cisk-navigator-app
   Region: Choose nearest to you
   Branch: main
   Root Directory: (leave empty)
   Runtime: Python 3
   Build Command: pip install -r requirements.new.txt
   Start Command: gunicorn run:app
   Instance Type: Free
   ```

4. **Add Environment Variables**:
   Click "Advanced" → "Add Environment Variable":
   ```
   SECRET_KEY = [Click "Generate" for random value]
   FLASK_CONFIG = production
   ```

5. **Deploy**:
   - Click "Create Web Service"
   - Render will build and deploy your app
   - First deploy takes ~5 minutes

## Post-Deployment

### First Login
Once deployed, visit your app URL:
```
https://your-app-name.onrender.com/auth/login
```

**Bootstrap Admin Credentials**:
- Username: `cisk`
- Password: `Zurich20`
- **IMPORTANT**: Change password immediately after first login!

### Database Persistence

**⚠️ Important**: The free Render tier uses ephemeral storage. Your SQLite database will be **reset on every deploy or service restart**.

**For Production Use**, you should:

1. **Upgrade to Persistent Disk** (Render paid plan):
   - Add a persistent disk in Render dashboard
   - Mount at `/opt/render/project/src/instance`
   - Database will persist across deploys

2. **Or Use PostgreSQL** (Recommended for production):
   - Add PostgreSQL database in Render (free tier available)
   - Update `FLASK_CONFIG` to use PostgreSQL
   - Database persists independently

### Using PostgreSQL on Render

1. **Create PostgreSQL Database**:
   - In Render dashboard: "New +" → "PostgreSQL"
   - Name it (e.g., `cisk-navigator-db`)
   - Free tier: 90 days, then $7/month

2. **Update App Environment Variables**:
   - Copy the "Internal Database URL" from PostgreSQL dashboard
   - In your web service, add environment variable:
     ```
     DATABASE_URL = [paste Internal Database URL]
     ```

3. **Update Config** (optional - auto-detected):
   The app will automatically use `DATABASE_URL` if present.

## Monitoring

### View Logs
- In Render dashboard, click your service
- Click "Logs" tab
- See real-time application logs

### Check Status
- Dashboard shows service status
- Green = running
- Red = deployment failed (check logs)

## Updating the App

Whenever you push changes to GitHub:
```bash
git add .
git commit -m "Your changes"
git push origin main
```

Render automatically detects the push and redeploys (if auto-deploy is enabled).

## Custom Domain

To use your own domain:

1. **In Render Dashboard**:
   - Go to your service
   - Click "Settings" → "Custom Domain"
   - Add your domain (e.g., `app.yourcompany.com`)

2. **In Your DNS Provider**:
   - Add CNAME record pointing to Render's domain
   - Example: `app.yourcompany.com` → `cisk-navigator-app.onrender.com`

3. **SSL Certificate**:
   - Render automatically provisions Let's Encrypt SSL
   - Your app will be available at `https://app.yourcompany.com`

## Troubleshooting

### Deploy Failed

**Check logs** for errors:
- Database connection issues
- Missing dependencies
- Python version mismatch

**Common fixes**:
- Ensure `requirements.new.txt` is complete
- Check `PYTHON_VERSION` environment variable
- Verify `SECRET_KEY` is set

### App Won't Start

**Check**:
- Start command is correct: `gunicorn run:app`
- Port binding: Gunicorn uses `$PORT` from Render
- Database: SQLite file can be created

**Try**:
- Manual redeploy from dashboard
- Check logs for specific error
- Verify all environment variables

### Database Reset After Deploy

This is **expected** with SQLite on free tier!

**Solutions**:
1. Upgrade to persistent disk (paid)
2. Use PostgreSQL (free for 90 days)
3. Accept resets for testing/demo purposes

### Slow First Request

Render free tier **spins down after 15 minutes of inactivity**.

First request after spin-down:
- Takes 30-60 seconds to wake up
- Subsequent requests are fast

**Solution**: Upgrade to paid tier for always-on service.

## Cost

### Free Tier
- **OLD app (viz)**: Free forever (static-like)
- **NEW app**: Free with limitations:
  - Spins down after 15 min inactivity
  - 750 hours/month (enough for one service)
  - Database resets on deploy (unless using PostgreSQL)

### Paid Options
- **Starter ($7/month per service)**:
  - Always on (no spin down)
  - Persistent disk available
  - More RAM/CPU

- **PostgreSQL ($7/month)**:
  - Persistent database
  - Backups included
  - 1GB storage

## Security Recommendations

### For Production:

1. **Change Bootstrap Password**:
   - Login as `cisk`/`Zurich20`
   - Immediately change password
   - Use strong password (16+ characters)

2. **Set Strong SECRET_KEY**:
   - In Render: Environment Variables → SECRET_KEY → Generate
   - Never commit SECRET_KEY to git

3. **Use PostgreSQL**:
   - Don't rely on SQLite in production
   - PostgreSQL is more secure and reliable

4. **Enable HTTPS Only**:
   - Render provides this automatically
   - Enforce HTTPS in app (future enhancement)

5. **Regular Backups**:
   - If using PostgreSQL, enable Render backups
   - Or export data regularly

## Support

### Render Support
- Render Status: https://status.render.com/
- Render Docs: https://render.com/docs
- Community: https://community.render.com/

### App Issues
- GitHub Issues: https://github.com/YOUR_USERNAME/CISK-Navigator/issues
- Check `flask_debug.log` locally first
- Review Render logs for production issues

## Next Steps

After successful deployment:

1. **✅ Login and change bootstrap password**
2. **✅ Create your first organization**
3. **✅ Add users and assign to organization**
4. **✅ Build your hierarchy (Spaces → Challenges → Initiatives → Systems → KPIs)**
5. **✅ Create value types**
6. **✅ Start collecting data!**

---

**Need Help?** Check the logs first, then consult:
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical details
- [SPECIFICATIONS.md](app/SPECIFICATIONS.md) - Feature documentation
- Render documentation for deployment issues
