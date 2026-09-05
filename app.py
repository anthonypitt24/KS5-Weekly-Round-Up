import streamlit as st
import requests
import html
from datetime import datetime, date, timedelta
from urllib.parse import quote

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="KS5 Progression Hub",
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
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

.hero {
    padding: 2.2rem;
    border-radius: 20px;
    background: linear-gradient(135deg, #203864, #315c9b);
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 25px rgba(0,0,0,0.08);
}

.hero h1 {
    color: white;
    font-size: 2.4rem;
    margin-bottom: 0.3rem;
}

.hero p {
    color: #e8eef8;
    font-size: 1.05rem;
    margin-bottom: 0;
}

.stat-card {
    background: white;
    padding: 1.25rem;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 3px 12px rgba(0,0,0,0.04);
}

.stat-number {
    font-size: 2rem;
    font-weight: 750;
    margin: 0;
}

.stat-label {
    color: #6b7280;
    margin: 0;
}

.opportunity-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}

.live-badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    background: #dcfce7;
    color: #166534;
    font-size: 0.8rem;
    font-weight: 700;
}

.verified-badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    background: #dbeafe;
    color: #1e40af;
    font-size: 0.8rem;
    font-weight: 700;
}

.warning-badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    background: #fef3c7;
    color: #92400e;
    font-size: 0.8rem;
    font-weight: 700;
}

.section-header {
    font-size: 1.35rem;
    font-weight: 750;
    margin-top: 1.2rem;
    margin-bottom: 0.8rem;
}

.teams-preview {
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 14px;
    padding: 1.5rem;
    min-height: 500px;
}

.teams-title {
    font-size: 1.7rem;
    font-weight: 750;
}

.teams-subtitle {
    color: #6b7280;
    margin-bottom: 1.5rem;
}

.source-line {
    color: #6b7280;
    font-size: 0.85rem;
}

.action-box {
    background: #eef6ff;
    border-left: 5px solid #315c9b;
    padding: 1rem;
    border-radius: 8px;
}

.small-muted {
    color: #6b7280;
    font-size: 0.85rem;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# CONSTANTS
# ============================================================

TODAY = date.today()

# ============================================================
# VERIFIED UNIVERSITY EVENTS
#
# IMPORTANT:
# These are deliberately kept separate from live jobs.
# Only put dates here after checking the university's
# official events page.
# ============================================================

UNIVERSITY_EVENTS = [
    {
        "institution": "University of Liverpool",
        "event": "Undergraduate Open Day",
        "date": None,
        "description": "Explore courses, facilities, student life and accommodation.",
        "link": "https://www.liverpool.ac.uk/study/undergraduate/open-days/",
        "verified": False,
        "last_checked": None
    },
    {
        "institution": "Liverpool John Moores University",
        "event": "Open Day",
        "date": None,
        "description": "Explore courses, facilities, student support and life at LJMU.",
        "link": "https://www.ljmu.ac.uk/study/open-days",
        "verified": False,
        "last_checked": None
    },
    {
        "institution": "Manchester Metropolitan University",
        "event": "Open Day",
        "date": None,
        "description": "Meet staff and students and explore courses and facilities.",
        "link": "https://www.mmu.ac.uk/study/open-days",
        "verified": False,
        "last_checked": None
    },
    {
        "institution": "University of Chester",
        "event": "Open Day",
        "date": None,
        "description": "Explore courses, accommodation, facilities and student support.",
        "link": "https://www1.chester.ac.uk/undergraduate/open-days",
        "verified": False,
        "last_checked": None
    }
]

# ============================================================
# WORK EXPERIENCE
# ============================================================

WORK_EXPERIENCES = [
    {
        "title": "JPMorgan Software Engineering Simulation",
        "platform": "Forage",
        "area": "Computing",
        "time": "Approximately 5 hours",
        "description": "Practical virtual experience for students interested in software engineering and technology.",
        "link": "https://www.theforage.com"
    },
    {
        "title": "Healthcare Virtual Experiences",
        "platform": "Springpod",
        "area": "Healthcare",
        "time": "Self-paced",
        "description": "Explore healthcare careers through virtual activities, case studies and employer insight.",
        "link": "https://www.springpod.com"
    },
    {
        "title": "Engineering Virtual Experiences",
        "platform": "Uptree",
        "area": "Engineering",
        "time": "Self-paced",
        "description": "Explore engineering projects, infrastructure and careers.",
        "link": "https://uptree.co"
    },
    {
        "title": "Virtual Work Experience",
        "platform": "Springpod",
        "area": "All subjects",
        "time": "Self-paced",
        "description": "Explore different industries and careers through employer-led virtual experiences.",
        "link": "https://www.springpod.com"
    }
]

# ============================================================
# PROGRESSION TIPS
# ============================================================

PROGRESSION_TIPS = [
    {
        "title": "Build evidence, not just a CV",
        "text": "Keep a record of work experience, volunteering, projects, competitions, responsibilities and achievements."
    },
    {
        "title": "Use STARR in interviews",
        "text": "Structure competency answers using Situation, Task, Action, Result and Reflection. Focus on what you personally did."
    },
    {
        "title": "Research degree apprenticeships",
        "text": "Degree apprenticeships combine employment with higher-level study. Research employers early because recruitment can open months before university applications."
    },
    {
        "title": "Don't choose a university on reputation alone",
        "text": "Compare course content, assessment, placement opportunities, entry requirements, location and graduate outcomes."
    },
    {
        "title": "Start researching employers",
        "text": "Don't wait until you are ready to apply. Follow employers you're interested in and understand what they look for in school-leaver applicants."
    }
]

# ============================================================
# DEADLINES
#
# These are examples/checkpoints rather than claimed external
# deadlines. They are safe to edit locally.
# ============================================================

DEFAULT_DEADLINES = [
    {
        "date": "15 September 2026",
        "title": "Review apprenticeship opportunities",
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

defaults = {
    "jobs": [],
    "apprenticeships": [],
    "selected_jobs": [],
    "selected_apprenticeships": [],
    "selected_open_days": [],
    "selected_experiences": [],
    "selected_tip": None,
    "selected_deadlines": [],
    "generated_bulletin": "",
    "last_job_refresh": None,
    "last_apprenticeship_refresh": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# DATE HELPERS
# ============================================================

def parse_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    formats = [
        "%d %B %Y",
        "%d %b %Y",
        "%Y-%m-%d",
        "%d/%m/%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue

    return None


def days_until(value):
    d = parse_date(value)

    if not d:
        return None

    return (d - TODAY).days


def is_expired(value):
    remaining = days_until(value)

    return remaining is not None and remaining < 0


def format_date(value):
    d = parse_date(value)

    if not d:
        return "Not specified"

    return d.strftime("%d %B %Y")


# ============================================================
# ADZUNA LIVE JOBS API
# ============================================================

def fetch_jobs(
    app_id,
    app_key,
    postcode,
    distance,
    keywords="",
    results=50
):

    if not app_id or not app_key:
        return []

    url = (
        "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    )

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results,
        "what": keywords,
        "where": postcode,
        "distance": distance,
        "content-type": "application/json",
        "sort_by": "date"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        if response.status_code != 200:
            st.error(
                f"Jobs API returned HTTP {response.status_code}."
            )
            return []

        data = response.json()

        jobs = []

        for job in data.get("results", []):

            title = job.get(
                "title",
                "Job opportunity"
            )

            company = (
                job.get("company", {})
                .get("display_name", "Employer")
            )

            location = (
                job.get("location", {})
                .get("display_name", "Location not specified")
            )

            salary_min = job.get("salary_min")
            salary_max = job.get("salary_max")

            if salary_min and salary_max:
                salary = (
                    f"£{int(salary_min):,}–"
                    f"£{int(salary_max):,}"
                )
            elif salary_min:
                salary = f"From £{int(salary_min):,}"
            else:
                salary = "Salary not specified"

            created = job.get("created")

            created_date = None

            if created:
                try:
                    created_date = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    ).date()
                except Exception:
                    pass

            category = (
                job.get("category", {})
                .get("label", "General")
            )

            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "category": category,
                    "created": created_date,
                    "description": job.get(
                        "description",
                        ""
                    ),
                    "url": job.get(
                        "redirect_url",
                        ""
                    ),
                    "source": "Adzuna"
                }
            )

        return jobs

    except requests.RequestException as exc:

        st.error(
            f"Could not connect to the jobs service: {exc}"
        )

        return []


# ============================================================
# DFE APPRENTICESHIPS
# ============================================================

def fetch_apprenticeships(
    api_key,
    postcode,
    distance,
    route=""
):

    if not api_key:
        return []

    url = (
        "https://api.apprenticeships.education.gov.uk/"
        "vacancies"
    )

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
            timeout=20
        )

        if response.status_code != 200:

            st.error(
                f"DfE Apprenticeships API returned "
                f"HTTP {response.status_code}."
            )

            return []

        data = response.json()

        return data.get("vacancies", [])

    except requests.RequestException as exc:

        st.error(
            f"Could not connect to the DfE apprenticeship service: {exc}"
        )

        return []


# ============================================================
# JOB FILTERING
# ============================================================

def job_is_relevant(job, keywords):

    if not keywords:
        return True

    text = " ".join(
        [
            str(job.get("title", "")),
            str(job.get("company", "")),
            str(job.get("category", "")),
            str(job.get("description", ""))
        ]
    ).lower()

    return any(
        keyword.lower() in text
        for keyword in keywords
    )


# ============================================================
# BULLETIN GENERATOR
# ============================================================

def create_bulletin(
    audience,
    bulletin_date,
    jobs,
    apprenticeships,
    open_days,
    experiences,
    tip,
    deadlines,
    intro
):

    lines = []

    lines.append("🎓 KS5 PROGRESSION")
    lines.append(
        f"THIS WEEK — {bulletin_date.strftime('%d %B %Y')}"
    )

    lines.append("")

    lines.append("👋 " + intro)

    lines.append("")

    # --------------------------------------------------------
    # JOBS
    # --------------------------------------------------------

    if jobs:

        lines.append("💼 LIVE JOBS")
        lines.append("")

        for job in jobs:

            lines.append(
                f"**{job['title']}**"
            )

            lines.append(
                f"{job.get('company', 'Employer')} • "
                f"{job.get('location', 'Location not specified')}"
            )

            if job.get("salary"):
                lines.append(
                    f"💷 {job['salary']}"
                )

            if job.get("category"):
                lines.append(
                    f"🏷️ {job['category']}"
                )

            lines.append("")

            if job.get("url"):
                lines.append(
                    "👉 " + job["url"]
                )

            lines.append("")

    # --------------------------------------------------------
    # APPRENTICESHIPS
    # --------------------------------------------------------

    if apprenticeships:

        lines.append("🎓 LIVE APPRENTICESHIPS")
        lines.append("")

        for apprenticeship in apprenticeships:

            title = apprenticeship.get(
                "title",
                "Apprenticeship opportunity"
            )

            employer = apprenticeship.get(
                "employerName",
                "Employer"
            )

            level = apprenticeship.get(
                "apprenticeshipLevel",
                "Level not specified"
            )

            closing = apprenticeship.get(
                "closingDate",
                ""
            )

            location = apprenticeship.get(
                "location",
                apprenticeship.get(
                    "address",
                    "Location not specified"
                )
            )

            url = apprenticeship.get(
                "vacancyUrl",
                "https://www.findapprenticeship.service.gov.uk/"
            )

            lines.append(
                f"**{title}**"
            )

            lines.append(
                f"{employer} • {level}"
            )

            lines.append(
                f"📍 {location}"
            )

            if closing:
                lines.append(
                    f"📅 Closes: {closing[:10]}"
                )

            lines.append("")

            lines.append(
                "👉 " + url
            )

            lines.append("")

    # --------------------------------------------------------
    # UNIVERSITY
    # --------------------------------------------------------

    if open_days:

        lines.append("🏛️ UNIVERSITY & HE")
        lines.append("")

        for item in open_days:

            lines.append(
                f"**{item['institution']} — "
                f"{item['event']}**"
            )

            if item.get("date"):

                lines.append(
                    f"📅 {format_date(item['date'])}"
                )

            else:

                lines.append(
                    "📅 Check the official university page "
                    "for the latest date."
                )

            lines.append(
                item["description"]
            )

            lines.append("")

            lines.append(
                "👉 " + item["link"]
            )

            lines.append("")

    # --------------------------------------------------------
    # WORK EXPERIENCE
    # --------------------------------------------------------

    if experiences:

        lines.append(
            "💻 WORK EXPERIENCE & SUPER-CURRICULAR"
        )

        lines.append("")

        for item in experiences:

            lines.append(
                f"**{item['title']}**"
            )

            lines.append(
                f"{item['platform']} • "
                f"{item['area']} • "
                f"{item['time']}"
            )

            lines.append(
                item["description"]
            )

            lines.append("")

            lines.append(
                "👉 " + item["link"]
            )

            lines.append("")

    # --------------------------------------------------------
    # TIP
    # --------------------------------------------------------

    if tip:

        lines.append(
            "💡 PROGRESSION TIP OF THE WEEK"
        )

        lines.append("")

        lines.append(
            f"**{tip['title']}**"
        )

        lines.append(
            tip["text"]
        )

        lines.append("")

    # --------------------------------------------------------
    # DEADLINES
    # --------------------------------------------------------

    if deadlines:

        lines.append(
            "📅 COMING UP"
        )

        lines.append("")

        for deadline in deadlines:

            lines.append(
                f"• **{deadline['date']}** — "
                f"{deadline['title']}"
            )

        lines.append("")

    # --------------------------------------------------------
    # ACTION
    # --------------------------------------------------------

    lines.append(
        "🎯 YOUR ACTION THIS WEEK"
    )

    lines.append("")

    lines.append(
        "Spend 20 minutes doing something that moves "
        "your next-step plans forward. Search for a job, "
        "explore an apprenticeship, research a university "
        "course, improve your CV or complete a work "
        "experience activity."
    )

    lines.append("")

    lines.append(
        "Good luck with your progression planning! 🚀"
    )

    lines.append("")

    lines.append(
        f"Audience: {audience}"
    )

    return "\n".join(lines)


# ============================================================
# MARKDOWN → HTML
# ============================================================

def markdown_to_html(text):

    escaped = html.escape(text)

    output = []

    parts = escaped.split("**")

    bold = False

    for part in parts:

        if bold:
            output.append(
                f"<strong>{part}</strong>"
            )
        else:
            output.append(part)

        bold = not bold

    result = "".join(output)

    result = result.replace(
        "\n",
        "<br>"
    )

    return result


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Hub Settings")

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
        value=TODAY
    )

    st.divider()

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    st.subheader("📍 Search Area")

    postcode = st.text_input(
        "College postcode",
        value="CH65 6TQ"
    )

    radius = st.slider(
        "Search radius",
        min_value=5,
        max_value=50,
        value=20,
        step=5
    )

    st.divider()

    # --------------------------------------------------------
    # ADZUNA
    # --------------------------------------------------------

    st.subheader("💼 Live Jobs")

    adzuna_app_id = st.text_input(
        "Adzuna App ID",
        type="password"
    )

    adzuna_app_key = st.text_input(
        "Adzuna App Key",
        type="password"
    )

    job_keywords = st.text_input(
        "Job search",
        placeholder="e.g. part time, retail, IT, admin"
    )

    st.caption(
        "Leave the search blank to retrieve a broad selection "
        "of current vacancies."
    )

    st.divider()

    # --------------------------------------------------------
    # DFE
    # --------------------------------------------------------

    st.subheader("🎓 Apprenticeships")

    dfe_api_key = st.text_input(
        "DfE API key",
        type="password"
    )

    apprenticeship_route = st.text_input(
        "Optional route",
        placeholder="e.g. Engineering"
    )

    st.divider()

    # --------------------------------------------------------
    # STYLE
    # --------------------------------------------------------

    st.subheader("🎨 Bulletin")

    style = st.selectbox(
        "Tone",
        [
            "Friendly",
            "Professional",
            "Energetic",
            "Concise"
        ]
    )

# ============================================================
# HERO
# ============================================================

st.markdown("""
<div class="hero">

<h1>🎓 KS5 Progression Hub</h1>

<p>
Live jobs, apprenticeships, university opportunities,
work experience and progression advice — curated into
a weekly Microsoft Teams bulletin.
</p>

</div>
""", unsafe_allow_html=True)

# ============================================================
# TOP STATS
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:

    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">
                {len(st.session_state.jobs)}
            </p>
            <p class="stat-label">
                Live jobs
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with c2:

    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">
                {len(st.session_state.apprenticeships)}
            </p>
            <p class="stat-label">
                Apprenticeships
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:

    verified_events = [
        x for x in UNIVERSITY_EVENTS
        if x.get("verified")
        and x.get("date")
        and not is_expired(x.get("date"))
    ]

    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">
                {len(verified_events)}
            </p>
            <p class="stat-label">
                Verified HE events
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with c4:

    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">
                {len(WORK_EXPERIENCES)}
            </p>
            <p class="stat-label">
                Work experiences
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with c5:

    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-number">
                {len(DEFAULT_DEADLINES)}
            </p>
            <p class="stat-label">
                Planning dates
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.write("")

# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "🏠 Dashboard",
        "💼 Live Jobs",
        "🎓 Apprenticeships",
        "🏛️ University & HE",
        "💻 Work Experience",
        "💡 Progression Tip",
        "📅 Coming Up",
        "📢 Build Bulletin"
    ]
)

# ============================================================
# DASHBOARD
# ============================================================

with tabs[0]:

    st.subheader("This week's progression hub")

    st.write(
        "Refresh the live sources, select the strongest opportunities "
        "and then build a Teams-ready bulletin."
    )

    st.markdown("### 🔄 Refresh live data")

    refresh1, refresh2 = st.columns(2)

    with refresh1:

        if st.button(
            "🔎 Refresh Live Jobs",
            use_container_width=True,
            type="primary"
        ):

            with st.spinner(
                "Searching current jobs..."
            ):

                keywords = job_keywords.strip()

                jobs = fetch_jobs(
                    adzuna_app_id,
                    adzuna_app_key,
                    postcode,
                    radius,
                    keywords
                )

                st.session_state.jobs = jobs

                st.session_state.last_job_refresh = (
                    datetime.now()
                )

            if jobs:

                st.success(
                    f"Found {len(jobs)} current jobs."
                )

            else:

                st.warning(
                    "No jobs found. Check your API credentials "
                    "or search settings."
                )

    with refresh2:

        if st.button(
            "🎓 Refresh Apprenticeships",
            use_container_width=True,
            type="primary"
        ):

            with st.spinner(
                "Searching current apprenticeships..."
            ):

                apprenticeships = fetch_apprenticeships(
                    dfe_api_key,
                    postcode,
                    radius,
                    apprenticeship_route
                )

                st.session_state.apprenticeships = (
                    apprenticeships
                )

                st.session_state.last_apprenticeship_refresh = (
                    datetime.now()
                )

            if apprenticeships:

                st.success(
                    f"Found {len(apprenticeships)} apprenticeship vacancies."
                )

            else:

                st.warning(
                    "No apprenticeship vacancies found."
                )

    st.divider()

    st.markdown("### ⭐ Recommended workflow")

    a, b, c = st.columns(3)

    with a:

        st.info(
            "**1. Refresh**\n\n"
            "Get the latest jobs and apprenticeships."
        )

    with b:

        st.info(
            "**2. Curate**\n\n"
            "Select the opportunities most useful to students."
        )

    with c:

        st.info(
            "**3. Publish**\n\n"
            "Generate the Teams-ready bulletin."
        )

    st.markdown("### 🛡️ Information quality")

    st.success(
        "Live jobs and apprenticeships are retrieved from external "
        "services. University dates are deliberately NOT invented "
        "by this application."
    )

# ============================================================
# LIVE JOBS
# ============================================================

with tabs[1]:

    st.subheader("💼 Live Jobs")

    if not st.session_state.jobs:

        st.info(
            "No live jobs loaded yet. Enter your Adzuna credentials "
            "and use **Refresh Live Jobs**."
        )

    else:

        jobs = st.session_state.jobs

        st.write(
            f"Showing {len(jobs)} jobs."
        )

        # Filters

        fc1, fc2, fc3 = st.columns(3)

        with fc1:

            job_type_filter = st.selectbox(
                "Job type",
                [
                    "All",
                    "Part-time",
                    "Full-time",
                    "Apprenticeship",
                    "Trainee",
                    "Entry level"
                ]
            )

        with fc2:

            category_filter = st.text_input(
                "Filter category",
                placeholder="e.g. IT"
            )

        with fc3:

            selected_days = st.selectbox(
                "Posted within",
                [
                    "Any time",
                    "7 days",
                    "14 days",
                    "30 days"
                ]
            )

        if selected_days == "7 days":
            cutoff = TODAY - timedelta(days=7)
        elif selected_days == "14 days":
            cutoff = TODAY - timedelta(days=14)
        elif selected_days == "30 days":
            cutoff = TODAY - timedelta(days=30)
        else:
            cutoff = None

        filtered_jobs = []

        for job in jobs:

            title_text = job.get(
                "title",
                ""
            ).lower()

            category_text = job.get(
                "category",
                ""
            ).lower()

            if job_type_filter != "All":

                if job_type_filter.lower() not in title_text:
                    continue

            if category_filter:

                if category_filter.lower() not in category_text:
                    continue

            created = job.get("created")

            if cutoff and created:

                if created < cutoff:
                    continue

            filtered_jobs.append(job)

        st.write(
            f"**{len(filtered_jobs)} jobs match your filters.**"
        )

        for i, job in enumerate(filtered_jobs):

            st.markdown(
                '<div class="opportunity-card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f"### 💼 {job['title']}"
            )

            st.write(
                f"**{job['company']}** • "
                f"{job['location']}"
            )

            st.write(
                f"💷 {job['salary']} • "
                f"🏷️ {job['category']}"
            )

            if job.get("created"):

                st.write(
                    f"🕒 Posted: "
                    f"{format_date(job['created'])}"
                )

            if job.get("description"):

                description = (
                    job["description"]
                    .replace("\n", " ")
                )

                if len(description) > 350:
                    description = (
                        description[:350] + "..."
                    )

                st.write(description)

            if job.get("url"):

                st.link_button(
                    "View vacancy",
                    job["url"]
                )

            selected = st.checkbox(
                "⭐ Include in bulletin",
                key=f"job_{i}"
            )

            if selected:

                if job not in st.session_state.selected_jobs:

                    st.session_state.selected_jobs.append(
                        job
                    )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

        if st.session_state.selected_jobs:

            st.success(
                f"{len(st.session_state.selected_jobs)} "
                "job(s) selected."
            )

# ============================================================
# APPRENTICESHIPS
# ============================================================

with tabs[2]:

    st.subheader("🎓 Live Apprenticeships")

    apprenticeships = (
        st.session_state.apprenticeships
    )

    if not apprenticeships:

        st.info(
            "No apprenticeships loaded. Add your DfE API key "
            "and refresh the live apprenticeship search."
        )

    else:

        for i, vacancy in enumerate(
            apprenticeships
        ):

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
                vacancy.get(
                    "address",
                    "Location not specified"
                )
            )

            closing = vacancy.get(
                "closingDate",
                ""
            )

            url = vacancy.get(
                "vacancyUrl",
                "https://www.findapprenticeship.service.gov.uk/"
            )

            st.markdown(
                '<div class="opportunity-card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f"### 🎓 {title}"
            )

            st.write(
                f"**{employer}** • {level}"
            )

            st.write(
                f"📍 {location}"
            )

            if closing:

                st.write(
                    f"📅 Closing: {closing[:10]}"
                )

            st.link_button(
                "View apprenticeship",
                url
            )

            selected = st.checkbox(
                "⭐ Include in bulletin",
                key=f"apprenticeship_{i}"
            )

            if selected:

                if vacancy not in st.session_state.selected_apprenticeships:

                    st.session_state.selected_apprenticeships.append(
                        vacancy
                    )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

# ============================================================
# UNIVERSITY
# ============================================================

with tabs[3]:

    st.subheader("🏛️ University & HE")

    st.warning(
        "University event dates are intentionally blank unless "
        "they have been verified. This prevents the system from "
        "publishing incorrect open-day dates."
    )

    for i, item in enumerate(
        UNIVERSITY_EVENTS
    ):

        st.markdown(
            '<div class="opportunity-card">',
            unsafe_allow_html=True
        )

        st.markdown(
            f"### 🏛️ {item['institution']}"
        )

        st.write(
            f"**{item['event']}**"
        )

        if (
            item.get("verified")
            and item.get("date")
            and not is_expired(item["date"])
        ):

            st.markdown(
                '<span class="verified-badge">'
                '✓ VERIFIED DATE'
                '</span>',
                unsafe_allow_html=True
            )

            st.write(
                f"📅 **{format_date(item['date'])}**"
            )

            if item.get("last_checked"):

                st.caption(
                    f"Last checked: {item['last_checked']}"
                )

        else:

            st.markdown(
                '<span class="warning-badge">'
                'DATE NEEDS CHECKING'
                '</span>',
                unsafe_allow_html=True
            )

        st.write(
            item["description"]
        )

        st.link_button(
            "Check official university page",
            item["link"]
        )

        selected = st.checkbox(
            "Include in bulletin",
            key=f"university_{i}"
        )

        if selected:

            if item not in st.session_state.selected_open_days:

                st.session_state.selected_open_days.append(
                    item
                )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )

# ============================================================
# WORK EXPERIENCE
# ============================================================

with tabs[4]:

    st.subheader(
        "💻 Work Experience & Super-Curricular"
    )

    areas = sorted(
        set(
            item["area"]
            for item in WORK_EXPERIENCES
        )
    )

    area_filter = st.selectbox(
        "Subject area",
        ["All"] + areas
    )

    for i, item in enumerate(
        WORK_EXPERIENCES
    ):

        if (
            area_filter != "All"
            and item["area"] != area_filter
        ):
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

        st.write(
            item["description"]
        )

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

                st.session_state.selected_experiences.append(
                    item
                )

        st.markdown(
            "</div>",
            unsafe_allow_html=True
        )

# ============================================================
# PROGRESSION TIP
# ============================================================

with tabs[5]:

    st.subheader(
        "💡 Progression Tip"
    )

    for i, tip in enumerate(
        PROGRESSION_TIPS
    ):

        with st.expander(
            tip["title"]
        ):

            st.write(
                tip["text"]
            )

            if st.button(
                f"Use this tip",
                key=f"tip_button_{i}"
            ):

                st.session_state.selected_tip = tip

                st.success(
                    "Tip selected."
                )

# ============================================================
# DEADLINES
# ============================================================

with tabs[6]:

    st.subheader(
        "📅 Coming Up"
    )

    st.write(
        "These are college planning checkpoints. "
        "Do not treat them as official external deadlines "
        "unless you have verified them."
    )

    for i, deadline in enumerate(
        DEFAULT_DEADLINES
    ):

        remaining = days_until(
            deadline["date"]
        )

        if remaining is None:

            badge = ""

        elif remaining < 0:

            badge = "⚫ Past"

        elif remaining == 0:

            badge = "🔴 TODAY"

        elif remaining == 1:

            badge = "🟠 Tomorrow"

        elif remaining <= 7:

            badge = f"🔴 {remaining} days"

        elif remaining <= 14:

            badge = f"🟠 {remaining} days"

        else:

            badge = f"🟢 {remaining} days"

        selected = st.checkbox(
            f"**{deadline['date']}** — "
            f"{deadline['title']} "
            f"({badge})",
            key=f"deadline_{i}"
        )

        if selected:

            if deadline not in st.session_state.selected_deadlines:

                st.session_state.selected_deadlines.append(
                    deadline
                )

# ============================================================
# BULLETIN BUILDER
# ============================================================

with tabs[7]:

    st.subheader(
        "📢 Build Teams Bulletin"
    )

    # --------------------------------------------------------
    # SELECTION COUNTS
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Jobs",
            len(
                st.session_state.selected_jobs
            )
        )

    with c2:

        st.metric(
            "Apprenticeships",
            len(
                st.session_state.selected_apprenticeships
            )
        )

    with c3:

        st.metric(
            "HE",
            len(
                st.session_state.selected_open_days
            )
        )

    with c4:

        st.metric(
            "Work experience",
            len(
                st.session_state.selected_experiences
            )
        )

    st.divider()

    # --------------------------------------------------------
    # INTRO
    # --------------------------------------------------------

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

    custom_message = st.text_area(
        "Optional message to students",
        placeholder=(
            "e.g. Year 13 — please pay particular "
            "attention to the apprenticeship vacancies "
            "closing this week."
        ),
        height=100
    )

    if custom_message.strip():

        intro += (
            "\n\n" +
            custom_message.strip()
        )

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    unverified_events = [
        item for item
        in st.session_state.selected_open_days
        if not (
            item.get("verified")
            and item.get("date")
            and not is_expired(item.get("date"))
        )
    ]

    if unverified_events:

        st.warning(
            f"{len(unverified_events)} selected HE event(s) "
            "do not have a verified date. They will appear with "
            "'check the official university page' rather than "
            "an invented date."
        )

    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    if st.button(
        "✨ Generate Teams Bulletin",
        type="primary",
        use_container_width=True
    ):

        bulletin = create_bulletin(

            audience=audience,

            bulletin_date=bulletin_date,

            jobs=st.session_state.selected_jobs,

            apprenticeships=(
                st.session_state.selected_apprenticeships
            ),

            open_days=(
                st.session_state.selected_open_days
            ),

            experiences=(
                st.session_state.selected_experiences
            ),

            tip=(
                st.session_state.selected_tip
            ),

            deadlines=(
                st.session_state.selected_deadlines
            ),

            intro=intro
        )

        st.session_state.generated_bulletin = bulletin

        st.success(
            "Bulletin generated."
        )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    if st.session_state.generated_bulletin:

        st.divider()

        preview_col, text_col = st.columns(
            [1.1, 0.9]
        )

        with preview_col:

            st.markdown(
                "### 👀 Teams Preview"
            )

            preview = markdown_to_html(
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

                    {preview}

                </div>
                """,
                unsafe_allow_html=True
            )

        with text_col:

            st.markdown(
                "### 📋 Teams-ready text"
            )

            edited = st.text_area(
                "Edit before posting",
                value=(
                    st.session_state.generated_bulletin
                ),
                height=600,
                key="editable_bulletin"
            )

            st.session_state.generated_bulletin = edited

            st.download_button(
                "⬇️ Download bulletin",
                data=edited,
                file_name=(
                    "KS5_Progression_"
                    f"{bulletin_date.strftime('%Y-%m-%d')}.txt"
                ),
                mime="text/plain",
                use_container_width=True
            )

        st.divider()

        st.markdown(
            "### 📋 Copy to Microsoft Teams"
        )

        st.info(
            "Copy the text from the box above and paste it "
            "into your Teams announcement. Use Teams' formatting "
            "options to add a banner or announcement styling."
        )

        st.code(
            st.session_state.generated_bulletin,
            language="text"
        )

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "KS5 Progression Hub • Staff use • "
    "Live opportunity data + verified information • "
    "No student personal data required"
)
