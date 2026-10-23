"""
Read-only Bing Webmaster Tools API access for the weekly SEO workflow.
Bing (and Yahoo, which uses Bing's results) sends most of the site's
organic users, and Search Console doesn't see any of it.

Auth is a per-user API key (Bing Webmaster Tools > Settings > API Access).
It never lives in the repo:
  %APPDATA%\\teachings-seo\\bing_api_key.txt   (just the key, one line)
or the BING_WEBMASTER_API_KEY environment variable.

Only Get* methods are called. Docs:
https://learn.microsoft.com/en-us/bingwebmaster/getting-access
"""
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import gapi

ENDPOINT = "https://ssl.bing.com/webmaster/api.svc/json/"
KEY_FILE = os.path.join(gapi.CREDS_DIR, "bing_api_key.txt")


class BingError(Exception):
    pass


def api_key():
    key = os.environ.get("BING_WEBMASTER_API_KEY")
    if not key and os.path.exists(KEY_FILE):
        with open(KEY_FILE, encoding="utf-8") as f:
            key = f.read().strip()
    if not key:
        raise gapi.SetupError(f"No Bing API key. Save it in {KEY_FILE} (see seo/README.md, Bing section).")
    return key


def parse_date(v):
    """Bing returns WCF dates like /Date(1696402800000-0700)/."""
    m = re.match(r"/Date\((-?\d+)", v or "")
    if not m:
        return None
    return dt.datetime.fromtimestamp(int(m.group(1)) / 1000, dt.timezone.utc).date().isoformat()


class Bing:
    def __init__(self, key=None):
        self.key = key or api_key()

    def call(self, method, **params):
        if not method.startswith("Get"):
            raise ValueError("read-only client: only Get* methods")
        q = urllib.parse.urlencode({**params, "apikey": self.key})
        req = urllib.request.Request(ENDPOINT + method + "?" + q, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # never echo the request URL: it contains the key
            detail = e.read().decode("utf-8", "replace")[:300].replace(self.key, "***")
            raise BingError(f"{method}: HTTP {e.code} {detail}") from None
        except urllib.error.URLError as e:
            raise BingError(f"{method}: {e.reason}") from None
        return body.get("d", body)

    def sites(self):
        return self.call("GetUserSites")

    def _rows(self, method, site, key_field):
        rows = []
        for r in self.call(method, siteUrl=site) or []:
            rows.append({key_field: r.get("Query"), "date": parse_date(r.get("Date")),
                         "clicks": r.get("Clicks", 0), "impressions": r.get("Impressions", 0),
                         "avg_impression_position": r.get("AvgImpressionPosition"),
                         "avg_click_position": r.get("AvgClickPosition")})
        return rows

    def queries(self, site):
        return self._rows("GetQueryStats", site, "query")

    def pages(self, site):
        # GetPageStats reuses the QueryStats shape; "Query" holds the page URL
        return self._rows("GetPageStats", site, "page")

    def traffic(self, site):
        return [{"date": parse_date(r.get("Date")), "clicks": r.get("Clicks", 0),
                 "impressions": r.get("Impressions", 0)}
                for r in self.call("GetRankAndTrafficStats", siteUrl=site) or []]

    def crawl(self, site):
        return [dict(r, Date=parse_date(r.get("Date"))) for r in self.call("GetCrawlStats", siteUrl=site) or []]
