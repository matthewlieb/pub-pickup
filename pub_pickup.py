# pub_pickup.py

import streamlit as st
from newsapi.newsapi_client import NewsApiClient
from newsapi.newsapi_exception import NewsAPIException
from eventregistry import EventRegistry, QueryArticlesIter
from dateutil import parser
import pandas as pd

# ——— Initialize API clients ———
NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY")
if not NEWSAPI_KEY:
    st.error("🛑 No NEWSAPI_KEY found. Please configure it in your Streamlit secrets.")
    st.stop()
newsapi = NewsApiClient(api_key=NEWSAPI_KEY)

NEWSAPI_AI_KEY = st.secrets.get("NEWSAPI_AI_KEY")
if not NEWSAPI_AI_KEY:
    st.warning("⚠️ No NEWSAPI_AI_KEY (newsapi.ai) found in secrets. Skipping Event Registry fetch.")
    er_client = None
else:
    er_client = EventRegistry(apiKey=NEWSAPI_AI_KEY)

# ——— Page config & title ———
st.set_page_config(page_title="Press Pickup Automator", layout="wide")
st.title("📰 Press Pickup Automator")

# ——— Inputs ———
client = st.text_input("Client / Talent Name", help="e.g. John Krasinski")
project = st.text_input("Project / Film Name", help="e.g. Quiet Place 3")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date")
with col2:
    end_date = st.date_input("End Date")

# ——— Fetch from NewsAPI.org ———
def fetch_newsapi(query, start, end):
    try:
        resp = newsapi.get_everything(
            q=query,
            from_param=start.isoformat(),
            to=end.isoformat(),
            language="en",
            sort_by="publishedAt",
            page_size=100,
        )
    except NewsAPIException as e:
        err = e.args[0] if e.args and isinstance(e.args[0], dict) else {"message": str(e)}
        st.error(f"⚠️ NewsAPI.org error: {err.get('message')}")
        return []
    rows = []
    for art in resp.get("articles", []):
        pub = art.get("source", {}).get("name", "")
        try:
            dated = parser.parse(art.get("publishedAt")).strftime("%B %-d, %Y")
        except:
            dated = art.get("publishedAt", "")
        title = art.get("title", "")
        url = art.get("url", "")
        rows.append((pub, dated, title, url))
    return rows

# ——— Fetch from newsapi.ai (Event Registry) ———
def fetch_eventregistry(query, start, end):
    if not er_client:
        return []
    try:
        q = QueryArticlesIter(
            keywords=query,
            dateStart=start.isoformat(),
            dateEnd=end.isoformat()
        )
        arts = q.execQuery(er_client, maxItems=100)
    except Exception as e:
        st.warning(f"⚠️ EventRegistry fetch failed: {e}")
        return []
    rows = []
    for art in arts:
        pub = art.get("source", {}).get("uri", "")
        date = art.get("date", "")
        try:
            dated = parser.parse(date).strftime("%B %-d, %Y")
        except:
            dated = date
        title = art.get("title", "")
        url = art.get("url", "")
        rows.append((pub, dated, title, url))
    return rows

# ——— Button handler ———
if st.button("Fetch Press Pickup"):
    if not client or not project:
        st.error("⚠️ Please enter both a client name and a project/film name.")
    else:
        query = f"{client} {project}"
        rows = fetch_newsapi(query, start_date, end_date) + fetch_eventregistry(query, start_date, end_date)

        # — Deduplicate & sort —
        seen = set()
        unique = []
        for pub, dt, title, url in rows:
            if url and url not in seen:
                seen.add(url)
                unique.append((pub, dt, title, url))
        try:
            unique.sort(key=lambda x: parser.parse(x[1]), reverse=True)
        except:
            unique.sort(key=lambda x: x[1], reverse=True)

        if not unique:
            st.info("ℹ️ No press pickups found for that query and date range.")
        else:
            df = pd.DataFrame(unique, columns=["Publisher", "Date", "Headline", "URL"])

            # — Interactive table (sortable/filterable) —
            st.markdown("### Results (Interactive Table)")
            st.dataframe(df)

            # — CSV download —
            st.download_button(
                "Download CSV",
                data=df.to_csv(index=False),
                file_name=f"{client.replace(' ','_')}_{project.replace(' ','_')}_pickup.csv",
                mime="text/csv"
            )

            # — Email template —
            st.markdown("### 📋 Email Template")
            template_lines = [
                f"**{pub}**  |  {dt}  |  {title}\n\nLink: {url}\n\n---"
                for pub, dt, title, url in unique
            ]
            st.code("\n".join(template_lines), language="markdown")
