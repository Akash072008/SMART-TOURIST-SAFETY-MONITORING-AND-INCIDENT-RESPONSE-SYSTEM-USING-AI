import streamlit as st
import requests
import pandas as pd

# --- Page Configuration ---
st.set_page_config(
    page_title="Tourist Safety Telemetry",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Clean Dark Telemetry CSS (Zero-Blink SVG Gauges) ---
st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
    header[data-testid="stHeader"] { background: transparent; }
    footer { visibility: hidden; }
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    .panel {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        margin-bottom: 14px;
    }
    .panel-label {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #9ca3af;
        margin-bottom: 8px;
        text-align: center;
    }

    .banner-safe {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid #10b981;
        color: #34d399;
        padding: 12px 18px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 15px;
        margin-bottom: 16px;
    }
    .banner-sos {
        background: rgba(239, 68, 68, 0.22);
        border: 2px solid #ef4444;
        color: #fca5a5;
        padding: 14px 18px;
        border-radius: 12px;
        font-weight: 800;
        font-size: 17px;
        text-align: center;
        margin-bottom: 16px;
    }
    .banner-warn {
        background: rgba(245, 158, 11, 0.14);
        border: 1px solid #f59e0b;
        color: #fbbf24;
        padding: 12px 18px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 16px;
    }

    div.stButton > button {
        width: 100%;
        height: 54px;
        border-radius: 12px;
        font-size: 16px;
        font-weight: 800;
        letter-spacing: 1px;
        border: 1px solid #ef4444;
        background: linear-gradient(180deg, #dc2626, #991b1b);
        color: white;
    }
    div.stButton > button:hover {
        background: linear-gradient(180deg, #ef4444, #b91c1c);
        border-color: #fca5a5;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if "manual_sos" not in st.session_state:
    st.session_state.manual_sos = False
if "last_valid_data" not in st.session_state:
    st.session_state.last_valid_data = {
        "sos": False, "finger": False, "bpm": 0,
        "raw": 0, "temp": 0.0, "gps_valid": False,
        "lat": 0.0, "lng": 0.0
    }

# --- Zero-Flicker SVG Speedometer Generator ---
def render_svg_speedometer(title, value, unit, min_v, max_v, color, subtitle):
    clamped = max(min_v, min(max_v, float(value)))
    pct = (clamped - min_v) / (max_v - min_v) if max_v > min_v else 0
    arc_len = 307.0
    dash_offset = arc_len * (1.0 - pct)
    display_val = f"{int(value)}" if unit == "BPM" else f"{value:.1f}"

    html = (
        '<div class="panel" style="text-align:center;">'
        f'<div class="panel-label">{title}</div>'
        '<svg width="220" height="145" viewBox="0 0 220 145" style="overflow:visible;">'
        '<path d="M 30 125 A 80 80 0 1 1 190 125" fill="none" stroke="#1f2937" stroke-width="16" stroke-linecap="round" />'
        f'<path d="M 30 125 A 80 80 0 1 1 190 125" fill="none" stroke="{color}" stroke-width="16" stroke-linecap="round" '
        f'stroke-dasharray="{arc_len}" stroke-dashoffset="{dash_offset:.1f}" style="transition: stroke-dashoffset 0.4s ease, stroke 0.4s ease;" />'
        f'<text x="110" y="102" text-anchor="middle" fill="#f8fafc" font-size="34" font-weight="800" font-family="Segoe UI, sans-serif">{display_val}</text>'
        f'<text x="110" y="124" text-anchor="middle" fill="#9ca3af" font-size="13" font-weight="700" font-family="Segoe UI, sans-serif">{unit}</text>'
        f'<text x="26" y="143" text-anchor="middle" fill="#6b7280" font-size="11">{min_v}</text>'
        f'<text x="194" y="143" text-anchor="middle" fill="#6b7280" font-size="11">{max_v}</text>'
        '</svg>'
        f'<div style="font-size:13px; color:#9ca3af; margin-top:4px;">{subtitle}</div>'
        '</div>'
    )
    return html

# --- Top Control Bar ---
c_title, c_ip, c_sos = st.columns([2.2, 1.3, 1.1], vertical_alignment="center")
with c_title:
    st.markdown("<h2 style='margin:0; color:#f8fafc;'>🛡️ Smart Tourist Safety Dashboard</h2>", unsafe_allow_html=True)
with c_ip:
    esp_ip = st.text_input("ESP32 IP Address", value="10.189.206.129", label_visibility="collapsed", placeholder="Enter ESP32 IP")
with c_sos:
    btn_label = "✅ CLEAR SOS ALERT" if st.session_state.manual_sos else "🚨 TRIGGER SOS"
    if st.button(btn_label):
        st.session_state.manual_sos = not st.session_state.manual_sos
        st.rerun()

# --- Live Telemetry Fragment ---
@st.fragment(run_every=1.0)
def live_telemetry_panel(ip_addr):
    connected = False
    err_msg = ""
    try:
        r = requests.get(f"http://{ip_addr.strip()}/", timeout=0.8)
        if r.status_code == 200:
            st.session_state.last_valid_data = r.json()
            connected = True
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception:
        err_msg = "Timeout / Unreachable"

    data = st.session_state.last_valid_data
    sos_active = data.get("sos", False) or st.session_state.manual_sos
    bpm = int(data.get("bpm", 0))
    temp = float(data.get("temp", 0.0))
    raw_adc = int(data.get("raw", 0))
    finger_on = data.get("finger", bpm > 0)
    gps_valid = data.get("gps_valid", False)
    lat = float(data.get("lat", 0.0))
    lng = float(data.get("lng", 0.0))

    # 1. Status Banner
    if sos_active:
        src = "HARDWARE SOS BUTTON" if data.get("sos", False) else "DASHBOARD SOS OVERRIDE"
        st.markdown(f'<div class="banner-sos">🚨 EMERGENCY SOS ACTIVE ({src}) — IMMEDIATE ASSISTANCE REQUIRED! 🚨</div>', unsafe_allow_html=True)
    elif not connected:
        st.markdown(f'<div class="banner-warn">📡 Connecting to wearable at <b>{ip_addr}</b> ({err_msg}) — Confirm IP in Arduino Serial Monitor</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="banner-safe">🟢 WEARABLE CONNECTED ({ip_addr}) — Live Telemetry Active</div>', unsafe_allow_html=True)

    # 2. Main 2-Column Layout
    left_col, right_col = st.columns([1.25, 1], gap="large")

    with left_col:
        g1, g2 = st.columns(2)
        with g1:
            bpm_color = "#ef4444" if bpm > 110 else ("#38bdf8" if bpm > 0 else "#4b5563")
            bpm_sub = "🟢 Pulse Locked" if bpm > 0 else ("🟡 Reading Pulse..." if finger_on else "⚪ Place Finger on Sensor")
            st.markdown(render_svg_speedometer("HEART RATE", bpm, "BPM", 0, 180, bpm_color, bpm_sub), unsafe_allow_html=True)

        with g2:
            temp_color = "#ef4444" if temp > 37.8 else ("#10b981" if temp > 20 else "#4b5563")
            temp_sub = "⚠️ Elevated Temp" if temp > 37.8 else ("🟢 Normal Range" if temp > 20 else "⚪ Reading Probe...")
            st.markdown(render_svg_speedometer("BODY TEMPERATURE", temp, "°C", 25, 42, temp_color, temp_sub), unsafe_allow_html=True)

        # Hardware Diagnostics Strip
        d1, d2 = st.columns(2)
        with d1:
            diag_html = (
                '<div class="panel" style="padding:14px 18px;">'
                '<div class="panel-label" style="text-align:left; margin-bottom:2px;">Optical Sensor Signal</div>'
                f'<div style="font-size:18px; font-weight:700; color:#e2e8f0;">ADC: {raw_adc}</div>'
                '<div style="font-size:12px; color:#6b7280;">GPIO 34 Analog Input</div>'
                '</div>'
            )
            st.markdown(diag_html, unsafe_allow_html=True)

        with d2:
            sos_txt = "🔴 TRIGGERED" if sos_active else "🟢 Normal (Safe)"
            sos_html = (
                '<div class="panel" style="padding:14px 18px;">'
                '<div class="panel-label" style="text-align:left; margin-bottom:2px;">SOS Safety Switch</div>'
                f'<div style="font-size:18px; font-weight:700; color:#e2e8f0;">{sos_txt}</div>'
                '<div style="font-size:12px; color:#6b7280;">GPIO 13 &amp; Web Control</div>'
                '</div>'
            )
            st.markdown(sos_html, unsafe_allow_html=True)

    with right_col:
        gps_status = "🟢 3D Satellite Lock" if gps_valid else "🟡 Searching Satellites"
        coord_display = f"{lat:.6f}, {lng:.6f}" if gps_valid else "Place NEO-6M near window / sky"
        gps_header = (
            '<div class="panel" style="padding:14px 18px; margin-bottom:10px;">'
            '<div style="display:flex; justify-content:space-between; align-items:center;">'
            '<span class="panel-label" style="margin:0;">📍 Live GPS Tracking</span>'
            f'<span style="font-size:12px; font-weight:700; color:#38bdf8;">{gps_status}</span>'
            '</div>'
            f'<div style="font-size:13px; color:#9ca3af; margin-top:4px; font-family:monospace;">{coord_display}</div>'
            '</div>'
        )
        st.markdown(gps_header, unsafe_allow_html=True)

        if gps_valid and lat != 0.0:
            df_map = pd.DataFrame({"lat": [lat], "lon": [lng]})
            st.map(df_map, zoom=15, height=275)
        else:
            map_placeholder = (
                '<div class="panel" style="height:275px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">'
                '<div style="font-size:38px; margin-bottom:8px;">🛰️</div>'
                '<div style="font-size:15px; font-weight:700; color:#e2e8f0;">Acquiring GPS Satellite Fix</div>'
                '<div style="font-size:12px; color:#6b7280; max-width:250px; margin-top:6px;">'
                'NEO-6M needs clear sky visibility. Once locked, the interactive map appears here automatically.'
                '</div>'
                '</div>'
            )
            st.markdown(map_placeholder, unsafe_allow_html=True)

live_telemetry_panel(esp_ip)