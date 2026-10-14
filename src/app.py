import base64
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import cv2
import pandas as pd
import streamlit as st

# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "data", "uploads")
EVENTS_FILE = os.path.join(BASE_DIR, "data", "events.csv")
SNAPSHOT_FOLDER = os.path.join(BASE_DIR, "outputs", "snapshots")
EVENTS_FOLDER = os.path.join(BASE_DIR, "outputs", "events")
SUMMARY_FOLDER = os.path.join(BASE_DIR, "outputs", "summaries")
METADATA_FILE = os.path.join(SUMMARY_FOLDER, "metadata.json")
SUMMARY_HTML = os.path.join(SUMMARY_FOLDER, "summary.html")
PROCESS_SCRIPT = os.path.join(BASE_DIR, "src", "process_video.py")

SUMMARY_VIDEO_BROWSER = os.path.join(
    SUMMARY_FOLDER, "Forensic_Annotated_Summary_browser.mp4"
)
SUMMARY_VIDEO_ORIGINAL = os.path.join(
    SUMMARY_FOLDER, "Forensic_Annotated_Summary.mp4"
)
SUMMARY_VIDEO = (
    SUMMARY_VIDEO_BROWSER
    if os.path.isfile(SUMMARY_VIDEO_BROWSER)
    else SUMMARY_VIDEO_ORIGINAL
)

# Design tokens
NAVY = "#0B1F3A"
NAVY_2 = "#142B4D"
BLUE = "#2563EB"
BLUE_SOFT = "#E8EFFD"
AMBER = "#D97706"
RED = "#C62828"
GREEN = "#15803D"
CANVAS = "#F1F4F9"
INK = "#0F172A"
MUTED = "#64748B"
LINE = "#DDE3EC"

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CCTV Forensic Investigation System",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# STYLES
# ============================================================

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{
        font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }}
    #MainMenu, footer {{ visibility: hidden; }}
    .stApp {{ background: {CANVAS}; }}
    .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }}

    /* -------- SIDEBAR (scoped, no leaks) -------- */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {NAVY} 0%, {NAVY_2} 100%);
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] * {{
        color: #E2E8F0;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] hr {{
        border-color: rgba(255,255,255,0.12);
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] .stCaption,
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] small {{
        color: #94A3B8 !important;
    }}

    /* -------- BRAND -------- */
    .brand {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 6px 0 4px 0;
    }}
    .brand-mark {{
        width: 38px;
        height: 38px;
        border-radius: 9px;
        background: {BLUE};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }}
    .brand-name {{
        font-size: 16px;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
    }}
    .brand-sub {{ font-size: 12px; color: #94A3B8; }}
    .side-row {{
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        padding: 5px 0;
    }}
    .side-row span:last-child {{
        font-weight: 600;
        color: #FFFFFF;
    }}

    /* -------- TOP BAR -------- */
    .topbar {{
        background: #FFFFFF;
        border: 1px solid {LINE};
        border-radius: 10px;
        padding: 18px 24px;
        margin-bottom: 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .topbar h1 {{
        font-size: 24px;
        font-weight: 700;
        color: {INK};
        margin: 0;
        padding: 0;
        letter-spacing: -0.2px;
    }}
    .topbar p {{
        margin: 2px 0 0 0;
        color: {MUTED};
        font-size: 14px;
    }}
    .topbar .meta {{
        text-align: right;
        font-size: 13px;
        color: {MUTED};
    }}
    .topbar .meta b {{ color: {INK}; }}

    /* -------- PILLS -------- */
    .pill {{
        display: inline-block;
        padding: 3px 11px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }}
    .pill-green {{ background: #DCFCE7; color: {GREEN}; }}
    .pill-amber {{ background: #FEF3C7; color: #92400E; }}
    .pill-red {{ background: #FEE2E2; color: {RED}; }}
    .pill-blue {{ background: {BLUE_SOFT}; color: {BLUE}; }}
    .pill-grey {{ background: #E2E8F0; color: #334155; }}

    /* -------- KPI CARDS -------- */
    .kpi {{
        background: #FFFFFF;
        border: 1px solid {LINE};
        border-left: 4px solid {BLUE};
        border-radius: 10px;
        padding: 16px 18px;
        height: 100%;
    }}
    .kpi.amber {{ border-left-color: {AMBER}; }}
    .kpi.red {{ border-left-color: {RED}; }}
    .kpi.green {{ border-left-color: {GREEN}; }}
    .kpi-label {{
        font-size: 13px;
        color: {MUTED};
        font-weight: 500;
    }}
    .kpi-value {{
        font-size: 28px;
        font-weight: 700;
        color: {INK};
        line-height: 1.25;
    }}
    .kpi-note {{ font-size: 12px; color: {MUTED}; margin-top: 2px; }}

    /* -------- PANELS & TEXT -------- */
    .panel {{
        background: #FFFFFF;
        border: 1px solid {LINE};
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 14px;
    }}
    .panel-title {{
        font-size: 15px;
        font-weight: 700;
        color: {INK};
        margin-bottom: 8px;
    }}
    .panel p, .panel li {{ color: #334155; font-size: 14px; }}
    .rule-box {{
        background: {BLUE_SOFT};
        border: 1px solid #C7D8FB;
        border-radius: 8px;
        padding: 12px 16px;
        color: {NAVY};
        font-size: 14px;
    }}
    .insight {{
        border-left: 3px solid {BLUE};
        background: #F8FAFC;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
        font-size: 14px;
        color: #1E293B;
    }}
    .hash {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 12px;
        color: #334155;
        word-break: break-all;
        background: #F1F5F9;
        padding: 6px 8px;
        border-radius: 6px;
    }}

    /* -------- TABS (force readable colours) -------- */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        border-bottom: 1px solid {LINE};
        background: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-weight: 600;
        padding: 10px 18px;
        background: transparent;
        color: {MUTED} !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {INK} !important;
    }}
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [data-baseweb="tab"] div {{
        color: inherit !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {BLUE} !important;
    }}
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] span,
    .stTabs [aria-selected="true"] div {{
        color: {BLUE} !important;
    }}

    /* -------- EXPANDER -------- */
    div[data-testid="stExpander"] {{
        background: #FFFFFF;
        border: 1px solid {LINE};
        border-radius: 10px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# COMPATIBILITY HELPERS
# ============================================================

def show_image(image, caption=None):
    try:
        st.image(image, caption=caption, width="stretch")
    except TypeError:
        st.image(image, caption=caption, use_container_width=True)


def show_df(df, **kwargs):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


def primary_button(label, **kwargs):
    try:
        return st.button(label, type="primary", width="stretch", **kwargs)
    except TypeError:
        return st.button(label, type="primary", use_container_width=True, **kwargs)


# ============================================================
# DATA LAYER
# ============================================================

def file_mtime(path):
    return os.path.getmtime(path) if os.path.exists(path) else 0


def fmt_time(seconds):
    """Format seconds as MM:SS.SS. Defined before any tab uses it."""
    if pd.isna(seconds):
        return "-"
    minutes, secs = divmod(float(seconds), 60)
    return f"{int(minutes):02d}:{secs:05.2f}"


@st.cache_data(show_spinner=False)
def load_events(path, mtime):
    columns = ["No", "Event Type", "Object ID", "Frame", "Time (s)", "Snapshot"]

    if not os.path.exists(path):
        return pd.DataFrame(columns=columns)

    rows = []
    with open(path, "r", newline="", encoding="utf-8", errors="ignore") as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader, start=1):
            no = pd.to_numeric(
                row.get("Event Number") or row.get("No"), errors="coerce"
            )
            frame = pd.to_numeric(
                row.get("Frame Number") or row.get("Frame"), errors="coerce"
            )
            ts = pd.to_numeric(
                row.get("Timestamp (seconds)") or row.get("Time (s)"),
                errors="coerce",
            )
            snapshot = (row.get("Snapshot") or "").strip()

            rows.append({
                "No": int(no) if pd.notna(no) else i,
                "Event Type": (row.get("Event Type") or "").strip(),
                "Object ID": (row.get("Object ID") or "").strip(),
                "Frame": frame,
                "Time (s)": ts,
                "Snapshot": snapshot if snapshot else f"event_{i:04d}.jpg",
            })

    return pd.DataFrame(rows, columns=columns)


@st.cache_data(show_spinner=False)
def video_info(upload_folder, mtime):
    info = {"name": None, "frames": None, "duration": None, "fps": None,
            "width": None, "height": None}

    if not os.path.isdir(upload_folder):
        return info

    videos = [
        os.path.join(upload_folder, name)
        for name in os.listdir(upload_folder)
        if name.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
    ]
    if not videos:
        return info

    latest = max(videos, key=os.path.getmtime)
    info["name"] = os.path.basename(latest)

    try:
        cap = cv2.VideoCapture(latest)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        if frames > 0 and fps and fps > 0:
            info.update(
                frames=frames,
                fps=round(fps, 2),
                duration=round(frames / fps, 2),
                width=width,
                height=height,
            )
    except Exception:
        pass

    return info


def load_metadata():
    if not os.path.isfile(METADATA_FILE):
        return None
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_files(folder, extensions):
    if not os.path.isdir(folder):
        return 0
    return sum(
        1 for name in os.listdir(folder)
        if name.lower().endswith(extensions)
    )


def clip_path_for(no):
    """Return the current clip for an event, converting to browser H.264 if needed."""
    browser_clip = os.path.join(EVENTS_FOLDER, f"event_{no:04d}_browser.mp4")
    original_clip = os.path.join(EVENTS_FOLDER, f"event_{no:04d}.mp4")

    if not os.path.isfile(original_clip):
        alt = os.path.join(EVENTS_FOLDER, f"event_{no:02d}.mp4")
        if os.path.isfile(alt):
            original_clip = alt

    if not os.path.isfile(original_clip):
        return browser_clip if os.path.isfile(browser_clip) else original_clip

    if (not os.path.isfile(browser_clip)
            or os.path.getmtime(browser_clip) < os.path.getmtime(original_clip)):
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run(
                [ffmpeg, "-y", "-i", original_clip, "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
                 browser_clip],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            return original_clip

    return browser_clip if os.path.isfile(browser_clip) else original_clip


def snapshot_path_for(name):
    return os.path.join(SNAPSHOT_FOLDER, name)


def build_object_table(df):
    if df.empty:
        return pd.DataFrame()

    table = df.groupby("Object ID").agg(
        Events=("No", "count"),
        First_Seen=("Time (s)", "min"),
        Last_Seen=("Time (s)", "max"),
        First_Frame=("Frame", "min"),
        Last_Frame=("Frame", "max"),
    ).reset_index()

    table["Span (s)"] = (table["Last_Seen"] - table["First_Seen"]).round(2)
    table = table.rename(columns={
        "First_Seen": "First Seen (s)",
        "Last_Seen": "Last Seen (s)",
        "First_Frame": "First Frame",
        "Last_Frame": "Last Frame",
    })
    return table.sort_values("Events", ascending=False).reset_index(drop=True)


def risk_level(events_for_object):
    if events_for_object >= 10:
        return "High"
    if events_for_object >= 4:
        return "Medium"
    return "Low"


def make_evidence_zip(df):
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if os.path.isfile(EVENTS_FILE):
            archive.write(EVENTS_FILE, "events.csv")

        for _, row in df.iterrows():
            snapshot = snapshot_path_for(row["Snapshot"])
            if os.path.isfile(snapshot):
                archive.write(snapshot, f"snapshots/{row['Snapshot']}")

            clip = clip_path_for(int(row["No"]))
            if os.path.isfile(clip):
                archive.write(
                    clip, f"clips/event_{int(row['No']):04d}.mp4"
                )

        if os.path.isfile(SUMMARY_VIDEO):
            archive.write(
                SUMMARY_VIDEO,
                f"summary/{os.path.basename(SUMMARY_VIDEO)}",
            )

        if os.path.isfile(METADATA_FILE):
            archive.write(METADATA_FILE, "summaries/metadata.json")

    buffer.seek(0)
    return buffer.getvalue()


def make_html_report(df, vinfo, case_id, meta=None):
    rows = ""
    for _, row in df.iterrows():
        frame = "" if pd.isna(row["Frame"]) else int(row["Frame"])
        rows += (
            f"<tr><td>{int(row['No']):02d}</td>"
            f"<td>{row['Event Type']}</td>"
            f"<td>{row['Object ID']}</td>"
            f"<td>{frame}</td>"
            f"<td>{row['Time (s)']}</td></tr>"
        )

    images = ""
    for _, row in df.iterrows():
        snapshot = snapshot_path_for(row["Snapshot"])
        if os.path.isfile(snapshot):
            with open(snapshot, "rb") as file:
                encoded = base64.b64encode(file.read()).decode()
            images += (
                '<div class="ev">'
                f'<img src="data:image/jpeg;base64,{encoded}"/>'
                f"<p>Event {int(row['No']):02d} — Person {row['Object ID']} "
                f"— {row['Time (s)']} s</p></div>"
            )

    csv_hash = sha256_of(EVENTS_FILE) if os.path.isfile(EVENTS_FILE) else "n/a"
    video_hash = (meta or {}).get("video_sha256", "n/a")
    object_count = df["Object ID"].nunique() if not df.empty else 0

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Forensic Report {case_id}</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; color: #0F172A; margin: 40px; }}
h1 {{ margin-bottom: 0; }}
.sub {{ color: #64748B; margin-top: 4px; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #DDE3EC; padding: 8px 10px; text-align: left; font-size: 14px; }}
th {{ background: #0B1F3A; color: #fff; }}
.grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
.ev img {{ width: 100%; border: 1px solid #DDE3EC; border-radius: 6px; }}
.ev p {{ font-size: 13px; color: #475569; margin: 4px 0 0; }}
code {{ background: #F1F5F9; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
@media print {{ body {{ margin: 15mm; }} .grid {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<h1>CCTV Forensic Investigation Report</h1>
<p class="sub">Case {case_id} · Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<h2>Summary</h2>
<ul>
<li>Source video: {vinfo.get('name') or 'n/a'}</li>
<li>Detection rule: person enters the predefined restricted area</li>
<li>Detection method: YOLO + ByteTrack</li>
<li>Events: {len(df)} · Tracked persons: {object_count}</li>
<li>Source video SHA-256: <code>{video_hash}</code></li>
<li>Event log SHA-256: <code>{csv_hash}</code></li>
</ul>
<h2>Event log</h2>
<table><tr><th>#</th><th>Event</th><th>Person</th><th>Frame</th><th>Time (s)</th></tr>
{rows}
</table>
<h2>Evidence snapshots</h2>
<div class="grid">{images}</div>
</body>
</html>"""


# ============================================================
# LOAD DATA
# ============================================================

all_events = load_events(EVENTS_FILE, file_mtime(EVENTS_FILE))
vinfo = video_info(UPLOAD_FOLDER, file_mtime(UPLOAD_FOLDER))
metadata = load_metadata()
has_data = not all_events.empty

n_snapshots = count_files(SNAPSHOT_FOLDER, (".jpg", ".jpeg", ".png"))
n_clips = sum(
    1 for no in all_events["No"].tolist()
    if os.path.isfile(
        os.path.join(EVENTS_FOLDER, f"event_{int(no):04d}.mp4")
    ) or os.path.isfile(
        os.path.join(EVENTS_FOLDER, f"event_{int(no):02d}.mp4")
    )
) if has_data else 0

case_id = (
    datetime.fromtimestamp(file_mtime(EVENTS_FILE)).strftime("CASE-%Y%m%d-%H%M")
    if has_data else "CASE-PENDING"
)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-mark">🔎</div>
            <div>
                <div class="brand-name">Forensic Console</div>
                <div class="brand-sub">CCTV investigation platform</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("**Analysis status**")

    if has_data:
        st.markdown(
            '<span class="pill pill-green">Analysis complete</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="pill pill-amber">Awaiting video</span>',
            unsafe_allow_html=True,
        )

    unique_persons = (
        int(metadata.get("unique_tracked_ids", 0))
        if metadata else (all_events["Object ID"].nunique() if has_data else 0)
    )

    st.markdown(
        f"""
        <div style="margin-top:10px">
            <div class="side-row"><span>Case ID</span><span>{case_id}</span></div>
            <div class="side-row"><span>Events logged</span><span>{len(all_events)}</span></div>
            <div class="side-row"><span>Unique persons</span><span>{unique_persons}</span></div>
            <div class="side-row"><span>Snapshots</span><span>{n_snapshots}</span></div>
            <div class="side-row"><span>Event clips</span><span>{n_clips}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sel_objects = []
    time_range = None

    if has_data:
        st.divider()
        st.markdown("**Filters**")

        object_options = sorted(
            all_events["Object ID"].unique(),
            key=lambda x: (len(str(x)), str(x)),
        )
        sel_objects = st.multiselect(
            "Person ID",
            object_options,
            placeholder="All persons",
        )

        t_min = float(all_events["Time (s)"].min())
        t_max = float(all_events["Time (s)"].max())
        if t_max > t_min:
            time_range = st.slider(
                "Time window (s)",
                min_value=float(int(t_min)),
                max_value=float(int(t_max) + 1),
                value=(float(int(t_min)), float(int(t_max) + 1)),
            )

    st.divider()
    st.caption("YOLO + ByteTrack · Automated event detection")

# ============================================================
# APPLY FILTERS
# ============================================================

events = all_events.copy()

if has_data:
    if sel_objects:
        events = events[events["Object ID"].isin(sel_objects)]
    if time_range:
        events = events[
            (events["Time (s)"] >= time_range[0])
            & (events["Time (s)"] <= time_range[1])
        ]

filtered = len(events) != len(all_events)

# ============================================================
# HEADER
# ============================================================

status_pill = (
    '<span class="pill pill-green">Complete</span>'
    if has_data else '<span class="pill pill-amber">Awaiting video</span>'
)

st.markdown(
    f"""
    <div class="topbar">
        <div>
            <h1>CCTV Forensic Investigation System</h1>
            <p>Automated video analysis, event detection and digital evidence extraction</p>
        </div>
        <div class="meta">
            {status_pill}<br>
            <span>Case <b>{case_id}</b></span><br>
            <span>Source: <b>{vinfo.get("name") or "no video uploaded"}</b></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# UPLOAD & ANALYSIS
# ============================================================

session_key_roi = "roi_default"

if has_data:
    st.info(
        "ℹ️ **A previous analysis is loaded.** "
        "Expand **➕ Analyse a new video** below to upload a different clip. "
        "Starting a new run replaces the current evidence automatically."
    )

expander_title = (
    "➕ Analyse a new video"
    if has_data
    else "➕ Analyse a new video (start here)"
)

with st.expander(expander_title, expanded=not has_data):
    left, right = st.columns([1, 1])

    with left:
        uploaded_video = st.file_uploader(
            "Select CCTV video",
            type=["mp4", "avi", "mov", "mkv"],
            help="Supported formats: MP4, AVI, MOV, MKV",
        )

    with right:
        if uploaded_video is not None:
            st.markdown(
                f"**File:** {uploaded_video.name}  \n"
                f"**Size:** {round(uploaded_video.size / (1024 * 1024), 2)} MB"
            )
            st.video(uploaded_video)
        else:
            st.caption("Choose a video to preview it here before analysis.")

    if uploaded_video is not None:
        st.markdown("**Restricted area (rectangular ROI)**")
        st.caption(
            "Enter pixel coordinates from the top-left of the frame. "
            "The red box is drawn at the moment each event fires."
        )

        tmp_bytes = uploaded_video.getvalue()
        tmp_path = os.path.join(UPLOAD_FOLDER, uploaded_video.name)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        if not os.path.isfile(tmp_path):
            with open(tmp_path, "wb") as file:
                file.write(tmp_bytes)

        probe = cv2.VideoCapture(tmp_path)
        vw = int(probe.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
        vh = int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
        probe.release()

        defaults = st.session_state.get(session_key_roi) or {
            "x": min(270, vw - 1),
            "y": min(390, vh - 1),
            "w": min(540, vw),
            "h": min(460, vh),
        }

        r1, r2, r3, r4 = st.columns(4)
        with r1:
            roi_x = st.number_input("X", 0, vw - 1,
                                    min(int(defaults["x"]), vw - 1), step=10)
        with r2:
            roi_y = st.number_input("Y", 0, vh - 1,
                                    min(int(defaults["y"]), vh - 1), step=10)
        with r3:
            roi_w = st.number_input("Width", 1, vw,
                                    min(int(defaults["w"]), vw), step=10)
        with r4:
            roi_h = st.number_input("Height", 1, vh,
                                    min(int(defaults["h"]), vh), step=10)

        roi_valid = (roi_x + roi_w <= vw) and (roi_y + roi_h <= vh)

        if roi_valid:
            cap = cv2.VideoCapture(tmp_path)
            ok, frame = cap.read()
            cap.release()
            if ok:
                cv2.rectangle(frame, (int(roi_x), int(roi_y)),
                              (int(roi_x + roi_w), int(roi_y + roi_h)),
                              (0, 0, 255), 3)
                cv2.putText(frame, "RESTRICTED AREA",
                            (int(roi_x), max(25, int(roi_y) - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            (0, 0, 255), 2)
                show_image(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                    caption=f"Red rectangle = restricted area · "
                            f"video {vw}×{vh}",
                )
        else:
            st.error("The ROI extends outside the video frame.")

        if roi_valid and primary_button("Start forensic analysis"):
            video_path = os.path.join(
                UPLOAD_FOLDER, os.path.basename(uploaded_video.name)
            )
            with open(video_path, "wb") as file:
                file.write(uploaded_video.getbuffer())

            st.session_state[session_key_roi] = {
                "x": int(roi_x), "y": int(roi_y),
                "w": int(roi_w), "h": int(roi_h),
            }

            progress_bar = st.progress(0, text="Starting analysis…")
            log_box = st.empty()
            log_lines = []

            command = [
                sys.executable,
                "-u",
                PROCESS_SCRIPT,
                video_path,
                str(int(roi_x)), str(int(roi_y)),
                str(int(roi_w)), str(int(roi_h)),
            ]

            returncode = -1
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=BASE_DIR,
                    bufsize=1,
                )

                for line in process.stdout:
                    line = line.rstrip()
                    if not line:
                        continue

                    if line.startswith("Progress:"):
                        try:
                            head = line.split("Progress:")[1].split("(")[0].strip()
                            done_str, total_str = head.split("/")
                            done = int(done_str.strip())
                            total = int(total_str.strip().split()[0])
                            fraction = min(1.0, done / max(1, total))
                            progress_bar.progress(
                                fraction,
                                text=f"Analysing… {done}/{total} samples "
                                     f"({fraction*100:.0f}%)",
                            )
                        except (ValueError, IndexError):
                            pass
                        continue

                    log_lines.append(line)
                    log_box.code("\n".join(log_lines[-15:]), language=None)

                process.wait()
                returncode = process.returncode

            except Exception as error:
                progress_bar.empty()
                st.error(f"Could not run processing: {error}")
                returncode = -1

            if returncode == 0:
                progress_bar.progress(1.0, text="Analysis complete")
                st.success("Forensic analysis complete. Refreshing dashboard…")
                st.cache_data.clear()
                st.rerun()
            else:
                progress_bar.empty()
                st.error("Video processing failed. See log above.")
                st.stop()

    if has_data:
        st.divider()
        st.caption(
            "Or clear the currently loaded evidence without uploading a new "
            "video. Source files in `data/uploads/` are preserved."
        )
        if st.button("🗑 Clear current evidence"):
            try:
                if os.path.isfile(EVENTS_FILE):
                    os.remove(EVENTS_FILE)
                for folder in (SNAPSHOT_FOLDER, EVENTS_FOLDER, SUMMARY_FOLDER):
                    if os.path.isdir(folder):
                        shutil.rmtree(folder)
                st.cache_data.clear()
                st.success("Evidence cleared.")
                st.rerun()
            except OSError as error:
                st.error(f"Could not clear evidence: {error}")

# ============================================================
# EMPTY STATE
# ============================================================

if not has_data:
    st.info(
        "No analysis results yet. Upload a CCTV video, set the "
        "restricted area and select **Start forensic analysis**."
    )
    st.stop()

if events.empty:
    st.warning("No events match the current filters. Adjust the filters in the sidebar.")
    st.stop()

# ============================================================
# KPI ROW
# ============================================================

total_events = len(events)
unique_persons = (
    int(metadata.get("unique_tracked_ids", 0)) if metadata
    else events["Object ID"].nunique()
)

bins = (events["Time (s)"] // 10 * 10).astype(int)
peak_bin = bins.value_counts().idxmax()
peak_count = int(bins.value_counts().max())

duration = (
    vinfo["duration"] if vinfo["duration"]
    else float(all_events["Time (s)"].max())
)
frames = (
    vinfo["frames"] if vinfo["frames"]
    else int(all_events["Frame"].max())
)
duration_note = "from video metadata" if vinfo["duration"] else "estimated from last event"
frames_note = f"{vinfo['fps']} fps" if vinfo["fps"] else "estimated from last event"

coverage = (
    round(min(n_snapshots, len(all_events)) / len(all_events) * 100)
    if len(all_events) else 0
)

processing_time = (
    f"{metadata.get('processing_seconds', 0):.1f}s"
    if metadata and "processing_seconds" in metadata else "—"
)


def kpi(label, value, note="", tone=""):
    return f"""
    <div class="kpi {tone}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-note">{note}</div>
    </div>
    """


k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.markdown(kpi("Restricted-area events", total_events,
                     "filtered view" if filtered else "all detections",
                     "red"),
                unsafe_allow_html=True)
with k2:
    st.markdown(kpi("Unique persons", unique_persons,
                     "distinct tracked IDs"),
                unsafe_allow_html=True)
with k3:
    st.markdown(kpi("Video duration", f"{duration:,.1f}s", duration_note),
                unsafe_allow_html=True)
with k4:
    st.markdown(kpi("Video frames", f"{frames:,}", frames_note),
                unsafe_allow_html=True)
with k5:
    st.markdown(kpi("Evidence coverage", f"{coverage}%",
                     f"{n_snapshots} snapshots · {n_clips} clips",
                     "green" if coverage == 100 else "amber"),
                unsafe_allow_html=True)
with k6:
    st.markdown(kpi("Processing time", processing_time,
                     "from metadata.json"),
                unsafe_allow_html=True)

st.write("")

# ============================================================
# TABS
# ============================================================

tab_overview, tab_log, tab_objects, tab_evidence, tab_clips, tab_files = st.tabs([
    "Overview",
    "Event log",
    "Person analysis",
    "Evidence gallery",
    "Event clips",
    "Reports & export",
])

# ============================================================
# OVERVIEW
# ============================================================

with tab_overview:
    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown('<div class="panel-title">Event activity over time</div>',
                    unsafe_allow_html=True)

        bin_size = st.select_slider(
            "Bin size (seconds)",
            options=[1, 2, 5, 10, 15, 30, 60],
            value=5,
        )

        binned = (
            events.assign(
                window=(events["Time (s)"] // bin_size * bin_size).astype(int)
            )
            .groupby("window")
            .size()
            .reset_index(name="Events")
            .set_index("window")
        )
        st.bar_chart(binned, height=300, color=BLUE)

    with c2:
        st.markdown('<div class="panel-title">Key findings</div>',
                    unsafe_allow_html=True)

        top_object = events["Object ID"].value_counts().idxmax()
        top_object_count = int(events["Object ID"].value_counts().max())
        first_timestamp = events["Time (s)"].min()
        last_timestamp = events["Time (s)"].max()

        st.markdown(
            f"""
            <div class="insight"><b>{total_events}</b> restricted-area events involving
                <b>{unique_persons}</b> tracked person(s).</div>
            <div class="insight">First event at <b>{fmt_time(first_timestamp)}</b>,
                last at <b>{fmt_time(last_timestamp)}</b>.</div>
            <div class="insight">Peak activity: <b>{peak_count}</b> event(s) between
                <b>{peak_bin}s</b> and <b>{peak_bin + 10}s</b>.</div>
            <div class="insight">Most active person: <b>ID {top_object}</b>
                with <b>{top_object_count}</b> event(s).</div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    c3, c4 = st.columns([1, 2])

    with c3:
        st.markdown('<div class="panel-title">Detection rule</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="rule-box">A person enters the predefined restricted area.</div>',
            unsafe_allow_html=True,
        )
        st.write("")
        st.markdown(
            "- **Detector:** YOLO11n\n"
            "- **Tracker:** ByteTrack\n"
            "- **Log fields:** timestamp, person ID, frame"
        )

    with c4:
        st.markdown('<div class="panel-title">Events per person</div>',
                    unsafe_allow_html=True)
        per_object = (
            events["Object ID"].value_counts()
            .reset_index()
            .rename(columns={"index": "Object ID", "Object ID": "Events"})
        )
        per_object.columns = ["Object ID", "Events"]
        per_object = per_object.head(15).set_index("Object ID")
        st.bar_chart(per_object, height=max(140, 28 * len(per_object)),
                     color=NAVY_2)

# ============================================================
# EVENT LOG
# ============================================================

with tab_log:
    st.markdown('<div class="panel-title">Forensic event log</div>',
                unsafe_allow_html=True)

    search = st.text_input(
        "Search log", placeholder="Search by event type or person ID"
    )
    view = events.copy()

    if search:
        term = search.lower()
        view = view[
            view["Event Type"].str.lower().str.contains(term, na=False)
            | view["Object ID"].astype(str).str.lower().str.contains(term, na=False)
        ]

    view["Timecode"] = view["Time (s)"].apply(fmt_time)
    view["Clip"] = view["No"].apply(
        lambda number: "Yes"
        if os.path.isfile(clip_path_for(int(number)))
        else "Missing"
    )
    view["Snapshot file"] = view["Snapshot"].apply(
        lambda name: "Yes"
        if os.path.isfile(snapshot_path_for(name))
        else "Missing"
    )

    display = view[[
        "No", "Timecode", "Time (s)", "Event Type", "Object ID",
        "Frame", "Snapshot file", "Clip",
    ]].rename(columns={
        "No": "Event",
        "Timecode": "Timecode",
        "Time (s)": "Time (s)",
        "Object ID": "Person ID",
        "Frame": "Frame",
    })

    show_df(display)
    st.caption(f"{len(display)} of {len(all_events)} events shown")

    st.download_button(
        "Download filtered log (CSV)",
        data=display.to_csv(index=False).encode("utf-8"),
        file_name="forensic_events_filtered.csv",
        mime="text/csv",
    )

# ============================================================
# PERSON ANALYSIS
# ============================================================

with tab_objects:
    st.markdown('<div class="panel-title">Tracked person summary</div>',
                unsafe_allow_html=True)

    object_table = build_object_table(events)
    if not object_table.empty:
        object_table["Risk"] = object_table["Events"].apply(risk_level)
        object_table = object_table.rename(columns={"Object ID": "Person ID"})
        show_df(object_table)

        st.caption(
            "Risk is a simple heuristic based on event count per person "
            "(High ≥ 10, Medium ≥ 4). It is a triage aid, not a finding."
        )

        st.write("")
        st.markdown('<div class="panel-title">Person timeline</div>',
                    unsafe_allow_html=True)

        timeline_df = (
            events[["Object ID", "Time (s)"]]
            .rename(columns={"Object ID": "Person", "Time (s)": "Time"})
            .astype({"Person": str})
            .sort_values("Time")
        )
        st.scatter_chart(
            timeline_df,
            x="Time",
            y="Person",
            height=max(180, 34 * events["Object ID"].nunique()),
            color=RED,
        )
    else:
        st.info("No person information is available.")

# ============================================================
# EVIDENCE GALLERY
# ============================================================

with tab_evidence:
    st.markdown('<div class="panel-title">Snapshot evidence</div>',
                unsafe_allow_html=True)
    st.caption("Frames captured at the moment each event was triggered.")

    per_page = 6
    pages = max(1, (len(events) + per_page - 1) // per_page)
    page_col, info_col = st.columns([1, 4])

    with page_col:
        page = st.number_input("Page", min_value=1, max_value=pages,
                               value=1, step=1)

    with info_col:
        st.write("")
        st.caption(f"Page {page} of {pages} · {len(events)} snapshots")

    chunk = events.iloc[(int(page) - 1) * per_page:int(page) * per_page]
    columns = st.columns(3)

    for index, (_, row) in enumerate(chunk.iterrows()):
        with columns[index % 3]:
            snapshot = snapshot_path_for(row["Snapshot"])
            st.markdown(
                f"**Event {int(row['No']):02d}** &nbsp; "
                f'<span class="pill pill-blue">Person {row["Object ID"]}</span>'
                f' &nbsp;'
                f'<span class="pill pill-grey">{fmt_time(row["Time (s)"])}</span>',
                unsafe_allow_html=True,
            )

            if os.path.isfile(snapshot):
                with open(snapshot, "rb") as file:
                    image_bytes = file.read()
                frame_text = "" if pd.isna(row["Frame"]) else int(row["Frame"])
                show_image(image_bytes, caption=f"Frame {frame_text}")
            else:
                st.error("Snapshot not found.")
            st.write("")

# ============================================================
# EVENT CLIPS
# ============================================================

with tab_clips:
    st.markdown('<div class="panel-title">Event video evidence</div>',
                unsafe_allow_html=True)
    st.caption("Short video segments surrounding each detected event.")

    labels = {
        int(row["No"]): (
            f"Event {int(row['No']):02d} · Person {row['Object ID']} · "
            f"{fmt_time(row['Time (s)'])}"
        )
        for _, row in events.iterrows()
    }

    selected_no = st.selectbox(
        "Select event",
        options=list(labels.keys()),
        format_func=lambda number: labels[number],
    )

    row = events[events["No"] == selected_no].iloc[0]
    clip = clip_path_for(int(selected_no))
    video_col, details_col = st.columns([2, 1])

    with video_col:
        if os.path.isfile(clip):
            st.video(clip)
            if clip.lower().endswith("_browser.mp4"):
                st.caption("Playing browser-compatible H.264 evidence video.")

            with open(clip, "rb") as file:
                st.download_button(
                    "Download selected event clip",
                    data=file.read(),
                    file_name=os.path.basename(clip),
                    mime="video/mp4",
                )
        else:
            st.warning("Event clip not found.")

    with details_col:
        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">Event details</div>
                <p><b>Event type:</b> {row['Event Type']}</p>
                <p><b>Person ID:</b> {row['Object ID']}</p>
                <p><b>Frame:</b>
                    {'' if pd.isna(row['Frame']) else int(row['Frame'])}</p>
                <p><b>Timestamp:</b> {row['Time (s)']} s
                    ({fmt_time(row['Time (s)'])})</p>
                <p><b>Snapshot:</b> {row['Snapshot']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ============================================================
# REPORTS & EXPORT
# ============================================================

with tab_files:
    report_col, export_col = st.columns([3, 2])

    with report_col:
        st.markdown('<div class="panel-title">Automated HTML summary</div>',
                    unsafe_allow_html=True)

        if os.path.isfile(SUMMARY_HTML):
            with open(SUMMARY_HTML, "rb") as file:
                st.download_button(
                    "Download HTML event summary",
                    data=file.read(),
                    file_name="cctv_forensic_summary.html",
                    mime="text/html",
                )
        else:
            st.info("The HTML summary has not been generated yet.")

        if os.path.isfile(SUMMARY_VIDEO):
            st.markdown("**Annotated summary video**")
            st.video(SUMMARY_VIDEO)
            if SUMMARY_VIDEO == SUMMARY_VIDEO_BROWSER:
                st.caption("Playing browser-compatible H.264 summary video.")

        st.write("")
        st.markdown('<div class="panel-title">Chain of custody</div>',
                    unsafe_allow_html=True)
        st.caption(
            "SHA-256 fingerprints help verify whether evidence files "
            "have changed since their hashes were calculated."
        )

        if os.path.isfile(EVENTS_FILE):
            st.markdown("**events.csv**")
            st.markdown(
                f'<div class="hash">{sha256_of(EVENTS_FILE)}</div>',
                unsafe_allow_html=True,
            )

        if metadata and metadata.get("video_sha256"):
            st.markdown("**source video**")
            st.markdown(
                f'<div class="hash">{metadata["video_sha256"]}</div>',
                unsafe_allow_html=True,
            )

    with export_col:
        st.markdown('<div class="panel-title">Export</div>',
                    unsafe_allow_html=True)

        if os.path.isfile(EVENTS_FILE):
            with open(EVENTS_FILE, "rb") as file:
                st.download_button(
                    "Download full event log (CSV)",
                    data=file.read(),
                    file_name="forensic_events.csv",
                    mime="text/csv",
                )
        else:
            st.warning("Event log file not found.")

        st.write("")
        report_html = make_html_report(events, vinfo, case_id, metadata)

        st.download_button(
            "Download investigation report (HTML)",
            data=report_html.encode("utf-8"),
            file_name=f"{case_id}_report.html",
            mime="text/html",
        )

        st.caption(
            "Open the report in a browser and use Print → Save as PDF "
            "if you need a PDF copy."
        )

        st.write("")
        if st.button("Prepare evidence package (ZIP)"):
            with st.spinner("Packaging evidence…"):
                st.session_state["evidence_zip"] = make_evidence_zip(events)

        if "evidence_zip" in st.session_state:
            st.download_button(
                "Download evidence package",
                data=st.session_state["evidence_zip"],
                file_name=f"{case_id}_evidence.zip",
                mime="application/zip",
            )

        st.write("")
        st.markdown('<div class="panel-title">Storage locations</div>',
                    unsafe_allow_html=True)
        st.code(
            f"Event log : {EVENTS_FILE}\n"
            f"Snapshots : {SNAPSHOT_FOLDER}\n"
            f"Clips     : {EVENTS_FOLDER}\n"
            f"Summaries : {SUMMARY_FOLDER}",
            language=None,
        )

# ============================================================
# FOOTER
# ============================================================

st.write("")
st.caption(
    "CCTV Video Forensic Investigation System · YOLO + ByteTrack · "
    f"Report generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"
)