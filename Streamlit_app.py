# ===============================================
# pfas_tool_v11_ridgeline_fixed.py
# PFAS Ridgeline Tool (fixed version)
# Ensures GACg and GACp remain visible unless intentionally filtered
# ===============================================

import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="PFAS Ridgeline Tool", page_icon="💧", layout="wide")

# Title
st.title("💧 PFAS Treatment Technologies — Ridgeline Visualization Tool")
st.markdown(
    "Upload your dataset and adjust the assumptions. "
    "Ridgeline plots show Score, GHG, Affordability, and GEHH for each technology."
)
st.divider()

# ------------------------------
# File Upload
# ------------------------------
uploaded = st.file_uploader("📤 Upload PFAS CSV file", type=["csv"])
if not uploaded:
    st.warning("Awaiting CSV upload...")
    st.stop()

df = pd.read_csv(uploaded)
df.columns = df.columns.str.strip().str.replace(" ", "_")

required = ["Tech", "Score", "GHG", "Affordability", "GEHH"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"Missing required columns: {', '.join(missing)}")
    st.stop()

# ------------------------------
# Helper masks
# ------------------------------
gac_mask = df["Tech"].str.contains("GAC", case=False, na=False)
ix_mask  = df["Tech"].str.fullmatch("IX", case=False, na=False)
ro_mask  = df["Tech"].str.fullmatch("RO", case=False, na=False)
nf_mask  = df["Tech"].str.fullmatch("NF", case=False, na=False)

# ------------------------------
# SIDEBAR — Overall Assumptions
# ------------------------------
st.sidebar.header("Overall Assumptions")

flow_rate = st.sidebar.slider("Flowrate (MGD)", 0.01, 10.0, 1.00, 0.01)


# Score Weighting Scheme
if "Weighting_Scheme" in df.columns:
    ws_min = int(df["Weighting_Scheme"].min())
    ws_max = int(df["Weighting_Scheme"].max())
    weighting_scheme = st.sidebar.slider(
        "Score Weighting Scheme (single value)", ws_min, ws_max, ws_min, 1
    )
else:
    weighting_scheme = None

# Region select
if "Region" in df.columns:
    region_options = sorted(df["Region"].dropna().unique().tolist())
    region_options = ["All"] + region_options
    region_select = st.sidebar.selectbox("Electrical Grid Region", region_options)
else:
    region_select = "All"

st.sidebar.markdown("---")

# ------------------------------
# Media Treatment — GAC / IX
# ------------------------------
st.sidebar.markdown("### 🌀 Media Treatment (GAC & IX)")

### -------- GAC --------
st.sidebar.markdown("#### GAC assumptions")

# Media Usage — GAC
if "Media_Usage" in df.columns and gac_mask.any():
    gmin = float(df.loc[gac_mask, "Media_Usage"].min())
    gmax = float(df.loc[gac_mask, "Media_Usage"].max())
    gac_media_usage = st.sidebar.slider(
        "Media Usage (lb/1000 gal) — GAC", gmin, gmax, (gmin, gmax)
    )
else:
    gac_media_usage = None

# Redundant Filter — GAC
if "Redundant_Filter" in df.columns and gac_mask.any():
    rfmin = int(df.loc[gac_mask, "Redundant_Filter"].min())
    rfmax = int(df.loc[gac_mask, "Redundant_Filter"].max())
    gac_redundant_filters = st.sidebar.slider(
        "Number of Redundant Filters — GAC", rfmin, rfmax, rfmin
    )
else:
    gac_redundant_filters = None

# Backwash Interval — GAC
if "Backwash_Interval" in df.columns and gac_mask.any():
    bwmin = float(df.loc[gac_mask, "Backwash_Interval"].min())
    bwmax = float(df.loc[gac_mask, "Backwash_Interval"].max())
    gac_backwash = st.sidebar.slider(
        "Backwash Interval (hours) — GAC", bwmin, bwmax, bwmin
    )
else:
    gac_backwash = None

# GAC Disposal
if "GAC_Disposal" in df.columns:
    dispo_options = ["All"] + sorted(df["GAC_Disposal"].dropna().unique().tolist())
    gac_disposal_select = st.sidebar.selectbox("GAC Disposal", dispo_options)
else:
    gac_disposal_select = "All"

st.sidebar.markdown("---")

### -------- IX --------
st.sidebar.markdown("#### IX assumptions")

if "Media_Usage" in df.columns and ix_mask.any():
    ix_min = float(df.loc[ix_mask, "Media_Usage"].min())
    ix_max = float(df.loc[ix_mask, "Media_Usage"].max())
    ix_media_usage = st.sidebar.slider(
        "Media Usage (lb/1000 gal) — IX", ix_min, ix_max, (ix_min, ix_max)
    )
else:
    ix_media_usage = None

if "Redundant_Filter" in df.columns and ix_mask.any():
    ix_rfmin = int(df.loc[ix_mask, "Redundant_Filter"].min())
    ix_rfmax = int(df.loc[ix_mask, "Redundant_Filter"].max())
    ix_redundant_filters = st.sidebar.slider(
        "Number of Redundant Filters — IX", ix_rfmin, ix_rfmax, ix_rfmin
    )
else:
    ix_redundant_filters = None

if "Backwash_Interval" in df.columns and ix_mask.any():
    ix_bwmin = float(df.loc[ix_mask, "Backwash_Interval"].min())
    ix_bwmax = float(df.loc[ix_mask, "Backwash_Interval"].max())
    ix_backwash = st.sidebar.slider(
        "Backwash Interval (hours) — IX", ix_bwmin, ix_bwmax, ix_bwmin
    )
else:
    ix_backwash = None

st.sidebar.markdown("---")

# ------------------------------
# Membrane Separation — RO / NF
# ------------------------------
st.sidebar.markdown("### 🧪 Membrane Separation (RO & NF)")

### -------- RO --------
st.sidebar.markdown("#### RO assumptions")

if "Redundant_Trains" in df.columns and ro_mask.any():
    rmin = int(df.loc[ro_mask, "Redundant_Trains"].min())
    rmax = int(df.loc[ro_mask, "Redundant_Trains"].max())
    ro_redundant_trains = st.sidebar.slider(
        "Redundant Trains — RO", rmin, rmax, rmin
    )
else:
    ro_redundant_trains = None

if "Cleaning_Chemicals" in df.columns and ro_mask.any():
    cmin = int(df.loc[ro_mask, "Cleaning_Chemicals"].min())
    cmax = int(df.loc[ro_mask, "Cleaning_Chemicals"].max())
    ro_cleaning_chems = st.sidebar.slider(
        "Cleaning Chemicals — RO", cmin, cmax, cmin
    )
else:
    ro_cleaning_chems = None

st.sidebar.markdown("---")

### -------- NF --------
st.sidebar.markdown("#### NF assumptions")

if "Redundant_Trains" in df.columns and nf_mask.any():
    nfmin = int(df.loc[nf_mask, "Redundant_Trains"].min())
    nfmax = int(df.loc[nf_mask, "Redundant_Trains"].max())
    nf_redundant_trains = st.sidebar.slider(
        "Redundant Trains — NF", nfmin, nfmax, nfmin
    )
else:
    nf_redundant_trains = None

if "Cleaning_Chemicals" in df.columns and nf_mask.any():
    nf_cmin = int(df.loc[nf_mask, "Cleaning_Chemicals"].min())
    nf_cmax = int(df.loc[nf_mask, "Cleaning_Chemicals"].max())
    nf_cleaning_chems = st.sidebar.slider(
        "Cleaning Chemicals — NF", nf_cmin, nf_cmax, nf_cmin
    )
else:
    nf_cleaning_chems = None


# ------------------------------
# Filtering Logic (fixed)
# ------------------------------
filtered = df.copy()

# Weighting Scheme
if weighting_scheme is not None:
    filtered = filtered[filtered["Weighting_Scheme"] == weighting_scheme]

# Region
if region_select != "All":
    filtered = filtered[filtered["Region"] == region_select]

# GAC Disposal (apply ONLY to GAC rows)
if gac_disposal_select != "All":
    filtered = filtered[
        (~gac_mask) |
        (filtered["GAC_Disposal"] == gac_disposal_select)
    ]

# GAC media usage range
if gac_media_usage:
    lo, hi = gac_media_usage
    filtered = filtered[(~gac_mask) | (filtered["Media_Usage"].between(lo, hi))]

# IX media usage
if ix_media_usage:
    lo, hi = ix_media_usage
    filtered = filtered[(~ix_mask) | (filtered["Media_Usage"].between(lo, hi))]

# RO cleaning chemicals
if ro_cleaning_chems is not None:
    filtered = filtered[(~ro_mask) | (filtered["Cleaning_Chemicals"] == ro_cleaning_chems)]

# NF cleaning chemicals
if nf_cleaning_chems is not None:
    filtered = filtered[(~nf_mask) | (filtered["Cleaning_Chemicals"] == nf_cleaning_chems)]


st.sidebar.write("Filtered Rows:", len(filtered))

# ------------------------------
# Ridgeline Function
# ------------------------------
def ridgeline(df_in, xcol, title):
    if df_in.empty:
        return alt.Chart().mark_text(text="No data").properties(height=200)

    tech_order = sorted(df_in["Tech"].unique())

    chart = (
        alt.Chart(df_in, height=60)
        .transform_density(
            xcol, groupby=["Tech"],
            as_=[xcol, "density"], steps=20
        )
        .mark_area(opacity=0.7, stroke = 'black', strokeWidth=0.5)
        .encode(
            x=alt.X(xcol + ":Q"),
            y=alt.Y("density:Q", axis=None),
            color=alt.Color("Tech:N", legend=None),
        )
        .facet(
            row=alt.Row("Tech:N", sort=tech_order, header=alt.Header(labelAngle=0))
        )
        .properties(title=title)
    )
    return chart


# ------------------------------
# TABS (Ridgeline outputs)
# ------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Overall Score",
    "🌍 Global Warming Potential",
    "📊 Global Environment and Human Health",
    "💰 Life Cycle Cost"
])

with tab1:
    st.subheader("Score Distribution")
    st.altair_chart(ridgeline(filtered, "Score", "Score by Technology"), use_container_width=True)

with tab2:
    st.subheader("GHG Distribution")
    st.altair_chart(ridgeline(filtered, "GHG", "GHG by Technology"), use_container_width=True)

with tab3:
    st.subheader("GEHH Distribution")
    st.altair_chart(ridgeline(filtered, "GEHH", "GEHH by Technology"), use_container_width=True)

with tab4:
    st.subheader("Affordability Distribution")
    st.altair_chart(ridgeline(filtered, "Affordability", "Affordability by Technology"), use_container_width=True)

st.divider()
st.caption("PFAS Ridgeline Tool — University of Maine (2025)")
