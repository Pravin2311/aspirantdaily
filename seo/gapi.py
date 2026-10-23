"""
Read-only access to Search Console, the GA4 Data/Admin APIs and the AdSense
Management API for the weekly SEO workflow. One OAuth desktop client, one
consent screen, read-only scopes only.

Secrets never live in the repo. Both files sit in a per-user folder:
  %APPDATA%\\teachings-seo\\client_secret*.json  (downloaded once from Cloud Console;
                                                  Google's long file name is fine)
  %APPDATA%\\teachings-seo\\token.json           (written after the first consent)
Override the folder with the TEACHINGS_SEO_CREDS environment variable.
"""
import datetime as dt
import glob
import os
import sys

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/adsense.readonly",
]

CREDS_DIR = os.environ.get("TEACHINGS_SEO_CREDS") or os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~/.config"), "teachings-seo")
TOKEN = os.path.join(CREDS_DIR, "token.json")


class SetupError(Exception):
    """Raised when credentials are missing or need an interactive step."""


def get_credentials(interactive=False):
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save(creds)
            return creds
        except RefreshError as e:
            if not interactive:
                raise SetupError(f"Saved token could not be refreshed ({e}). "
                                 "Re-run: python seo/weekly.py --auth")
    if not interactive:
        raise SetupError("No saved Google token. Run once: python seo/weekly.py --auth")
    # Google's download is named client_secret_<id>.apps.googleusercontent.com.json
    found = sorted(glob.glob(os.path.join(CREDS_DIR, "client_secret*.json")))
    if not found:
        raise SetupError(f"No OAuth client file (client_secret*.json) in {CREDS_DIR}. "
                         "See seo/README.md, step 3.")
    if len(found) > 1:
        raise SetupError(f"Several client_secret*.json files in {CREDS_DIR}; keep only one.")
    flow = InstalledAppFlow.from_client_secrets_file(found[0], SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    _save(creds)
    return creds


def _save(creds):
    os.makedirs(CREDS_DIR, exist_ok=True)
    with open(TOKEN, "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def _iso(d):
    return d.isoformat() if isinstance(d, dt.date) else d


# ---------------------------------------------------------------- Search Console

class SearchConsole:
    def __init__(self, creds):
        self.svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    def sites(self):
        return self.svc.sites().list().execute().get("siteEntry", [])

    def query(self, site, start, end, dimensions, filters=None, data_state="final"):
        """All rows for the window, paging past the 25k-row page size."""
        rows, start_row = [], 0
        while True:
            body = {"startDate": _iso(start), "endDate": _iso(end),
                    "dimensions": dimensions, "type": "web", "rowLimit": 25000,
                    "startRow": start_row, "dataState": data_state}
            if filters:
                body["dimensionFilterGroups"] = [{"filters": filters}]
            page = self.svc.searchanalytics().query(siteUrl=site, body=body).execute()
            batch = page.get("rows", [])
            for r in batch:
                row = dict(zip(dimensions, r["keys"])) if dimensions else {}
                row.update(clicks=r["clicks"], impressions=r["impressions"],
                           ctr=r["ctr"], position=r["position"])
                rows.append(row)
            if len(batch) < 25000:
                return rows
            start_row += 25000

    def sitemaps(self, site):
        return self.svc.sitemaps().list(siteUrl=site).execute().get("sitemap", [])

    def inspect(self, site, url):
        body = {"inspectionUrl": url, "siteUrl": site}
        res = self.svc.urlInspection().index().inspect(body=body).execute()
        r = res.get("inspectionResult", {}).get("indexStatusResult", {})
        return {"url": url, "verdict": r.get("verdict"),
                "coverageState": r.get("coverageState"),
                "lastCrawlTime": r.get("lastCrawlTime"),
                "googleCanonical": r.get("googleCanonical"),
                "userCanonical": r.get("userCanonical")}


# ---------------------------------------------------------------- GA4

class Analytics:
    def __init__(self, creds):
        self.data = build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
        self.admin = build("analyticsadmin", "v1beta", credentials=creds, cache_discovery=False)

    def find_property(self, measurement_id):
        """Property id whose web stream carries the gtag measurement id on the site."""
        summaries = self.admin.accountSummaries().list(pageSize=200).execute()
        for acct in summaries.get("accountSummaries", []):
            for prop in acct.get("propertySummaries", []):
                streams = self.admin.properties().dataStreams().list(
                    parent=prop["property"]).execute().get("dataStreams", [])
                for s in streams:
                    if s.get("webStreamData", {}).get("measurementId") == measurement_id:
                        return prop["property"].split("/")[1]
        return None

    def report(self, prop, start, end, dimensions, metrics, organic_only=False,
               limit=10000, order_by=None):
        body = {"dateRanges": [{"startDate": _iso(start), "endDate": _iso(end)}],
                "dimensions": [{"name": d} for d in dimensions],
                "metrics": [{"name": m} for m in metrics],
                "limit": limit, "returnPropertyQuota": True}
        if organic_only:
            body["dimensionFilter"] = {"filter": {
                "fieldName": "sessionDefaultChannelGroup",
                "stringFilter": {"value": "Organic Search"}}}
        if order_by:
            body["orderBys"] = [{"metric": {"metricName": order_by}, "desc": True}]
        res = self.data.properties().runReport(property=f"properties/{prop}", body=body).execute()
        rows = []
        for r in res.get("rows", []):
            row = {d: v["value"] for d, v in zip(dimensions, r["dimensionValues"])}
            for m, v in zip(metrics, r["metricValues"]):
                row[m] = float(v["value"])
            rows.append(row)
        return rows


# ---------------------------------------------------------------- AdSense

class AdSense:
    def __init__(self, creds):
        self.svc = build("adsense", "v2", credentials=creds, cache_discovery=False)

    def accounts(self):
        return self.svc.accounts().list().execute().get("accounts", [])

    def report(self, account, start, end, dimensions, metrics):
        s, e = start, end
        res = self.svc.accounts().reports().generate(
            account=account, dateRange="CUSTOM",
            startDate_year=s.year, startDate_month=s.month, startDate_day=s.day,
            endDate_year=e.year, endDate_month=e.month, endDate_day=e.day,
            dimensions=dimensions, metrics=metrics).execute()
        headers = [h["name"] for h in res.get("headers", [])]
        currency = next((h["currencyCode"] for h in res.get("headers", []) if h.get("currencyCode")), None)
        rows = []
        for r in res.get("rows", []):
            vals = [c.get("value") for c in r["cells"]]
            row = {}
            for h, v in zip(headers, vals):
                row[h] = v if h in dimensions else float(v or 0)
            row["currency"] = currency
            rows.append(row)
        return rows


def explain_http_error(e):
    """One line that says what the person has to fix, for the common cases."""
    status = getattr(e, "status_code", None) or getattr(e.resp, "status", None)
    text = str(e)
    if "has not been used in project" in text or "is disabled" in text:
        return "API not enabled in the Cloud project -- enable it (see seo/README.md step 2)."
    if status == 403:
        return "Permission denied -- the signed-in Google account lacks access to this property/account."
    if status == 401:
        return "Token rejected -- re-run: python seo/weekly.py --auth"
    return text.splitlines()[0][:300]


__all__ = ["SCOPES", "CREDS_DIR", "SetupError", "HttpError", "get_credentials",
           "SearchConsole", "Analytics", "AdSense", "explain_http_error"]

if __name__ == "__main__":
    print("Credentials folder:", CREDS_DIR, file=sys.stderr)
