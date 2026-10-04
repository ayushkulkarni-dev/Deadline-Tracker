import streamlit as st
import pandas as pd
from database import get_deadlines
from utils import days_left, categorize, days_label

ORDER = ["Overdue", "Due today", "Tomorrow", "This Week", "Upcoming"]

# which Streamlit colour box each category uses
STYLE = {
    "Overdue": st.error,
    "Due today": st.warning,
    "Tomorrow": st.warning,
    "This Week": st.info,
    "Upcoming": st.success,
}


def render_dashboard():
    st.header("📊 Deadline Dashboard")

    # ---------- Load from SQLite ----------
    df = pd.DataFrame(get_deadlines())

    if df.empty:
        st.info("No deadlines saved yet. Add some below and click Save.")
        return

    df[["subject", "time", "description"]] = df[["subject", "time", "description"]].fillna("")
    df["days_left"] = df["date"].apply(days_left)

    bad = int(df["days_left"].isna().sum())
    if bad:
        st.warning(f"{bad} deadline(s) have an invalid date and are hidden. Fix them in the review table.")
        df = df[df["days_left"].notna()].copy()
        if df.empty:
            return
    df["days_left"] = df["days_left"].astype(int)
    df["category"] = df["days_left"].apply(categorize)

    # ---------- Subject filter ----------
    subjects = sorted(s for s in df["subject"].unique() if s)
    chosen = st.selectbox("Filter by subject", ["All"] + subjects)
    if chosen != "All":
        df = df[df["subject"] == chosen]

    if df.empty:
        st.info("No deadlines for this subject.")
        return

    # ---------- Summary cards ----------
    counts = df["category"].value_counts()
    cols = st.columns(len(ORDER) + 1)
    cols[0].metric("Total", len(df))
    for col, name in zip(cols[1:], ORDER):
        col.metric(name, counts.get(name, 0))

    # ---------- Next deadline (days remaining) ----------
    coming = df[df["days_left"] >= 0].sort_values(["days_left", "time"])
    if not coming.empty:
        nxt = coming.iloc[0]
        st.info(f"⏭ **Next deadline:** {nxt['title']} ({nxt['subject']}) — "
                f"{days_label(nxt['days_left'])}")

    st.divider()

    # ---------- Sections ----------
    for name in ORDER:
        group = df[df["category"] == name].sort_values(["date", "time"])
        if group.empty:
            continue

        st.subheader(f"{name} ({len(group)})")
        for _, row in group.iterrows():
            with st.container(border=True):
                a, b, c = st.columns([3, 2, 1.5])
                a.markdown(f"**{row['title']}**  \n{row['subject']}")
                when = pd.to_datetime(row["date"]).strftime("%d %b %Y")
                b.write(f"{when} {row['time']}")
                with c:
                    STYLE[name](days_label(row["days_left"]))
