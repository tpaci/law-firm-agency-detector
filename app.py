import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

# AGENCY SIGNATURES
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

def normalize_url(url):
    if not url.startswith("http"):
        return "http://" + url
    return url

def detect_agency(html):
    soup = BeautifulSoup(html, "html.parser")
    evidence = {}

    texts = []
    footer = soup.find("footer")
    if footer:
        texts.append(footer.get_text())

    for meta in soup.find_all("meta"):
        if meta.get("content"):
            texts.append(meta["content"])

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        texts.append(comment)

    for tag in soup.find_all(["script", "link", "img"]):
        src = tag.get("src") or tag.get("href")
        if src:
            texts.append(src)

    full_text = " ".join(texts).lower()

    for agency, signatures in AGENCIES.items():
        for sig in signatures:
            if sig in full_text:
                if agency not in evidence:
                    evidence[agency] = []
                if ".js" in full_text or ".css" in full_text or "cdn" in full_text:
                    evidence[agency].append("asset")
                else:
                    evidence[agency].append("text")
                break

    return evidence

def main():
    st.title("🏷️ Law Firm Website Agency Detector")
    st.markdown("Upload a CSV of law firm URLs to identify which digital marketing agency built each site.")

    uploaded_file = st.file_uploader("Upload a CSV file with a column of URLs", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if df.columns[0] != "URL":
            st.warning("Make sure the first column is named 'URL'")
            return

        results = []
        for url in df["URL"]:
            st.write(f"🔍 Checking: {url}")
            full_url = normalize_url(str(url))
            try:
                response = requests.get(full_url, timeout=10)
                if response.status_code == 200:
                    hits = detect_agency(response.text)
                    if hits:
                        for agency, methods in hits.items():
                            results.append({
                                "URL": url,
                                "Agency Detected": agency,
                                "Evidence Type": ", ".join(set(methods))
                            })
                    else:
                        results.append({
                            "URL": url,
                            "Agency Detected": "None",
                            "Evidence Type": ""
                        })
                else:
                    results.append({
                        "URL": url,
                        "Agency Detected": "Error",
                        "Evidence Type": f"HTTP {response.status_code}"
                    })
            except Exception as e:
                results.append({
                    "URL": url,
                    "Agency Detected": "Error",
                    "Evidence Type": str(e)
                })

        result_df = pd.DataFrame(results)
        st.success("✅ Done scanning!")

        st.dataframe(result_df)

        csv_download = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Results CSV", data=csv_download, file_name="agency_results.csv", mime="text/csv")

if __name__ == "__main__":
    main()
