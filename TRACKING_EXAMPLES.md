# Analytics Tracking Examples

The CISK Navigator supports adding analytics tracking code to generated HTML files via the YAML `meta.tracking_code` field.

## Google Analytics (GA4)

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

## Google Tag Manager

```yaml
meta:
  title: "My Navigator"
  version: "1.0"
  tracking_code: |
    <!-- Google Tag Manager -->
    <script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
    new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
    j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
    'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
    })(window,document,'script','dataLayer','GTM-XXXXXXX');</script>
```

**Setup:**
1. Go to https://tagmanager.google.com/
2. Create a container
3. Get your Container ID (starts with `GTM-`)
4. Replace `GTM-XXXXXXX` with your actual ID

## Plausible Analytics (Privacy-Focused)

```yaml
meta:
  title: "My Navigator"
  version: "1.0"
  tracking_code: |
    <!-- Plausible Analytics -->
    <script defer data-domain="yourdomain.com" src="https://plausible.io/js/script.js"></script>
```

**Setup:**
1. Sign up at https://plausible.io/
2. Add your domain
3. Replace `yourdomain.com` with your actual domain

## Fathom Analytics (Privacy-Focused)

```yaml
meta:
  title: "My Navigator"
  version: "1.0"
  tracking_code: |
    <!-- Fathom Analytics -->
    <script src="https://cdn.usefathom.com/script.js" data-site="ABCDEFGH" defer></script>
```

**Setup:**
1. Sign up at https://usefathom.com/
2. Get your Site ID
3. Replace `ABCDEFGH` with your actual Site ID

## Matomo (Self-Hosted)

```yaml
meta:
  title: "My Navigator"
  version: "1.0"
  tracking_code: |
    <!-- Matomo -->
    <script>
      var _paq = window._paq = window._paq || [];
      _paq.push(['trackPageView']);
      _paq.push(['enableLinkTracking']);
      (function() {
        var u="https://your-matomo-domain.com/";
        _paq.push(['setTrackerUrl', u+'matomo.php']);
        _paq.push(['setSiteId', '1']);
        var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
        g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
      })();
    </script>
```

## Custom Tracking Endpoint

```yaml
meta:
  title: "My Navigator"
  version: "1.0"
  tracking_code: |
    <!-- Custom Tracking -->
    <script>
      fetch('https://your-tracking-endpoint.com/track', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          page: document.title,
          url: window.location.href,
          timestamp: new Date().toISOString()
        })
      });
    </script>
```

## Multiple Tracking Services

You can include multiple tracking services in one block:

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

    <!-- Plausible Analytics -->
    <script defer data-domain="yourdomain.com" src="https://plausible.io/js/script.js"></script>
```

## Important Notes

1. **Privacy**: Some analytics tools track users. Consider your organization's privacy policy.
2. **GDPR/CCPA**: If you serve users in EU/California, you may need cookie consent banners.
3. **Performance**: Analytics scripts can slow down page load. Consider async/defer attributes.
4. **Testing**: Test in the browser console to verify tracking is working.
5. **Standalone HTML**: The tracking code is embedded in generated standalone HTML files.

## Verifying It Works

After generating your HTML file:

1. Open the HTML file in a browser
2. Open Developer Tools (F12)
3. Go to Network tab
4. Look for requests to your analytics domain (e.g., google-analytics.com, plausible.io)
5. Check your analytics dashboard for page views

## Troubleshooting

**Tracking not working?**
- Check browser console for JavaScript errors
- Verify your tracking ID is correct
- Check if ad blockers are blocking the requests
- Make sure you're viewing the generated HTML file (not the Flask dev server)
- Some analytics require the file to be served over HTTPS

**Need to remove tracking?**
Simply remove or comment out the `tracking_code` field in your YAML file.
