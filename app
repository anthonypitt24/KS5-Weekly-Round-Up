import streamlit as st
import requests
import html
from datetime import datetime, date, timedelta

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="KS5 Progression Bulletin",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>
    .main {
        background-color: #f7f8fc;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 2rem;
    }

    .hero {
        padding: 2rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #243b64, #315c9b);
        color: white;
        margin-bottom: 1.5rem;
    }

    .hero h1 {
        color: white;
        margin-bottom: 0.3rem;
    }

    .hero p {
        color: #e8eef8;
        font-size: 1.05rem;
    }

    .stat-card {
        background: white;
        padding: 1.2rem;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }

    .stat-label {
        color: #6b7280;
        margin: 0;
    }

    .opportunity-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }

    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        margin-top: 1rem;
        margin-bottom: 0.8rem;
    }

    .tag {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        background: #eef2ff;
        margin-right: 0.3rem;
        font-size: 0.8rem;
    }

    .deadline {
        font-weight: 600;
    }

    .teams-preview {
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 12px;
        padding: 1.5rem;
        min-height: 500px;
    }

    .teams-title {
        font-size: 1.7rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }

    .teams-subtitle {
        color: #6b7280;
        margin-bottom: 1.5rem;
    }

    .teams-section {
        margin-top: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
    }

    .action-box {
        background: #eef6ff;
        border-left: 5px solid #315c9b;
        padding: 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA
# ============================================================

OPEN_DAYS = [
    {
        "institution": "University of Liverpool",
        "date": "12 October 2026",
        "description": "Explore courses, facilities, student life and university opportunities.",
        "link": "https://www.liverpool.ac.uk/study/undergraduate/open-days/"
    },
    {
        "institution": "Manchester Metropolitan University",
        "date": "19 October 2026",
        "description": "Meet staff and students and explore courses across the university.",
        "link": "https://www.mmu.ac.uk/study/open-days"
    },
    {
        "institution": "University of Chester",
        "date": "26 October 2026",
        "description": "Find out more about courses, accommodation and student support.",
        "link": "https://www1.chester.ac.uk/undergraduate/open-days"
    },
    {
        "institution": "Liverpool John Moores University",
        "date": "2 November 2026",
        "description": "Discover courses and what life is like as an LJMU student.",
        "link": "https://www.ljmu.ac.uk/study/open-days"
    }
]

VIRTUAL_EXPERIENCES = [
    {
        "title": "JPMorgan Software Engineering Simulation",
        "platform": "Forage",
        "area": "Computing",
        "time": "Approximately 5 hours",
        "description": "A practical virtual experience designed for students interested in software engineering and technology.",
        "link": "https://www.theforage.com"
    },
    {
        "title": "Healthcare Virtual Experience",
        "platform": "Springpod",
        "area": "Healthcare",
        "time": "Self-paced",
        "description": "Explore healthcare careers through virtual activities, case studies and employer insight.",
        "link": "https://www.springpod.com"
    },
    {
        "title": "Civil Engineering & Infrastructure Insight",
        "platform": "Uptree",
        "area": "Engineering",
        "time": "Self-paced",
        "description": "Explore engineering projects, infrastructure and careers within the sector.",
        "link": "https://uptree.co"
    }
]

PROGRESSION_TIPS = [
    {
        "title": "Make your CV more powerful",
        "text": "Replace vague phrases such as 'helped out with' with stronger action verbs such as coordinated, assisted, managed, resolved or organised."
    },
    {
        "title": "Use STARR in interviews",
        "text": "Structure competency answers using Situation, Task, Action, Result and Reflection. Focus most of your answer on what YOU actually did."
    },
    {
        "title": "Research degree apprenticeships",
        "text": "Degree apprenticeships allow you to combine employment with higher-level study. Research employers early because recruitment can open months before university applications."
    },
    {
        "title": "Don't choose courses on reputation alone",
        "text": "Look carefully at course content, assessment, placement opportunities, entry requirements, location and graduate outcomes before making your choices."
    },
    {
        "title": "Start building evidence",
        "text": "Keep a record of work experience, volunteering, competitions, projects, reading and responsibilities. These can become valuable evidence in applications and interviews."
    }
]

DEFAULT_DEADLINES = [
    {
        "date": "15 September 2026",
        "title": "Apprenticeship application deadline",
        "type": "Apprenticeship"
    },
    {
        "date": "30 September 2026",
        "title": "University research checkpoint",
        "type": "University"
    },
    {
        "date": "15 October 2026",
        "title": "UCAS preparation checkpoint",
        "type": "UCAS"
    }
]

# ============================================================
# SESSION STATE
# ============================================================

if "vacancies" not in st.session_state:
    st.session_state.vacancies = []

if "selected_vacancies" not in st.session_state:
    st.session_state.selected_vacancies = []

if "selected_open_days" not in st.session_state:
    st.session_state.selected_open_days = []

if "selected_experiences" not in st.session_state:
    st.session_state.selected_experiences = []

if "selected_tip" not in st.session_state:
    st.session_state.selected_tip = None

if "selected_deadlines" not in st.session_state:
    st.session_state.selected_deadlines = []

if "generated_bulletin" not in st.session_state:
    st.session_state.generated_bulletin = ""

# ============================================================
# DFE API
# ============================================================

def fetch_apprenticeships(api_key, postcode, distance, route=""):
    url = "https://api.apprenticeships.education.gov.uk/vacancies"

    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "X-Version": "2"
    }

    params = {
        "postcode": postcode,
        "distanceInMiles": distance,
        "pageSize": 50,
        "sort": "AgeDesc"
    }

    if route:
        params["routes"] = route

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("vacancies", [])

        st.error(
            f"DfE API returned status {response.status_code}. "
            "Check your API key and settings."
        )

    except requests.RequestException as exc:
        st.error(f"Could not connect to the DfE API: {exc}")

    return []

# ============================================================
# HELPERS
# ============================================================

def safe_date(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date()
    except Exception:
        return None


def days_until(date_string):
    try:
        d = datetime.strptime(date_string, "%d %B %Y").date()
        return (d - date.today()).days
    except Exception:
        return None


def create_bulletin_text(
    audience,
    bulletin_date,
    vacancies,
    open_days,
    experiences,
    tip,
    deadlines,
    intro
):
    lines = []

    lines.append("🎓 KS5 PROGRESSION")
    lines.append(f"THIS WEEK — {bulletin_date.strftime('%d %B %Y')}")
    lines.append("")
    lines.append("👋 " + intro)
    lines.append("")

    if vacancies:
        lines.append("💼 APPRENTICESHIP OPPORTUNITIES")
        lines.append("")

        for v in vacancies:
            lines.append(f"**{v['title']}**")
            lines.append(
                f"{v.get('employer', 'Employer')} • "
                f"{v.get('level', 'Level not specified')}"
            )

            if v.get("location"):
                lines.append(f"📍 {v['location']}")

            if v.get("closing"):
                lines.append(f"📅 Closes: {v['closing']}")

            lines.append("")
            lines.append("👉 " + v.get("url", "Find out more"))
            lines.append("")

    if open_days:
        lines.append("🎓 UNIVERSITY & HE")
        lines.append("")

        for item in open_days:
            lines.append(f"**{item['institution']} Open Day**")
            lines.append(f"📅 {item['date']}")
            lines.append(item["description"])
            lines.append("")
            lines.append("👉 " + item["link"])
            lines.append("")

    if experiences:
        lines.append("💻 WORK EXPERIENCE & SUPER-CURRICULAR")
        lines.append("")

        for item in experiences:
            lines.append(f"**{item['title']}**")
            lines.append(
                f"{item['platform']} • {item['area']} • {item['time']}"
            )
            lines.append(item["description"])
            lines.append("")
            lines.append("👉 " + item["link"])
            lines.append("")

    if tip:
        lines.append("💡 PROGRESSION TIP OF THE WEEK")
        lines.append("")
        lines.append(f"**{tip['title']}**")
        lines.append(tip["text"])
        lines.append("")

    if deadlines:
        lines.append("📅 COMING UP")
        lines.append("")

        for d in deadlines:
            lines.append(f"• **{d['date']}** — {d['title']}")

        lines.append("")

    lines.append("🎯 YOUR ACTION THIS WEEK")
    lines.append("")
    lines.append(
        "Spend 20 minutes doing something that moves your next-step plans "
        "forward. Research a course, explore an apprenticeship, improve your "
        "CV or complete a work experience activity."
    )
    lines.append("")

    lines.append("Good luck with your progression planning! 🚀")

    return "\n".join(lines)


def markdown_to_html(text):
    """
    Lightweight conversion for Teams-style preview.
    """
    escaped = html.escape(text)

    escaped = escaped.replace(
        "**",
        "<strong>",
        1
    )

    # More robust replacement for pairs of **
    output = []
    bold = False

    for part in escaped.split("**"):
        if bold:
            output.append(f"<strong>{part}</strong>")
        else:
            output.append(part)
        bold = not bold

    escaped = "".join(output)

    escaped = escaped.replace("\n", "<br>")

    return escaped


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Bulletin Settings")

    audience = st.selectbox(
        "Audience",
        [
            "All KS5",
            "Year 12",
            "Year 13"
        ]
    )

    bulletin_date = st.date_input(
        "Bulletin date",
        value=date.today()
    )

    st.divider()

    st.subheader("💼 Apprenticeships")

    api_key = st.text_input(
        "DfE API key",
        type="password",
        help="Enter your DfE apprenticeship API subscription key."
    )

    postcode = st.text_input(
        "College postcode",
        value="CH65 6TQ"
    )

    radius = st.slider(
        "Search radius",
        min_value=5,
        max_value=50,
        value=20
    )

    route = st.text_input(
        "Optional apprenticeship route",
        placeholder="e.g. Engineering"
    )

    st.divider()

    st.subheader("🎨 Bulletin Style")

    style = st.selectbox(
        "Tone",
        [
            "Friendly",
            "Professional",
            "Energetic",
            "Concise"
        ]
    )

    length = st.selectbox(
        "Length",
        [
            "Short",
            "Standard",
            "Detailed"
        ]
    )

# ============================================================
# HERO
# ============================================================

st.markdown("""
<div class="hero">
    <h1>🎓 KS5 Progression Bulletin</h1>
    <p>
        Find opportunities, curate the best ones and create a polished
        weekly bulletin ready to post into Microsoft Teams.
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# DASHBOARD STATS
# ============================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">{len(st.session_state.vacancies)}</p>
            <p class="stat-label">Live apprenticeships</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">{len(OPEN_DAYS)}</p>
            <p class="stat-label">HE opportunities</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">{len(VIRTUAL_EXPERIENCES)}</p>
            <p class="stat-label">Work experiences</p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">{len(DEFAULT_DEADLINES)}</p>
            <p class="stat-label">Upcoming dates</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.write("")

# ============================================================
# MAIN TABS
# ============================================================

tabs = st.tabs([
    "🏠 Dashboard",
    "💼 Apprenticeships",
    "🎓 University & HE",
    "💻 Work Experience",
    "💡 Progression Tip",
    "📅 Coming Up",
    "📢 Bulletin Builder"
])

# ============================================================
# DASHBOARD
# ============================================================

with tabs[0]:

    st.subheader("Welcome")

    st.write(
        "Use this dashboard to build this week's KS5 progression bulletin. "
        "Select the opportunities you want students to see, then generate "
        "a Teams-ready post."
    )

    st.markdown("### 🎯 Suggested weekly structure")

    c1, c2 = st.columns(2)

    with c1:
        st.info(
            "**1. Apprenticeship spotlight**\n\n"
            "Choose one or two particularly relevant live vacancies."
        )

        st.info(
            "**2. University opportunity**\n\n"
            "Highlight an open day, taster event or useful HE resource."
        )

    with c2:
        st.info(
            "**3. Work experience**\n\n"
            "Give students something practical they can do."
        )

        st.info(
            "**4. Progression action**\n\n"
            "Give students one small action they can complete this week."
        )

    st.markdown("### ⚠️ Upcoming deadlines")

    for deadline in DEFAULT_DEADLINES:
        remaining = days_until(deadline["date"])

        if remaining is not None:
            if remaining < 0:
                icon = "⚫"
            elif remaining <= 7:
                icon = "🔴"
            elif remaining <= 14:
                icon = "🟠"
            else:
                icon = "🟢"

            st.write(
                f"{icon} **{deadline['date']}** — "
                f"{deadline['title']}"
            )

# ============================================================
# APPRENTICESHIPS
# ============================================================

with tabs[1]:

    st.subheader("💼 Live Apprenticeships")

    if not api_key:
        st.info(
            "Enter your DfE API key in the sidebar, then click "
            "**Fetch live vacancies**."
        )

    if st.button(
        "🔎 Fetch Live Vacancies",
        type="primary",
        key="fetch_vacancies"
    ):

        with st.spinner("Searching apprenticeship vacancies..."):

            vacancies = fetch_apprenticeships(
                api_key,
                postcode,
                radius,
                route
            )

            st.session_state.vacancies = vacancies

        if vacancies:
            st.success(
                f"Found {len(vacancies)} apprenticeship vacancies."
            )
        else:
            st.warning(
                "No vacancies were returned. Try increasing the search radius "
                "or changing your filters."
            )

    vacancies = st.session_state.vacancies

    if vacancies:

        st.markdown(
            f"### {len(vacancies)} vacancies found"
        )

        for i, vacancy in enumerate(vacancies):

            title = vacancy.get(
                "title",
                "Apprenticeship opportunity"
            )

            employer = vacancy.get(
                "employerName",
                "Employer"
            )

            level = vacancy.get(
                "apprenticeshipLevel",
                "Level not specified"
            )

            location = vacancy.get(
                "location",
                vacancy.get("address", "Location not specified")
            )

            closing = vacancy.get(
                "closingDate",
                ""
            )

            closing_fmt = (
                closing[:10]
                if closing
                else "Not specified"
            )

            url = vacancy.get(
                "vacancyUrl",
                "https://www.findapprenticeship.service.gov.uk"
            )

            st.markdown(
                '<div class="opportunity-card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f"### {title}"
            )

            st.write(
                f"**{employer}** • {level}"
            )

            st.write(f"📍 {location}")
            st.write(f"📅 Closing: {closing_fmt}")

            st.link_button(
                "View vacancy",
                url
            )

            selected = st.checkbox(
                "Include in this week's bulletin",
                key=f"vacancy_select_{i}"
            )

            if selected:
                selected_item = {
                    "title": title,
                    "employer": employer,
                    "level": level,
                    "location": location,
                    "closing": closing_fmt,
                    "url": url
                }

                existing_titles = [
                    x["title"]
                    for x in st.session_state.selected_vacancies
                ]

                if title not in existing_titles:
                    st.session_state.selected_vacancies.append(
                        selected_item
                    )

            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.selected_vacancies:

        st.success(
            f"{len(st.session_state.selected_vacancies)} "
            "apprenticeship(s) selected."
        )

# ============================================================
# UNIVERSITY
# ============================================================

with tabs[2]:

    st.subheader("🎓 University & HE")

    st.write(
        "Select the events you want included in this week's bulletin."
    )

    for i, item in enumerate(OPEN_DAYS):

        st.markdown(
            '<div class="opportunity-card">',
            unsafe_allow_html=True
        )

        st.markdown(
            f"### 🎓 {item['institution']}"
        )

        st.write(f"📅 **{item['date']}**")
        st.write(item["description"])

        st.link_button(
            "View event",
            item["link"]
        )

        selected = st.checkbox(
            "Include in bulletin",
            key=f"open_day_{i}"
        )

        if selected:

            if item not in st.session_state.selected_open_days:
                st.session_state.selected_open_days.append(item)

        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# WORK EXPERIENCE
# ============================================================

with tabs[3]:

    st.subheader("💻 Work Experience & Super-Curricular")

    area_filter = st.selectbox(
        "Filter by subject area",
        [
            "All",
            "Computing",
            "Healthcare",
            "Engineering"
        ]
    )

    for i, item in enumerate(VIRTUAL_EXPERIENCES):

        if area_filter != "All" and item["area"] != area_filter:
            continue

        st.markdown(
            '<div class="opportunity-card">',
            unsafe_allow_html=True
        )

        st.markdown(
            f"### 💻 {item['title']}"
        )

        st.write(
            f"**{item['platform']}** • "
            f"{item['area']} • "
            f"{item['time']}"
        )

        st.write(item["description"])

        st.link_button(
            "Explore opportunity",
            item["link"]
        )

        selected = st.checkbox(
            "Include in bulletin",
            key=f"experience_{i}"
        )

        if selected:

            if item not in st.session_state.selected_experiences:
                st.session_state.selected_experiences.append(item)

        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# PROGRESSION TIP
# ============================================================

with tabs[4]:

    st.subheader("💡 Progression Tip")

    for i, tip in enumerate(PROGRESSION_TIPS):

        selected = st.radio(
            "",
            [f"**{tip['title']}** — {tip['text']}"],
            key=f"tip_{i}"
        )

        if st.button(
            f"Use '{tip['title']}'",
            key=f"use_tip_{i}"
        ):
            st.session_state.selected_tip = tip
            st.success("Tip selected for the bulletin.")

# ============================================================
# DEADLINES
# ============================================================

with tabs[5]:

    st.subheader("📅 Coming Up")

    st.write(
        "Highlight important dates so students know what needs their attention."
    )

    for i, deadline in enumerate(DEFAULT_DEADLINES):

        remaining = days_until(deadline["date"])

        if remaining is not None:

            if remaining < 0:
                badge = "Past"
            elif remaining == 0:
                badge = "TODAY"
            elif remaining == 1:
                badge = "Tomorrow"
            else:
                badge = f"{remaining} days"

        else:
            badge = ""

        selected = st.checkbox(
            f"**{deadline['date']}** — "
            f"{deadline['title']} "
            f"({badge})",
            key=f"deadline_{i}"
        )

        if selected:
            if deadline not in st.session_state.selected_deadlines:
                st.session_state.selected_deadlines.append(deadline)

# ============================================================
# BULLETIN BUILDER
# ============================================================

with tabs[6]:

    st.subheader("📢 Bulletin Builder")

    st.write(
        "Review what you've selected, edit the introduction and generate "
        "your Teams-ready bulletin."
    )

    # --------------------------------------------------------
    # SELECTION SUMMARY
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Apprenticeships",
            len(st.session_state.selected_vacancies)
        )

    with col2:
        st.metric(
            "HE events",
            len(st.session_state.selected_open_days)
        )

    with col3:
        st.metric(
            "Work experience",
            len(st.session_state.selected_experiences)
        )

    with col4:
        st.metric(
            "Deadlines",
            len(st.session_state.selected_deadlines)
        )

    st.divider()

    intro_options = {
        "Friendly":
            "Here's your weekly round-up of opportunities, events and ideas to help you plan your next steps.",
        "Professional":
            "This week's progression bulletin brings together opportunities and resources to support your next steps.",
        "Energetic":
            "Ready to make progress? Here are this week's opportunities, events and actions to help you move forward!",
        "Concise":
            "Here are this week's key progression opportunities and actions."
    }

    intro = st.text_area(
        "Introduction",
        value=intro_options[style],
        height=100
    )

    st.markdown("### ✏️ Optional custom message")

    custom_message = st.text_area(
        "Add a message for students",
        placeholder="e.g. Year 13 — please pay particular attention to the upcoming deadlines...",
        height=100
    )

    if custom_message.strip():
        intro += "\n\n" + custom_message.strip()

    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    if st.button(
        "✨ Generate Teams Bulletin",
        type="primary",
        use_container_width=True
    ):

        bulletin = create_bulletin_text(
            audience=audience,
            bulletin_date=bulletin_date,
            vacancies=st.session_state.selected_vacancies,
            open_days=st.session_state.selected_open_days,
            experiences=st.session_state.selected_experiences,
            tip=st.session_state.selected_tip,
            deadlines=st.session_state.selected_deadlines,
            intro=intro
        )

        st.session_state.generated_bulletin = bulletin

        st.success(
            "Bulletin generated. Review it below before posting to Teams."
        )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    if st.session_state.generated_bulletin:

        st.divider()

        preview_col, text_col = st.columns([1.1, 0.9])

        with preview_col:

            st.markdown("### 👀 Preview")

            html_preview = markdown_to_html(
                st.session_state.generated_bulletin
            )

            st.markdown(
                f"""
                <div class="teams-preview">
                    <div class="teams-title">
                        📢 KS5 Progression
                    </div>
                    <div class="teams-subtitle">
                        Weekly progression bulletin
                    </div>
                    {html_preview}
                </div>
                """,
                unsafe_allow_html=True
            )

        with text_col:

            st.markdown("### 📋 Teams-ready text")

            edited_bulletin = st.text_area(
                "Edit before copying",
                value=st.session_state.generated_bulletin,
                height=550,
                key="editable_bulletin"
            )

            st.session_state.generated_bulletin = edited_bulletin

            st.download_button(
                "⬇️ Download bulletin",
                data=edited_bulletin,
                file_name=(
                    f"KS5_Progression_"
                    f"{bulletin_date.strftime('%Y-%m-%d')}.txt"
                ),
                mime="text/plain",
                use_container_width=True
            )

        st.divider()

        st.markdown("### 📋 Copy to Microsoft Teams")

        st.info(
            "Click inside the text box above, select all, copy, then paste "
            "into your Microsoft Teams announcement or page."
        )

        st.code(
            st.session_state.generated_bulletin,
            language="text"
        )

        st.success(
            "Tip: In Teams, use **Format** when creating the post if you "
            "want to add a title, banner or announcement styling."
        )

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "KS5 Progression Bulletin Generator • Designed for staff use • "
    "No student personal data is required."
)
