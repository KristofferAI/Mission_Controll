import streamlit as st
import pandas as pd
from src.db import add_job, complete_job, list_jobs, list_bots


def render():
    st.title("⚙️ Jobs")
    st.markdown("---")

    jobs    = list_jobs()
    bots    = list_bots()
    pending = [j for j in jobs if j["status"] == "pending"]
    done    = [j for j in jobs if j["status"] == "done"]

    c1, c2, c3 = st.columns(3)
    c1.metric("📋 Total Jobs",   len(jobs))
    c2.metric("⏳ Pending",       len(pending))
    c3.metric("✅ Completed",     len(done))

    st.markdown("---")
    col_list, col_form = st.columns([2, 1])

    # ── Schedule form ─────────────────────────────────────────────────────────
    with col_form:
        st.subheader("📋 Schedule Job")
        if not bots:
            st.warning("Register a bot first in the **Bots** tab.")
        else:
            with st.form("add_job_form", clear_on_submit=True):
                bot_opts = {b["name"]: b["id"] for b in bots}
                sel_bot  = st.selectbox("Assign to Bot", list(bot_opts.keys()))
                title    = st.text_input("Job Title *", placeholder="Fetch EPL Fixtures")
                desc     = st.text_area("Description", placeholder="Optional details...")
                sub      = st.form_submit_button("Schedule Job", use_container_width=True)
                if sub:
                    if title.strip():
                        add_job(bot_opts[sel_bot], title.strip(), desc)
                        st.success(f"✅ Job **{title}** scheduled!")
                        st.rerun()
                    else:
                        st.error("Job title is required.")

    # ── Job list ──────────────────────────────────────────────────────────────
    with col_list:
        st.subheader("All Jobs")
        if not jobs:
            st.info("No jobs scheduled yet.")
        else:
            for job in pending:
                with st.expander(f"⏳ {job['title']} — {job.get('bot_name', '?')}"):
                    st.write(f"**Bot:** {job.get('bot_name', 'Unknown')}")
                    st.write(f"**Created:** {job['created_at'][:16]}")
                    if job["description"]:
                        st.caption(job["description"])
                    if st.button("✅ Mark Done", key=f"done_{job['id']}"):
                        complete_job(job["id"])
                        st.success("Job completed!")
                        st.rerun()

            if done:
                st.markdown("---")
                st.subheader("✅ Completed Jobs")
                df = pd.DataFrame(done)[["title", "bot_name", "created_at", "completed_at"]]
                df.columns = ["Job", "Bot", "Created", "Completed"]
                st.dataframe(df, use_container_width=True, hide_index=True)
