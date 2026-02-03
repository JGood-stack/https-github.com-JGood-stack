# ===============================================
# PFAS Ridgeline Tool — Robust Loader Version
# - Bulletproof header normalization & mapping
# - Works with CSV / TSV / Excel
# - Detects delimiter, strips BOM, handles & vs &amp;
# - Friendly schema validation + helpful errors
# - Keeps your original Altair theme & layout
# ===============================================

import io
import re
import streamlit as st
import pandas as pd
import altair as alt

# ------------------------------
# Streamlit Page Setup
# ------------------------------
st.set_page_config(
    page_title="PFAS Ridgeline Tool",
    page_icon="💧",
    layout="wide"
)

# ------------------------------
# Altair Global Font & Chart Size Theme
# ------------------------------
alt.themes.enable('none')  # remove Streamlit defaults

TITLE_FONT = 24
LABEL_FONT = 18

alt.themes.register(
    'large_theme',
    lambda: {
        "config": {
            "title": {"fontSize": TITLE_FONT},
            "axis": {"labelFontSize": LABEL_FONT, "titleFontSize": LABEL_FONT},
            "legend": {"labelFontSize": LABEL_FONT, "titleFontSize": LABEL_FONT},
            "view": {"continuousWidth": 900, "continuousHeight": 450}
        }
    }
)
alt.themes.enable('large_theme')

# ------------------------------
# Title
# ------------------------------
st.title("💧 PFAS Treatment Technologies — Ridgeline Visualization Tool")
st.markdown(
    "Upload your dataset and adjust the assumptions. "
    "Ridgeline plots show Score, GHG, Affordability, GEHH and Lifecycle Cost (Capital + O&M) for each technology."
)
st.divider()


# =====================================================
# Robust Loader + Header Normalization & Mapping
# =====================================================

REQUIRED = {
    # canonical internal names used by the app
    "tech",
    "score",
    "ghg",
    "affordability",
    "gehh",
    "lifecycle_cost",
}

# Optional fields used for filters (if present we enable related controls)
OPTIONAL = {
    "weighting_scheme",
    "region",
    "media_usage",
    "gac_disposal",
    "redundant_filter",
    "backwash_interval",
    "redundant_trains",
    "cleaning_chemicals",
}

# Build a mapping from many possible header variants -> canonical internal names.
# We map on a "normalized key" (lowercased, collapsed spaces, punctuation simplified).
HEADER_MAP = {
    # Required columns
    "tech": "tech",
    "score": "score",
    "ghg": "ghg",
    "affordability": "affordability",
    "gehh": "gehh",

    # Lifecycle cost: handle many variants (& vs &amp;, spaces, underscores, parentheses)
    "lifecycle cost (capital + o&m)": "lifecycle_cost",
    "lifecycle cost (capital + o & m)": "lifecycle_cost",
    "lifecycle cost (capital + oandm)": "lifecycle_cost",
    "lifecycle cost capital + o&m": "lifecycle_cost",
    "lifecycle_cost_(capital_+_o&m)": "lifecycle_cost",
    "lifecycle_cost_(capital_+_o & m)": "lifecycle_cost",
    "lifecycle cost": "lifecycle_cost",  # fallback if user shortens name
    "lifecycle_cost": "lifecycle_cost",
    "lifecycle cost (capital + o&amp;m)": "lifecycle_cost",
    "lifecycle_cost_(capital_+_o&amp;m)": "lifecycle_cost",

    # Optional columns
    "weighting scheme": "weighting_scheme",
    "weighting_scheme": "weighting_scheme",
    "weighting:": "weighting_scheme",
    "weighting": "weighting_scheme",

    "region": "region",

    "media usage": "media_usage",
    "media_usage": "media_usage",
    "media usa": "media_usage",  # truncated header seen in exports

    "gac disposal": "gac_disposal",
    "gac_disposal": "gac_disposal",

    "redundant filter": "redundant_filter",
    "redundant_filter": "redundant_filter",

    "backwash interval": "backwash_interval",
    "backwash_interval": "backwash_interval",

    "redundant trains": "redundant_trains",
    "redundant_trains": "redundant_trains",

    # Some datasets call this just "Chemicals"
    "cleaning chemicals": "cleaning_chemicals",
    "cleaning_chemicals": "cleaning_chemicals",
    "chemicals": "cleaning_chemicals",
}

def _norm_header_key(s: str) -> str:
    """Normalize a header string into a key we can reliably map."""
    if not isinstance(s, str):
        return s
    s = s.replace("\ufeff", "")  # strip BOM if any
    s = s.strip().lower()
    # HTML entity -> char
    s = s.replace("&amp;", "&")
    # collapse whitespace
    s = re.sub(r"\s+", " ", s)

    # For matching, remove most punctuation except '+' and '&' (we already normalized &amp;)
    # Keep words and spaces so keys like "lifecycle cost (capital + o&m)" match.
    s = s.replace("(", " ").replace(")", " ")
    s = s.replace("_", " ")
    s = re.sub(r"[^a-z0-9+& ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to canonical internal names used by the app."""
    original_cols = list(df.columns)
    new_cols = []
    for c in original_cols:
        key = _norm_header_key(c)
        # Direct map if known, otherwise keep a safe snake_case fallback
        if key in HEADER_MAP:
            new_cols.append(HEADER_MAP[key])
        else:
            # Safe fallback: snake_case made from normalized key
            snake = re.sub(r"[+&]", " ", key)              # turn +/& into words spaces
            snake = re.sub(r"\s+", "_", snake).strip("_")  # snake_case
            new_cols.append(snake)

    df.columns = new_cols
    # Drop empty/duplicate placeholders if any (common with "Unnamed: x" columns)
    df = df.loc[:, ~df.columns.isna()]
    return df

@st.cache_data(show_spinner=False)
def load_table(file) -> pd.DataFrame:
    """
    Load CSV/TSV/XLSX. Detect delimiter for CSV/TSV, strip BOM, canonicalize headers,
    and trim string cells.
    """
    # If it's an UploadedFile, grab the raw bytes (so we can sniff delimiters).
    if hasattr(file, "read"):
        raw = file.read()
        # reset so Streamlit can read again later if needed
        try:
            file.seek(0)
        except Exception:
            pass
    else:
        # Path-like (not typical when using file_uploader, but supported)
        with open(file, "rb") as f:
            raw = f.read()

    sample = raw[:4096].decode("utf-8", errors="replace")
    buf = io.BytesIO(raw)

    # Heuristic: more tabs than commas => TSV
    sep = "\t" if sample.count("\t") > sample.count(",") else ","

    # Try CSV/TSV first; if it fails, try Excel
    try:
        df = pd.read_csv(buf, sep=sep, header=0, dtype=str, encoding="utf-8-sig")
    except Exception:
        buf.seek(0)
        try:
            df = pd.read_excel(buf, sheet_name=0, header=0, engine="openpyxl", dtype=str)
        except Exception as e:
            raise RuntimeError(f"Could not read file as CSV/TSV or Excel. Details: {e}") from e

    # Normalize/rename headers to canonical internal names
    df = canonicalize_columns(df)

    # Trim whitespace in string cells
    df = df.apply(lambda s: s.str.strip() if s.dtype == "object" else s)

    return df


def coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ------------------------------
# File Upload
# ------------------------------
uploaded = st.file_uploader("📤 Upload PFAS CSV/TSV/Excel", type=["csv", "tsv", "txt", "xlsx"])
if not uploaded:
    st.warning("Awaiting file upload… (CSV/TSV/XLSX)")
    st.stop()

try:
    df = load_table(uploaded)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# Validate schema
missing = sorted(list(REQUIRED - set(df.columns)))
if missing:
    st.error(
        "Missing required columns after normalization: "
        + ", ".join(missing)
        + "\n\nDetected columns: "
        + ", ".join(sorted(df.columns))
    )
    st.stop()

# Convert numerics safely
df = coerce_numeric(
    df,
    [
        "media_usage", "redundant_filter", "backwash_interval",
        "redundant_trains", "cleaning_chemicals",
        "score", "ghg", "affordability", "gehh", "lifecycle_cost",
    ],
)

# Quick peek for debugging
with st.expander("🔍 See detected columns & first rows"):
    st.write("Detected columns (canonicalized):", list(df.columns))
    st.dataframe(df.head())


# ------------------------------
# Helper masks by technology
# ------------------------------
def make_masks(frame: pd.DataFrame):
    tech_series = frame["tech"].astype(str)
    gac_mask = tech_series.str.contains("GAC", case=False, na=False)
    ix_mask = tech_series.str.fullmatch("IX", case=False, na=False)
    ro_mask = tech_series.str.fullmatch("RO", case=False, na=False)
    nf_mask = tech_series.str.fullmatch("NF", case=False, na=False)
    return gac_mask, ix_mask, ro_mask, nf_mask


# ------------------------------
# SIDEBAR — Filters
# ------------------------------
st.sidebar.header("Overall Assumptions")

flow_rate = st.sidebar.slider("Flowrate (MGD)", 0.01, 10.0, 1.00, 0.01)

# Weighting Scheme dropdown (if present)
if "weighting_scheme" in df.columns:
    ws_options = sorted(df["weighting_scheme"].dropna().unique().tolist())
    weighting_scheme = st.sidebar.selectbox("Score Weighting Scheme", ["All"] + ws_options)
else:
    weighting_scheme = "All"

# Region dropdown (if present)
if "region" in df.columns:
    region_options = sorted(df["region"].dropna().unique().tolist())
    region_select = st.sidebar.selectbox("Electrical Grid Region", ["All"] + region_options)
else:
    region_select = "All"

st.sidebar.markdown("---")

# ------------------------------
# Media Treatment — GAC
# ------------------------------
st.sidebar.markdown("### 🌀 Media Treatment (GAC & IX)")
st.sidebar.markdown("#### GAC assumptions")

gac_mask, ix_mask, ro_mask, nf_mask = make_masks(df)

if "media_usage" in df.columns and gac_mask.any():
    gmin = float(pd.to_numeric(df.loc[gac_mask, "media_usage"], errors="coerce").min())
    gmax = float(pd.to_numeric(df.loc[gac_mask, "media_usage"], errors="coerce").max())
    gac_media_usage = st.sidebar.slider("Media Usage (lb/1000gal) — GAC", gmin, gmax, (gmin, gmax))
else:
    gac_media_usage = None

if "redundant_filter" in df.columns and gac_mask.any():
    rfmin = int(pd.to_numeric(df.loc[gac_mask, "redundant_filter"], errors="coerce").min())
    rfmax = int(pd.to_numeric(df.loc[gac_mask, "redundant_filter"], errors="coerce").max())
    gac_redundant_filters = st.sidebar.slider("Redundant Filters — GAC", rfmin, rfmax, (rfmin, rfmax))
else:
    gac_redundant_filters = None

if "backwash_interval" in df.columns and gac_mask.any():
    bwmin = float(pd.to_numeric(df.loc[gac_mask, "backwash_interval"], errors="coerce").min())
    bwmax = float(pd.to_numeric(df.loc[gac_mask, "backwash_interval"], errors="coerce").max())
    gac_backwash = st.sidebar.slider("Backwash Interval (hr) — GAC", bwmin, bwmax, (bwmin, bwmax))
else:
    gac_backwash = None

# GAC Disposal dropdown (if present)
if "gac_disposal" in df.columns:
    dispo_opts = sorted(df["gac_disposal"].dropna().astype(str).unique().tolist())
    gac_disposal_select = st.sidebar.selectbox("GAC Disposal", ["All"] + dispo_opts)
else:
    gac_disposal_select = "All"

st.sidebar.markdown("---")

# ------------------------------
# IX assumptions
# ------------------------------
st.sidebar.markdown("#### IX assumptions")

if "media_usage" in df.columns and ix_mask.any():
    ix_min = float(pd.to_numeric(df.loc[ix_mask, "media_usage"], errors="coerce").min())
    ix_max = float(pd.to_numeric(df.loc[ix_mask, "media_usage"], errors="coerce").max())
    ix_media_usage = st.sidebar.slider("Media Usage (lb/1000gal) — IX", ix_min, ix_max, (ix_min, ix_max))
else:
    ix_media_usage = None

if "redundant_filter" in df.columns and ix_mask.any():
    ix_rfmin = int(pd.to_numeric(df.loc[ix_mask, "redundant_filter"], errors="coerce").min())
    ix_rfmax = int(pd.to_numeric(df.loc[ix_mask, "redundant_filter"], errors="coerce").max())
    ix_redundant_filters = st.sidebar.slider("Redundant Filters — IX", ix_rfmin, ix_rfmax, (ix_rfmin, ix_rfmax))
else:
    ix_redundant_filters = None

if "backwash_interval" in df.columns and ix_mask.any():
    ix_bwmin = float(pd.to_numeric(df.loc[ix_mask, "backwash_interval"], errors="coerce").min())
    ix_bwmax = float(pd.to_numeric(df.loc[ix_mask, "backwash_interval"], errors="coerce").max())
    ix_backwash = st.sidebar.slider("Backwash Interval (hr) — IX", ix_bwmin, ix_bwmax, (ix_bwmin, ix_bwmax))
else:
    ix_backwash = None

st.sidebar.markdown("---")

# ------------------------------
# Membranes (RO & NF)
# ------------------------------
st.sidebar.markdown("### 🧪 Membrane Separation (RO & NF)")
st.sidebar.markdown("#### RO assumptions")

if "redundant_trains" in df.columns and ro_mask.any():
    rmin = int(pd.to_numeric(df.loc[ro_mask, "redundant_trains"], errors="coerce").min())
    rmax = int(pd.to_numeric(df.loc[ro_mask, "redundant_trains"], errors="coerce").max())
    ro_redundant_trains = st.sidebar.slider("Redundant Trains — RO", rmin, rmax, (rmin, rmax))
else:
    ro_redundant_trains = None

if "cleaning_chemicals" in df.columns and ro_mask.any():
    cmin = int(pd.to_numeric(df.loc[ro_mask, "cleaning_chemicals"], errors="coerce").min())
    cmax = int(pd.to_numeric(df.loc[ro_mask, "cleaning_chemicals"], errors="coerce").max())
    ro_cleaning_chems = st.sidebar.slider("Cleaning Chemicals — RO", cmin, cmax, (cmin, cmax))
else:
    ro_cleaning_chems = None

st.sidebar.markdown("---")

st.sidebar.markdown("#### NF assumptions")

if "redundant_trains" in df.columns and nf_mask.any():
    nfmin = int(pd.to_numeric(df.loc[nf_mask, "redundant_trains"], errors="coerce").min())
    nfmax = int(pd.to_numeric(df.loc[nf_mask, "redundant_trains"], errors="coerce").max())
    nf_redundant_trains = st.sidebar.slider("Redundant Trains — NF", nfmin, nfmax, (nfmin, nfmax))
else:
    nf_redundant_trains = None

if "cleaning_chemicals" in df.columns and nf_mask.any():
    nf_cmin = int(pd.to_numeric(df.loc[nf_mask, "cleaning_chemicals"], errors="coerce").min())
    nf_cmax = int(pd.to_numeric(df.loc[nf_mask, "cleaning_chemicals"], errors="coerce").max())
    nf_cleaning_chems = st.sidebar.slider("Cleaning Chemicals — NF", nf_cmin, nf_cmax, (nf_cmin, nf_cmax))
else:
    nf_cleaning_chems = None


# ------------------------------
# Apply Filters
# ------------------------------
filtered = df.copy()

# Global dropdowns first (only if columns exist)
if weighting_scheme != "All" and "weighting_scheme" in filtered.columns:
    filtered = filtered[filtered["weighting_scheme"] == weighting_scheme]

if region_select != "All" and "region" in filtered.columns:
    filtered = filtered[filtered["region"] == region_select]

if gac_disposal_select != "All" and "gac_disposal" in filtered.columns:
    # Apply only to GAC rows
    m_gac, _, _, _ = make_masks(filtered)
    filtered = filtered[(~m_gac) | (filtered["gac_disposal"] == gac_disposal_select)]

# Now compute masks on the filtered set for slider ranges
m_gac, m_ix, m_ro, m_nf = make_masks(filtered)

if gac_media_usage and "media_usage" in filtered.columns:
    filtered = filtered[(~m_gac) | (filtered["media_usage"].between(*gac_media_usage))]
if gac_redundant_filters and "redundant_filter" in filtered.columns:
    filtered = filtered[(~m_gac) | (filtered["redundant_filter"].between(*gac_redundant_filters))]
if gac_backwash and "backwash_interval" in filtered.columns:
    filtered = filtered[(~m_gac) | (filtered["backwash_interval"].between(*gac_backwash))]

if ix_media_usage and "media_usage" in filtered.columns:
    filtered = filtered[(~m_ix) | (filtered["media_usage"].between(*ix_media_usage))]
if ix_redundant_filters and "redundant_filter" in filtered.columns:
    filtered = filtered[(~m_ix) | (filtered["redundant_filter"].between(*ix_redundant_filters))]
if ix_backwash and "backwash_interval" in filtered.columns:
    filtered = filtered[(~m_ix) | (filtered["backwash_interval"].between(*ix_backwash))]

if ro_redundant_trains and "redundant_trains" in filtered.columns:
    filtered = filtered[(~m_ro) | (filtered["redundant_trains"].between(*ro_redundant_trains))]
if ro_cleaning_chems and "cleaning_chemicals" in filtered.columns:
    filtered = filtered[(~m_ro) | (filtered["cleaning_chemicals"].between(*ro_cleaning_chems))]

if nf_redundant_trains and "redundant_trains" in filtered.columns:
    filtered = filtered[(~m_nf) | (filtered["redundant_trains"].between(*nf_redundant_trains))]
if nf_cleaning_chems and "cleaning_chemicals" in filtered.columns:
    filtered = filtered[(~m_nf) | (filtered["cleaning_chemicals"].between(*nf_cleaning_chems))]

st.sidebar.write("Filtered Rows:", len(filtered))


# ------------------------------
# Ridgeline Chart Function — Enlarged
# ------------------------------
def ridgeline(df_in, xcol, title, xaxis_label):
    if df_in.empty:
        return alt.Chart().mark_text(text="No data").properties(height=200)

    tech_order = sorted(df_in["tech"].dropna().astype(str).unique().tolist())

    chart = (
        alt.Chart(df_in)
        .transform_density(
            xcol, groupby=["tech"],
            as_=[xcol, "density"], steps=40
        )
        .mark_area(opacity=0.7, stroke='black', strokeWidth=0.7)
        .encode(
            x=alt.X(f"{xcol}:Q", axis=alt.Axis(title=xaxis_label)),
            y=alt.Y("density:Q", axis=None),
            color=alt.Color("tech:N", legend=None)
        )
        .properties(width=900, height=120)
        .facet(
            row=alt.Row(
                "tech:N",
                sort=tech_order,
                header=alt.Header(labelFontSize=LABEL_FONT, labelAngle=0)
            )
        )
        .properties(title=title)
    )
    return chart


# ------------------------------
# TABS — Ridgeline Charts
# ------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Overall Score",
    "🌍 Global Warming Potential",
    "💰 Affordability",
    "📊 Global Environment & Human Health",
    "💰 Lifecycle Cost (Capital + O&M)"
])

with tab1:
    st.subheader("Overall Score (lower is better)")
    st.altair_chart(
        ridgeline(filtered, "score",
                  "Overall Score by Technology",
                  "Overall Score (lower is better)"),
        use_container_width=True
    )

with tab2:
    st.subheader("GHG (kgCO2e) (lower is better)")
    st.altair_chart(
        ridgeline(filtered, "ghg",
                  "GHG by Technology",
                  "GHG (kgCO2e) (lower is better)"),
        use_container_width=True
    )

with tab3:
    st.subheader("Affordability ($$) (lower is better)")
    st.altair_chart(
        ridgeline(filtered, "affordability",
                  "Affordability Score by Technology",
                  "Affordability ($$) (lower is better)"),
        use_container_width=True
    )

with tab4:
    st.subheader("Global Environment & Human Health (lower is better)")
    st.altair_chart(
        ridgeline(filtered, "gehh",
                  "GEHH Score by Technology",
                  "Score: Global Environment and Human Health (lower is better)"),
        use_container_width=True
    )

with tab5:
    st.subheader("Lifecycle Cost (Capital + O&M) ($$) (lower is better)")
    st.altair_chart(
        ridgeline(filtered, "lifecycle_cost",
                  "Lifecycle Cost Score by Technology",
                  "Lifecycle Cost ($$) (lower is better)"),
        use_container_width=True
    )

st.divider()
st.caption("PFAS Ridgeline Tool — University of Maine (2025)")
