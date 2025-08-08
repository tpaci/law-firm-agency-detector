import io
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

# ---------------------------
# Streamlit page setup + CSS
# ---------------------------
st.set_page_config(page_title="Law Firm Agency Detector", page_icon="🔎", layout="wide")

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: visible;}
.title { font-weight: 700; letter-spacing: .3px; font-size: 1.8rem; margin-bottom: .25rem; }
[data-testid="stFileUploaderDropzone"] { border: 2px dashed rgba(255,255,255,0.3); border-radius: 12px; padding: 1.5rem; }
[data-testid="stDataFrame"] div[role="grid"] { border-radius: 12px; }
.stProgress > div > div > div > div { background-color: #14b8a6; }
.brand-header { display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }
.brand-header img { max-height: 60px; height: auto; width: auto; max-width: 100%; border-radius: 8px; }
.brand-text { display: flex; flex-direction: column; }
.brand-text h1 { font-size: 1.8rem; margin: 0; font-weight: 700; }
.brand-text p { font-size: 1rem; margin: 0; color: #9ca3af; }

/* Mobile tweaks */
@media (max-width: 600px) {
    .brand-header { justify-content: center; text-align: center; }
    .brand-text { align-items: center; }
    .brand-text h1 { font-size: 1.4rem; }
    .brand-text p { font-size: 0.9rem; }
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# Agency signatures
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
    soup = BeautifulSoup(html, "html.parser")
    evidence = {}

    texts = []
    footer = soup.find("footer")
    if footer:
        texts.append(footer.get_text(" ", strip=True))
    for meta in soup.find_all("meta"):
        content = meta.get("content")
        if content:
            texts.append(str(content))
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        texts.append(str(comment))
    for tag in soup.find_all(["script", "link", "img"]):
        src = tag.get("src") or tag.get("href")
        if src:
            texts.append(str(src))

    full_text = " ".join(texts).lower()
    for agency, signatures in AGENCIES.items():
        for sig in signatures:
            if sig in full_text:
                kinds = []
                if any(x in full_text for x in (".js", ".css", "cdn", ".png", ".jpg", ".svg")):
                    kinds.append("asset")
                kinds.append("text")
                evidence[agency] = sorted(set(kinds))
                break
    return evidence

def run_scan(df: pd.DataFrame) -> pd.DataFrame:
    url_col = None
    for c in df.columns:
        if str(c).strip().lower() in ("url", "urls", "website", "domain"):
            url_col = c
            break
    if url_col is None:
        url_col = df.columns[0]

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
                headers={"User-Agent": "Mozilla/5.0"}
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
    # ---- Branded Header ----
    st.markdown("""
    <div class="brand-header">
        <img src="https://pbs.twimg.com/profile_images/1613686478852308992/UY_QrRVA_400x400.jpg" alt="Brand Logo">
        <div class="brand-text">
            <h1>Law Firm Website Agency Detector</h1>
            <p>Identify competitor-built law firm websites — instantly.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.header("Summary & Filters")

    # Sample CSV
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
        try:
            df = pd.read_csv(uploaded, encoding="utf-8", engine="python")
        except Exception:
            uploaded.seek(0)
            df = pd.read_csv(uploaded, encoding_errors="ignore", engine="python")

        st.success(f"Loaded {len(df)} rows.")
        st.dataframe(df.head(10), use_container_width=True)

        if st.button("▶️ Run scan"):
            result_df = run_scan(df)

            total_urls = len(df)
            detected_df = result_df[~result_df["Agency Detected"].isin(["None", "Error"])]
            detected_count = len(detected_df)
            rate = f"{(detected_count / total_urls * 100):.0f}%" if total_urls else "0%"

            st.sidebar.metric("Total URLs", total_urls)
            st.sidebar.metric("Detected", detected_count)
            st.sidebar.metric("Detection rate", rate)

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

            filtered = result_df.copy()
            if hide_none_error:
                filtered = filtered[~filtered["Agency Detected"].isin(["None", "Error"])]
            if selected_agencies:
                filtered = filtered[filtered["Agency Detected"].isin(selected_agencies)]

            st.success("✅ Done!")
            st.subheader("Results")
            st.dataframe(filtered if not filtered.empty else result_df, use_container_width=True)

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
