import io
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

# ---------------------------
# Streamlit page setup + CSS
# ---------------------------
st.set_page_config(page_title="Law Firm Agency Detector", page_icon="🔎", layout="wide")

# ---- Style block ----
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: visible;}
.title { font-weight: 700; letter-spacing: .3px; font-size: 1.8rem; margin-bottom: .25rem; }
[data-testid="stFileUploaderDropzone"] { border: 2px dashed rgba(255,255,255,0.3); border-radius: 12px; padding: 1.5rem; }
[data-testid="stDataFrame"] div[role="grid"] { border-radius: 12px; }
.stProgress > div > div > div > div { background-color: #14b8a6; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# Agency signatures (16 vendors, editable)
# ----------------------------------------
AGENCIES = {
    "Hennessey Digital": ["hennessey"],
    "Scorpion": ["scorpion", "scorpioncms"],
    "LawRank": ["lawrank"],
    "iLawyerMarketing": ["ilawyermarketing"],
    "Elite Legal Marketing": ["elitelegalmarketing"],
    "Juris Digital": ["jurisdigital"],
    "Justia": ["justia"],
    "Nifty Marketing": ["niftymarketing"],
    "On The Map Marketing": ["onthemapmarketing"],
    "FindLaw": ["findlaw", "powered by findlaw"],
    "Thomson Reuters": ["thomsonreuters", "thomson reuters"],
    "Martindale": ["martindale", "martindale-avvo", "martindale.com"],
    "Foster Web Marketing": ["fosterwebmarketing", "fwm"],
    "Triple Digital": ["tripledigital", "tripledigitalseo"],
    "EverConvert": ["everconvert"],
    "MeanPug": ["meanpug", "meanpug.com"]
}

# ---------------------------
# Helper functions
# ---------------------------
def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "http://" + url
    return url

def detect_agency(html: str) -> dict:
    """Return {'Agency Name': ['asset','text',...]} based on code/text matches."""
    soup = BeautifulSoup(html, "html.parser")
    evidence = {}

    # Collect searchable strings
    texts = []

    # Footer text
    footer = soup.find("footer")
    if footer:
        texts.append(footer.get_text(" ", strip=True))

    # Meta tag content
    for meta in soup.find_all("meta"):
        content = meta.get("content")
        if content:
            texts.append(str(content))

    # HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        texts.append(str(comment))

    # Assets (scripts, styles, images)
    for tag in soup.find_all(["script", "link", "img"]):
        src = tag.get("src") or tag.get("href")
        if src:
            texts.append(str(src))

    full_text = " ".join(texts).lower()

    # Check for each agency's signatures
    for agency, signatures in AGENCIES.items():
        for sig in signatures:
            if sig in full_text:
                kinds = []
                if any(x in full_text for x in (".js", ".css", "cdn", ".png", ".jpg", ".svg")):
                    kinds.append("asset")
                kinds.append("text")
                evidence[agency] = sorted(set(kinds))
                break  # stop after first signature match for this agency

    return evidence

def run_scan(df: pd.DataFrame) -> pd.DataFrame:
    # Find the column that likely contains URLs
    url_col = None
    for c in df.columns:
        if str(c).strip().lower() in ("url", "urls", "website", "domain"):
            url_col = c
            break
    if url_col is None:
        url_col = df.columns[0]  # assume first column is URLs

    urls = df[url_col].dropna().astype(str).tolist()

    results = []
    prog = st.progress(0, text="Starting scan…")

    for i, url in enumerate(urls, start=1):
        st.write(f"🔍 Checking: {url}")
        full_url = normalize_url(url)
        if not full_url:
            results.append({"URL": url, "Agency Detected": "Error", "Evidence Type": "Empty URL"})
            prog.progress(i/len(urls), text=f"Scanning… {i}/{len(urls)}")
            continue

        try:
            r = requests.get(
                full_url,
                timeout=12,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
            )
            if r.status_code == 200 and r.text:
                hits = detect_agency(r.text)
                if hits:
                    for agency, methods in hits.items():
                        results.append({
                            "URL": url,
                            "Agency Detected": agency,
                            "Evidence Type": ", ".join(methods)
                        })
                else:
                    results.append({"URL": url, "Agency Detected": "None", "Evidence Type": ""})
            else:
                results.append({"URL": url, "Agency Detected": "Error", "Evidence Type": f"HTTP {r.status_code}"})
        except Exception as e:
            results.append({"URL": url, "Agency Detected": "Error", "Evidence Type": str(e)})

        prog.progress(i/len(urls), text=f"Scanning… {i}/{len(urls)}")

    return pd.DataFrame(results)

# ---------------------------
# Streamlit app
# ---------------------------
def main():
    st.markdown("<h1 class='title'>🏷️ Law Firm Website Agency Detector</h1>", unsafe_allow_html=True)
    st.write("Upload a CSV of URLs and I’ll flag likely website vendors (Hennessey, Scorpion, LawRank, FindLaw, etc.).")

    # Sidebar (summary + filters)
    st.sidebar.header("Summary & Filters")

    # Sample CSV download
    sample = io.StringIO()
    pd.DataFrame({"URL": ["example.com", "scorpion.co", "hennesseydigital.com"]}).to_csv(sample, index=False)
    st.download_button(
        "📄 Download sample CSV",
        sample.getvalue().encode("utf-8"),
        file_name="sample_urls.csv",
        mime="text/csv"
    )

    uploaded = st.file_uploader(
        "Upload CSV (a column named 'URL' is ideal — otherwise I'll use the first column)",
        type=["csv"]
    )

    if uploaded:
        # read CSV robustly
        try:
            df = pd.read_csv(uploaded, encoding="utf-8", engine="python")
        except Exception:
            uploaded.seek(0)
            df = pd.read_csv(uploaded, encoding_errors="ignore", engine="python")

        st.success(f"Loaded {len(df)} rows.")
        st.dataframe(df.head(10), use_container_width=True)

        if st.button("▶️ Run scan"):
            result_df = run_scan(df)

            # ---- Sidebar metrics & filters ----
            total_urls = len(df)
            detected_df = result_df[~result_df["Agency Detected"].isin(["None", "Error"])]
            detected_count = len(detected_df)
            rate = f"{(detected_count / total_urls * 100):.0f}%" if total_urls else "0%"

            st.sidebar.metric("Total URLs", total_urls)
            st.sidebar.metric("Detected", detected_count)
            st.sidebar.metric("Detection rate", rate)

            # Counts by agency (for bar chart + multiselect)
            counts = detected_df["Agency Detected"].value_counts().sort_values(ascending=False)
            if not counts.empty:
                st.sidebar.bar_chart(counts)
                selected_agencies = st.sidebar.multiselect(
                    "Show only these agencies",
                    options=counts.index.tolist(),
                    default=counts.index.tolist()
                )
            else:
                selected_agencies = []

            hide_none_error = st.sidebar.checkbox("Hide None/Error rows", value=True)

            # Apply filters
            filtered = result_df.copy()
            if hide_none_error:
                filtered = filtered[~filtered["Agency Detected"].isin(["None", "Error"])]
            if selected_agencies:
                filtered = filtered[filtered["Agency Detected"].isin(selected_agencies)]

            # ---- Main area output ----
            st.success("✅ Done!")
            st.subheader("Results")
            st.dataframe(filtered if not filtered.empty else result_df, use_container_width=True)

            # Downloads (filtered + raw)
            st.download_button(
                "📥 Download filtered results CSV",
                (filtered if not filtered.empty else result_df).to_csv(index=False).encode("utf-8"),
                file_name="agency_results_filtered.csv",
                mime="text/csv"
            )
            st.download_button(
                "📥 Download full results CSV",
                result_df.to_csv(index=False).encode("utf-8"),
                file_name="agency_results_full.csv",
                mime="text/csv"
            )
    else:
        st.info("Drag a CSV file here to begin. Keep batches to a few hundred URLs to avoid rate limits.")

if __name__ == "__main__":
    main()
