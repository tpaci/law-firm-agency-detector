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
.title { font-weight: 700; letter-spacing: .2px; margin-bottom: .25rem; }
[data-testid="stFileUploaderDropzone"] { border: 1px dashed rgba(127,127,127,.35); border-radius: 12px; }
[data-testid="stDataFrame"] div[role="grid"] { border-radius: 12px; }
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
        if
