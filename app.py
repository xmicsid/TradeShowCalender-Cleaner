# app.py
from datetime import datetime
import streamlit as st
from clean_tradeshow import parse_many

st.set_page_config(page_title="Trade Show Calendar → Clean CSV", layout="wide")
st.title("Trade Show Calendar → Clean CSV")
st.caption(
    "Drag & drop one or more **saved HTML pages** (Webpage, HTML only) from thetradeshowcalendar. "
    "Get a clean CSV with Exhibitors/Attendees and dates."
)

with st.expander("How to save pages (once):", expanded=False):
    st.markdown("""
1. Open a page (e.g., page 1, page 2, …).
2. **Save As… → Webpage, HTML only** (e.g., `page01.html`, `page02.html`).
3. Drag the saved `.html` files into the uploader below.
""")

uploads = st.file_uploader(
    "Drop HTML files here",
    type=["html", "htm"],
    accept_multiple_files=True
)

if uploads:
    contents = [u.read() for u in uploads]
    df = parse_many(contents).copy()
    df.reset_index(drop=True, inplace=True)

    if df.empty:
        st.warning("No rows parsed. Double-check the page was saved as **HTML only**.")
        st.stop()

    st.success(f"Parsed {len(df):,} rows from {len(uploads)} file(s).")
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)

    # Optional quick filter
    with st.expander("Quick filter (optional)"):
        col1, col2 = st.columns(2)
        with col1:
            min_exh = st.number_input("Minimum Exhibitors", value=0, min_value=0, step=50)
        with col2:
            min_att = st.number_input("Minimum Attendees", value=0, min_value=0, step=100)

        show = df[(df["Exhibitors"].fillna(0) >= min_exh) & (df["Attendees"].fillna(0) >= min_att)].copy()
        show.reset_index(drop=True, inplace=True)
        st.write(f"{len(show):,} rows after filter")
        st.dataframe(show.head(200), use_container_width=True, hide_index=True)

    # Download CSV only (keeps it bulletproof)
    csv_bytes = show.to_csv(index=False).encode("utf-8")
    fname = f"upcoming_hv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.download_button("Download CSV", data=csv_bytes, file_name=fname, mime="text/csv")
else:
    st.info("Drop one or more saved HTML pages to begin.")
