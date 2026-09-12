"""Haute Joaillerie Atelier Bento Design System for Jewelry Retoucher CRM.

Implements luxury obsidian surfaces, 18K champagne gold accents, gemstone status
highlights, and bespoke horlogerie world clocks for international client outreach.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

LUXURY_BENTO_CSS = """
/* ==========================================================================
   HAUTE JOAILLERIE ATELIER BENTO DESIGN SYSTEM
   ========================================================================== */

/* 1. TYPOGRAPHY IMPORT */
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

:root {
    --bg-canvas: #07090E;
    --bg-bento: #0E121B;
    --bg-bento-subtle: #131722;
    --bg-surface-elevated: #161C2A;
    --border-gold-subtle: rgba(212, 175, 55, 0.18);
    --border-gold-glow: rgba(212, 175, 55, 0.45);
    --border-subtle: rgba(255, 255, 255, 0.08);
    --accent-gold: #D4AF37;
    --accent-gold-light: #F3D079;
    --accent-gold-dark: #AA7C11;
    --gem-emerald: #10B981;
    --gem-ruby: #F43F5E;
    --gem-sapphire: #38BDF8;
    --gem-amber: #F59E0B;
    --gem-amethyst: #A855F7;
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
}

/* 2. GLOBAL CANVAS & AMBIENT GLOW */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background-color: var(--bg-canvas) !important;
    color: var(--text-primary) !important;
}

.stApp {
    background: 
        radial-gradient(circle at 20% 0%, rgba(212, 175, 55, 0.04) 0%, transparent 45%),
        radial-gradient(circle at 80% 10%, rgba(56, 189, 248, 0.025) 0%, transparent 40%),
        var(--bg-canvas) !important;
}

/* 3. LUXURY TYPOGRAPHY HEADINGS */
h1, h2, h3 {
    font-family: 'Cinzel', Georgia, serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.035em !important;
    color: var(--text-primary) !important;
}

h4, h5, h6 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.015em !important;
    color: #E2E8F0 !important;
}

/* 4. STREAMLIT METRICS (BENTO STATS CARDS) */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(20, 26, 38, 0.85) 0%, rgba(14, 18, 27, 0.95) 100%) !important;
    border: 1px solid var(--border-gold-subtle) !important;
    border-radius: 14px !important;
    padding: 18px 22px !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(243, 208, 121, 0.1) !important;
    backdrop-filter: blur(12px) !important;
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease !important;
}

[data-testid="stMetric"]:hover {
    border-color: var(--border-gold-glow) !important;
    box-shadow: 0 12px 35px rgba(212, 175, 55, 0.12), inset 0 1px 0 rgba(243, 208, 121, 0.2) !important;
    transform: translateY(-2px) !important;
}

[data-testid="stMetricLabel"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    text-transform: uppercase !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.085em !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    margin-bottom: 4px !important;
}

[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
    letter-spacing: -0.02em !important;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6) !important;
}

[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
}

/* 5. BENTO CONTAINER WRAPPERS (border=True) */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: linear-gradient(180deg, #111520 0%, #0C0F17 100%) !important;
    border: 1px solid var(--border-gold-subtle) !important;
    border-radius: 12px !important;
    padding: 16px !important;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.35) !important;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
    border-color: rgba(212, 175, 55, 0.4) !important;
    box-shadow: 0 10px 30px rgba(212, 175, 55, 0.09) !important;
}

/* 6. STREAMLIT TABS (LUXURY GOLD PILLS) */
div[data-testid="stTabs"] {
    border-bottom: 1px solid rgba(212, 175, 55, 0.2) !important;
    margin-bottom: 1.25rem !important;
}

div[data-testid="stTabs"] button[role="tab"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em !important;
    font-size: 0.84rem !important;
    color: var(--text-secondary) !important;
    padding: 10px 18px !important;
    border-radius: 8px 8px 0 0 !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stTabs"] button[role="tab"]:hover {
    color: var(--accent-gold-light) !important;
    background: rgba(212, 175, 55, 0.05) !important;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: var(--accent-gold-light) !important;
    border-bottom: 2px solid var(--accent-gold) !important;
    background: linear-gradient(180deg, rgba(212, 175, 55, 0.09) 0%, transparent 100%) !important;
    text-shadow: 0 0 12px rgba(212, 175, 55, 0.35) !important;
}

/* 7. SIDEBAR ATELIER CONSOLE */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A0D15 0%, #07090E 100%) !important;
    border-right: 1px solid rgba(212, 175, 55, 0.15) !important;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4) !important;
}

[data-testid="stSidebar"] h3 {
    font-size: 1.05rem !important;
    margin-top: 0.5rem !important;
}

/* 8. BUTTONS & ACTIONS */
.stButton > button {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    border-radius: 10px !important;
    border: 1px solid var(--border-gold-subtle) !important;
    background: linear-gradient(180deg, #161C28 0%, #0E121B 100%) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.stButton > button:hover {
    border-color: var(--accent-gold) !important;
    box-shadow: 0 4px 16px rgba(212, 175, 55, 0.22) !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
}

.stButton > button:active {
    transform: translateY(0px) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #F3D079 0%, #D4AF37 50%, #B8860B 100%) !important;
    color: #07090E !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 4px 18px rgba(212, 175, 55, 0.32) !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 22px rgba(212, 175, 55, 0.45) !important;
    color: #000000 !important;
}

/* 9. INPUTS, TEXTAREAS & SELECTS */
input[type="text"], input[type="number"], textarea, div[data-baseweb="select"] > div {
    background-color: #0B0E16 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 9px !important;
    color: var(--text-primary) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

input:focus, textarea:focus, div[data-baseweb="select"] > div:focus-within {
    border-color: var(--accent-gold) !important;
    box-shadow: 0 0 0 1px var(--accent-gold), 0 0 14px rgba(212, 175, 55, 0.2) !important;
}

/* 10. EXPANDERS & ACCORDIONS */
[data-testid="stExpander"] {
    background-color: #0D111A !important;
    border: 1px solid var(--border-gold-subtle) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
}

/* 11. ALERTS & CALLOUTS */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    background-color: #0D111A !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* 12. PROGRESS BAR */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #D4AF37 0%, #10B981 100%) !important;
    border-radius: 6px !important;
}

/* ==========================================================================
   CUSTOM ATELIER BENTO COMPONENTS
   ========================================================================== */

/* ATELIER HEADER BENTO */
.atelier-header-bento {
    position: relative;
    overflow: hidden;
    margin-bottom: 1.5rem;
    padding: 24px 28px;
    background: linear-gradient(135deg, rgba(22, 28, 42, 0.95) 0%, rgba(13, 17, 26, 0.98) 100%);
    border: 1px solid var(--border-gold-subtle);
    border-radius: 16px;
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(243, 208, 121, 0.15);
}

.atelier-header-glow {
    position: absolute;
    top: 0;
    left: 15%;
    width: 70%;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, var(--accent-gold) 50%, transparent 100%);
    opacity: 0.8;
}

.atelier-header-content {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
}

.atelier-title-group {
    flex: 1 1 300px;
}

.atelier-eyebrow {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

.atelier-eyebrow-text {
    font-family: 'Cinzel', serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    color: var(--accent-gold-light);
    text-transform: uppercase;
}

.atelier-main-title {
    font-family: 'Cinzel', Georgia, serif;
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    margin: 0;
    color: #FFFFFF;
    line-height: 1.2;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
}

.atelier-subtitle {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.86rem;
    color: var(--text-secondary);
    margin-top: 6px;
    letter-spacing: 0.01em;
}

.atelier-meta-group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
}

.atelier-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}

.atelier-badge-gold {
    background: rgba(212, 175, 55, 0.1);
    border: 1px solid rgba(212, 175, 55, 0.35);
    color: var(--accent-gold-light);
}

.atelier-badge-emerald {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34D399;
}

.atelier-badge-date {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #E2E8F0;
    font-family: 'JetBrains Mono', monospace;
}

.badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
}

.dot-gold {
    background-color: var(--accent-gold);
    box-shadow: 0 0 6px var(--accent-gold);
}

.dot-emerald {
    background-color: var(--gem-emerald);
    box-shadow: 0 0 6px var(--gem-emerald);
}

/* HORLOGERIE SIDEBAR WORLD CLOCKS */
.horlogerie-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 1.25rem;
}

.horlogerie-card {
    background: linear-gradient(145deg, #101521 0%, #0B0E17 100%);
    border: 1px solid rgba(212, 175, 55, 0.16);
    border-radius: 10px;
    padding: 10px 14px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
    transition: all 0.2s ease;
}

.horlogerie-card:hover {
    border-color: rgba(212, 175, 55, 0.38);
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
}

.horlogerie-card.card-active {
    border-left: 3px solid var(--gem-emerald);
}

.horlogerie-card.card-dormant {
    border-left: 3px solid #334155;
}

.horlogerie-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.horlogerie-city {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    color: #E2E8F0;
}

.horlogerie-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.badge-open {
    background: rgba(16, 185, 129, 0.18);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.35);
}

.badge-closed {
    background: rgba(100, 116, 139, 0.15);
    color: #94A3B8;
    border: 1px solid rgba(100, 116, 139, 0.25);
}

.horlogerie-time-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
}

.horlogerie-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.35rem;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: -0.01em;
    line-height: 1.1;
}

.horlogerie-day {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.7rem;
    color: var(--text-muted);
}

.horlogerie-footer {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 4px;
}

.horlogerie-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
}

.dot-active {
    background-color: var(--gem-emerald);
    box-shadow: 0 0 6px var(--gem-emerald);
}

.dot-dormant {
    background-color: #64748B;
}

.horlogerie-desc {
    font-size: 0.7rem;
    color: var(--text-secondary);
}

/* KANBAN BENTO POLISH */
.bento-kanban-empty {
    border: 1px dashed rgba(212, 175, 55, 0.2);
    border-radius: 8px;
    padding: 16px 10px;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.78rem;
    background: rgba(14, 18, 27, 0.4);
    letter-spacing: 0.02em;
}
"""


def inject_luxury_theme() -> None:
    """Inject Haute Joaillerie luxury Bento CSS into current Streamlit session."""
    st.markdown(f"<style>{LUXURY_BENTO_CSS}</style>", unsafe_allow_html=True)


def render_atelier_header(date_str: str | None = None) -> None:
    """Render Haute Joaillerie Atelier Bento Header."""
    if not date_str:
        date_str = datetime.now().strftime("%d.%m.%Y")

    header_html = f"""
    <div class="atelier-header-bento">
        <div class="atelier-header-glow"></div>
        <div class="atelier-header-content">
            <div class="atelier-title-group">
                <div class="atelier-eyebrow">
                    <span>💎</span>
                    <span class="atelier-eyebrow-text">HAUTE JOAILLERIE ATELIER</span>
                </div>
                <h1 class="atelier-main-title">RETOUCH OPERATIONAL CRM</h1>
                <div class="atelier-subtitle">Bespoke Jewelry Post-Production, Client Relations & Cashflow Protocol</div>
            </div>
            <div class="atelier-meta-group">
                <div class="atelier-badge atelier-badge-gold">
                    <span class="badge-dot dot-gold"></span>
                    <span>18K Champagne Gold Tier</span>
                </div>
                <div class="atelier-badge atelier-badge-emerald">
                    <span class="badge-dot dot-emerald"></span>
                    <span>Offline-First Atelier</span>
                </div>
                <div class="atelier-badge atelier-badge-date">
                    <span>📅</span>
                    <span>{date_str}</span>
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def render_horlogerie_clocks(tz_targets: list[tuple[str, str]] | None = None) -> None:
    """Render luxury Horlogerie Bento World Clocks in the sidebar."""
    if tz_targets is None:
        tz_targets = [
            ("🇺🇸 New York", "America/New_York"),
            ("🇬🇧 London", "Europe/London"),
            ("🇫🇷 Paris", "Europe/Paris"),
            ("🇦🇪 Dubai", "Asia/Dubai"),
            ("🇯🇵 Tokyo", "Asia/Tokyo"),
        ]

    clock_cards_html = []

    for item in tz_targets:
        tz_label = item[0]
        tz_key = item[1]

        try:
            local_dt = datetime.now(ZoneInfo(tz_key))
            time_str = local_dt.strftime("%H:%M")
            day_str = local_dt.strftime("%a, %d %b")

            # Business hours: Mon-Fri (0-4), 09:00 - 18:00 local time
            is_weekday = local_dt.weekday() < 5
            is_work_hour = 9 <= local_dt.hour < 18
            is_active = is_weekday and is_work_hour

            if is_active:
                card_class = "horlogerie-card card-active"
                badge_class = "horlogerie-badge badge-open"
                badge_text = "OPEN"
                dot_class = "horlogerie-dot dot-active"
                desc_text = "Рабочее время (Active)"
            else:
                card_class = "horlogerie-card card-dormant"
                badge_class = "horlogerie-badge badge-closed"
                badge_text = "OFF" if is_weekday else "WKND"
                dot_class = "horlogerie-dot dot-dormant"
                desc_text = "Выходной" if not is_weekday else "Нерабочее время"

            card_markup = f"""
            <div class="{card_class}">
                <div class="horlogerie-header">
                    <span class="horlogerie-city">{tz_label}</span>
                    <span class="{badge_class}">{badge_text}</span>
                </div>
                <div class="horlogerie-time-row">
                    <span class="horlogerie-time">{time_str}</span>
                    <span class="horlogerie-day">{day_str}</span>
                </div>
                <div class="horlogerie-footer">
                    <span class="{dot_class}"></span>
                    <span class="horlogerie-desc">{desc_text}</span>
                </div>
            </div>
            """
            clock_cards_html.append(card_markup)
        except Exception:
            continue

    full_markup = f"""
    <div class="horlogerie-container">
        {"".join(clock_cards_html)}
    </div>
    """
    st.markdown(full_markup, unsafe_allow_html=True)
