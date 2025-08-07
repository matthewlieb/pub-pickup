import streamlit as st
from newsapi.newsapi_client import NewsApiClient
from newsapi.newsapi_exception import NewsAPIException
from dateutil import parser

# Initialize NewsAPI client (set your key in ~/.streamlit/secrets.toml)
API_KEY = st.secrets.get("NEWSAPI_KEY")
if not API_KEY:
    st.error("🛑 No NEWSAPI_KEY found. Please configure it in your Streamlit secrets.")
    st.stop()

newsapi = NewsApiClient(api_key=API_KEY)

st.set_page_config(page_title="Press Pickup Automator", layout="wide")
st.title("📰 Press Pickup Automator")

# ——— Input form ———
client = st.text_input("Client / Talent Name", help="e.g. John Krasinski")
project = st.text_input("Project / Film Name", help="e.g. Quiet Place 3")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date")
with col2:
    end_date = st.date_input("End Date")

# ——— NewsAPI Fetcher with error handling ———
def fetch_newsapi(query, start, end):
    """
    Returns a list of tuples: (publisher, date_str, headline, url)
    If NewsAPI errors (e.g. invalid key or date), shows an error and returns an empty list.
    """
    try:
        response = newsapi.get_everything(
            q=query,
            from_param=start.isoformat(),
            to=end.isoformat(),
            language="en",
            sort_by="publishedAt",
            page_size=100,
        )
    except NewsAPIException as e:
        # e.args[0] is a dict containing 'code' and 'message'
        err = e.args[0] if e.args and isinstance(e.args[0], dict) else {"message": str(e)}
        st.error(f"⚠️ NewsAPI error: {err.get('message', str(e))}")
        return []

    articles = response.get("articles", [])
    rows = []
    for art in articles:
        pub       = art.get("source", {}).get("name", "")
        try:
            dated = parser.parse(art.get("publishedAt")).strftime("%B %-d, %Y")
        except Exception:
            dated = art.get("publishedAt", "")
        headline  = art.get("title", "")
        url       = art.get("url", "")
        rows.append((pub, dated, headline, url))
    return rows

# ——— Placeholders for future sources ———
# def fetch_google(query, start, end):
#     return []

# def fetch_rss(query, start, end):
#     return []

# ——— Fetch button ———
if st.button("Fetch Press Pickup"):
    if not client or not project:
        st.error("⚠️ Please enter both a client name and a project/film name.")
    else:
        query = f"{client} {project}"
        rows = fetch_newsapi(query, start_date, end_date)
        # rows += fetch_google(query, start_date, end_date)
        # rows += fetch_rss(query, start_date, end_date)

        # ——— Deduplicate & sort ———
        seen = set()
        uniq = []
        for pub, dt, headline, url in rows:
            if not url or url in seen:
                continue
            seen.add(url)
            uniq.append((pub, dt, headline, url))

        def sort_key(item):
            try:
                return parser.parse(item[1])
            except:
                return item[1]
        uniq.sort(key=sort_key, reverse=True)

        # ——— Display results ———
        if uniq:
            st.markdown("### Results")
            st.table(uniq)

            # ——— Render email template ———
            st.markdown("### 📋 Email Template (Markdown)")
            md_lines = []
            for pub, dt, headline, url in uniq:
                md_lines.append(f"**{pub}**  |  {dt}  |  {headline}\n\nLink: {url}\n\n---")
            body = "\n".join(md_lines)
            st.code(body, language="markdown")

            # ——— Download button ———
            st.download_button(
                label="Download as Markdown",
                data=body,
                file_name=f"{client.replace(' ', '_')}_{project.replace(' ', '_')}_pickup.md",
                mime="text/markdown"
            )
        else:
            st.info("ℹ️ No press pickups found for that query and date range.")
