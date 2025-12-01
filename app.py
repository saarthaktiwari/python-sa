import streamlit as st
import pandas as pd
import datetime as dt
from dateutil import parser
import random
import io
from PIL import Image
import turtle

# ----------------------------
# App config & styling
# ----------------------------
st.set_page_config(page_title="MedTimer", page_icon="💊", layout="wide")

APP_PRIMARY = "#1b5e20"   # deep green
APP_ACCENT = "#4caf50"    # green accent
APP_WARN = "#f9a825"      # amber
APP_ERROR = "#c62828"     # red
APP_BG = "#f5f7f9"        # soft background

st.markdown(f"""
    <style>
    .big-title {{ font-size: 36px; font-weight: 700; color: {APP_PRIMARY}; }}
    .subtle {{ color: #546e7a; }}
    .pill {{
        padding: 8px 12px; border-radius: 20px; display: inline-block; margin-right: 8px;
        font-weight: 600; color: white;
    }}
    </style>
""", unsafe_allow_html=True)

# Auto-refresh every 20 seconds to keep statuses current
st_autorefresh_count = st.experimental_data_editor if False else None
st_autorefresh_key = st.experimental_rerun if False else None
st_autorefresh = st.experimental_rerun if False else None
st_autorefresh_id = st.experimental_set_query_params if False else None
st.experimental_set_query_params()  # harmless
count = st.experimental_get_query_params()
st_autorefresh_trigger = st.autorefresh(interval=20_000, key="refresh_key")

# ----------------------------
# Session state init
# ----------------------------
def init_state():
    if "meds" not in st.session_state:
        st.session_state.meds = []  # [{id, name, time_str, remind_min, status, taken_at}]
    if "history" not in st.session_state:
        st.session_state.history = {}  # {date_str: {"scheduled": int, "taken": int}}
    if "tips_index" not in st.session_state:
        st.session_state.tips_index = 0
    if "beep_flag" not in st.session_state:
        st.session_state.beep_flag = False
    if "id_counter" not in st.session_state:
        st.session_state.id_counter = 1
init_state()

# ----------------------------
# Utilities
# ----------------------------
def parse_hhmm(time_str: str) -> dt.datetime:
    today = dt.date.today()
    try:
        t = parser.parse(time_str).time()
    except Exception:
        t = dt.datetime.strptime(time_str, "%H:%M").time()
    return dt.datetime.combine(today, t)

def now_local() -> dt.datetime:
    return dt.datetime.now()

def status_color(status: str) -> str:
    return {"taken": APP_ACCENT, "upcoming": APP_WARN, "missed": APP_ERROR}.get(status, "#607d8b")

def compute_status(med) -> str:
    """
    upcoming: now < time and not taken
    missed: now >= time and not taken
    taken: explicitly marked
    """
    if med.get("status") == "taken":
        return "taken"
    target = parse_hhmm(med["time_str"])
    return "upcoming" if now_local() < target else "missed"

def update_all_statuses():
    for med in st.session_state.meds:
        med["status"] = compute_status(med)

def adherence_today():
    scheduled = len(st.session_state.meds)
    taken = sum(1 for m in st.session_state.meds if m.get("status") == "taken")
    pct = int((taken / scheduled) * 100) if scheduled else 0
    return scheduled, taken, pct

def record_daily_history():
    date_key = dt.date.today().isoformat()
    scheduled, taken, _ = adherence_today()
    st.session_state.history[date_key] = {"scheduled": scheduled, "taken": taken}

def weekly_adherence():
    # Last 7 days adherence
    today = dt.date.today()
    rows = []
    for i in range(7):
        d = (today - dt.timedelta(days=i)).isoformat()
        rec = st.session_state.history.get(d, {"scheduled": 0, "taken": 0})
        pct = int((rec["taken"]/rec["scheduled"]*100)) if rec["scheduled"] else 0
        rows.append({"date": d, "scheduled": rec["scheduled"], "taken": rec["taken"], "adherence_%": pct})
    rows.reverse()
    df = pd.DataFrame(rows)
    weekly_pct = int(df["adherence_%"].mean()) if not df.empty else 0
    return df, weekly_pct

def current_streak():
    # consecutive days with 100% adherence
    today = dt.date.today()
    streak = 0
    for i in range(30):  # up to last 30 days
        d = (today - dt.timedelta(days=i)).isoformat()
        rec = st.session_state.history.get(d)
        if not rec or rec["scheduled"] == 0 or rec["taken"] < rec["scheduled"]:
            break
        streak += 1
    return streak

# ----------------------------
# Motivational tips
# ----------------------------
TIPS_GOOD = [
    "Consistency builds confidence. Keep it going!",
    "Your routine is your superpower.",
    "Great job—your future self is grateful."
]
TIPS_NEUTRAL = [
    "You’re on track. A small step right now helps.",
    "Take a breath and check what’s next.",
    "Even one dose taken is progress."
]
TIPS_MISSED = [
    "It happens. Reset, and take the next dose when safe.",
    "No worries—refocus on the next scheduled dose.",
    "Forward is forward. You’ve got this."
]

def tip_for_status(pct: int) -> str:
    if pct >= 80:
        pool = TIPS_GOOD
    elif pct >= 30:
        pool = TIPS_NEUTRAL
    else:
        pool = TIPS_MISSED
    idx = st.session_state.tips_index % len(pool)
    st.session_state.tips_index += 1
    return pool[idx]

# ----------------------------
# Turtle graphics (smiley/trophy)
# ----------------------------
def draw_turtle_trophy(pct: int) -> Image.Image:
    # Create a turtle drawing and convert to PIL Image via PostScript
    # Trophy for >=90, Smiley for >=80, leaf for >=70
    canvas_size = (400, 400)
    screen = turtle.Screen()
    screen.setup(width=canvas_size[0], height=canvas_size[1])
    screen.bgcolor("white")
    t = turtle.Turtle(visible=False)
    t.speed(0)
    t.pensize(4)
    t.color("green")

    if pct >= 90:
        # Trophy
        t.penup(); t.goto(-50, -50); t.pendown()
        t.color("gold"); t.begin_fill()
        for _ in range(2):
            t.forward(100); t.left(90); t.forward(60); t.left(90)
        t.end_fill()
        # handles
        t.color("darkgoldenrod")
        t.penup(); t.goto(-50, 10); t.pendown()
        t.circle(30, 180)
        t.penup(); t.goto(50, 10); t.pendown()
        t.circle(-30, 180)
    elif pct >= 80:
        # Smiley
        t.penup(); t.goto(0, -80); t.pendown()
        t.circle(100)
        # eyes
        t.penup(); t.goto(-40, 40); t.pendown(); t.dot(20)
        t.penup(); t.goto(40, 40); t.pendown(); t.dot(20)
        # smile
        t.penup(); t.goto(-50, -10); t.pendown()
        t.setheading(-60); t.circle(60, 120)
    elif pct >= 70:
        # Leaf
        t.color("forestgreen")
        t.penup(); t.goto(0, -60); t.pendown()
        t.setheading(60)
        for _ in range(2):
            t.circle(80, 120)
            t.right(180)
    else:
        # Subtle dot
        t.penup(); t.goto(0,0); t.pendown()
        t.dot(10, "lightgray")

    # Export PostScript via Tkinter canvas
    cv = screen.getcanvas()
    ps = io.BytesIO(cv.postscript(colormode='color').encode('utf-8'))
    img = Image.open(ps)
    turtle.bye()
    return img

# ----------------------------
# Audio beep (base64 wav bytes)
# ----------------------------
# A tiny 440Hz beep wav (1 second). Pre-encoded bytes to keep it simple.
# If needed, replace with your own asset.
BEEP_WAV = None
def load_beep():
    # Minimal silent placeholder if audio fails.
    global BEEP_WAV
    if BEEP_WAV is None:
        # Generate a 0.2s sine wave via numpy if available; else skip.
        try:
            import numpy as np
            fr = 44100
            t = np.linspace(0, 0.2, int(fr*0.2), False)
            tone = 0.5*np.sin(2*np.pi*440*t)
            audio = (tone * (2**15 - 1)).astype(np.int16)
            import wave
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(fr)
                w.writeframes(audio.tobytes())
            BEEP_WAV = buf.getvalue()
        except Exception:
            BEEP_WAV = b""
load_beep()

def maybe_beep():
    if st.session_state.beep_flag and BEEP_WAV:
        st.audio(BEEP_WAV, format='audio/wav')
        st.session_state.beep_flag = False

# ----------------------------
# Reminder logic
# ----------------------------
def reminder_window_open(med) -> bool:
    """
    True if now >= (scheduled - remind_min) and not taken.
    """
    if med.get("status") == "taken":
        return False
    remind_min = int(med.get("remind_min", 0) or 0)
    sched = parse_hhmm(med["time_str"])
    window_start = sched - dt.timedelta(minutes=remind_min)
    return now_local() >= window_start and now_local() < sched

def check_and_trigger_beeps():
    for med in st.session_state.meds:
        if reminder_window_open(med):
            st.session_state.beep_flag = True
            break

# ----------------------------
# CRUD operations
# ----------------------------
def add_medicine(name: str, time_str: str, remind_min: int):
    med = {
        "id": st.session_state.id_counter,
        "name": name.strip(),
        "time_str": time_str.strip(),
        "remind_min": int(remind_min),
        "status": "upcoming",
        "taken_at": None,
    }
    st.session_state.id_counter += 1
    st.session_state.meds.append(med)
    update_all_statuses()

def edit_medicine(med_id: int, name: str, time_str: str, remind_min: int):
    for m in st.session_state.meds:
        if m["id"] == med_id:
            m["name"] = name.strip()
            m["time_str"] = time_str.strip()
            m["remind_min"] = int(remind_min)
            break
    update_all_statuses()

def delete_medicine(med_id: int):
    st.session_state.meds = [m for m in st.session_state.meds if m["id"] != med_id]
    update_all_statuses()

def mark_taken(med_id: int):
    for m in st.session_state.meds:
        if m["id"] == med_id:
            m["status"] = "taken"
            m["taken_at"] = now_local().isoformat(timespec="minutes")
            break
    update_all_statuses()
    record_daily_history()

# ----------------------------
# Header
# ----------------------------
st.markdown("<div class='big-title'>💊 MedTimer — Daily Medicine Companion</div>", unsafe_allow_html=True)
st.write(f"<span class='subtle'>Today: {dt.date.today().strftime('%a, %d %b %Y')}</span>", unsafe_allow_html=True)

# ----------------------------
# Layout: left (inputs & list), right (metrics, turtle, tips)
# ----------------------------
left, right = st.columns([0.6, 0.4])

with left:
    st.subheader("Add or edit medicines")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Medicine name")
        time_str = st.text_input("Scheduled time (HH:MM)", placeholder="08:00")
        remind_min = st.number_input("Remind minutes before", min_value=0, max_value=120, value=15, step=5)
        submitted = st.form_submit_button("Add medicine")
        if submitted and name and time_str:
            add_medicine(name, time_str, remind_min)
            st.success("Added medicine.")

    update_all_statuses()
    check_and_trigger_beeps()
    maybe_beep()

    st.subheader("Today's checklist")
    for m in sorted(st.session_state.meds, key=lambda x: parse_hhmm(x["time_str"])):
        col1, col2, col3, col4 = st.columns([0.45, 0.2, 0.2, 0.15])
        color = status_color(m["status"])
        with col1:
            st.markdown(f"<div class='pill' style='background:{color}'>{m['name']} • {m['time_str']} • {m['status']}</div>", unsafe_allow_html=True)
            if reminder_window_open(m):
                st.info("Reminder window open")
        with col2:
            if m["status"] != "taken":
                if st.button(f"Mark taken ✅", key=f"take_{m['id']}"):
                    mark_taken(m["id"])
            else:
                st.write(f"Taken at {m.get('taken_at','')}")
        with col3:
            # Edit inline
            with st.expander("Edit"):
                new_name = st.text_input("Name", value=m["name"], key=f"en_{m['id']}")
                new_time = st.text_input("Time (HH:MM)", value=m["time_str"], key=f"et_{m['id']}")
                new_remind = st.number_input("Remind (min)", min_value=0, max_value=120, value=int(m["remind_min"]), step=5, key=f"er_{m['id']}")
                if st.button("Save changes", key=f"save_{m['id']}"):
                    edit_medicine(m["id"], new_name, new_time, new_remind)
                    st.success("Updated.")
        with col4:
            if st.button("🗑️", key=f"del_{m['id']}"):
                delete_medicine(m["id"])
                st.warning("Deleted.")

with right:
    # Metrics
    scheduled, taken, pct_today = adherence_today()
    st.metric(label="Today's adherence", value=f"{pct_today}%", delta=f"{taken}/{scheduled} taken")
    record_daily_history()
    df_week, weekly_pct = weekly_adherence()
    st.metric(label="Weekly adherence (avg)", value=f"{weekly_pct}%")

    st.subheader("Weekly overview")
    st.dataframe(df_week, height=240)
    csv = df_week.to_csv(index=False).encode("utf-8")
    st.download_button("Download weekly report (CSV)", csv, file_name="medtimer_weekly.csv", mime="text/csv")

    st.subheader("Motivation & rewards")
    tip = tip_for_status(pct_today)
    st.info(tip)

    streak = current_streak()
    badge_msg = ""
    if streak >= 7:
        badge_msg = "🏆 Streak Badge: 7-day champion!"
    elif streak >= 3:
        badge_msg = "🥇 Streak Badge: 3-day starter!"
    elif pct_today >= 90:
        badge_msg = "✨ Daily Excellence Badge!"
    elif pct_today >= 80:
        badge_msg = "🌟 Great Adherence Badge!"
    if badge_msg:
        st.success(badge_msg)

    # Turtle trophy
    st.subheader("Encouragement")
    try:
        img = draw_turtle_trophy(max(pct_today, weekly_pct))
        st.image(img, caption="Keep going—small steps, big impact!", use_column_width=True)
    except Exception:
        st.write("Turtle graphics unavailable in this environment—continue focusing on your streak!")

# Footer
st.markdown("---")
st.caption("Designed for clarity and calm. Large fonts, gentle colors, simple actions.")
