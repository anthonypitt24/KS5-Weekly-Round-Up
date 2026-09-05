import streamlit as st
import requests
import html
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="KS5 Progression Hub",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CONSTANTS
# ============================================================

ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/gb/search/1"

# Searches designed around sixth-form / early-career opportunities.
SEARCHES = {
    "All opportunities": "",
    "Apprenticeships": "apprentice",
    "Trainee roles": "trainee",
    "School leaver": "school leaver",
    "Entry level": "entry level",
    "Junior roles": "junior",
    "Graduate / early career": "graduate",
    "Work experience": "work experience",
}

POPULAR_CAREERS = [
    "Accounting",
    "Administration",
    "Business",
    "Construction",
    "Creative",
    "Education",
    "Engineering",
    "Finance",
    "Healthcare",
    "IT & Technology",
    "Law",
    "Marketing",
    "Media",
    "Science",
    "Social Care",
    "Sport",
]

# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 1.05rem;
        color: #666;
        margin-top: 0.2rem;
        margin-bottom: 1.5rem;
    }

    .stat-card {
        padding: 1.2rem;
        border-radius: 14px;
        border: 1px solid #ddd;
        background: #ffffff;
        text-align: center;
        min-height: 120px;
    }

    .stat-number {
        font-size: 2rem;
        font-weight: 800;
    }

    .stat-label {
        color: #666;
        font-size: 0.9rem;
    }

    .job-card {
        padding: 1.25rem;
        border-radius: 14px;
        border: 1px solid #ddd;
        background: #fff;
        margin-bottom: 1rem;
    }

    .job-title {
        font-size: 1.2rem;
        font-weight: 750;
        margin-bottom: 0.3rem;
    }

    .job-company {
        font-size: 0.95rem;
        color: #555;
        margin-bottom: 0.7rem;
    }

    .job-meta {
        color: #555;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }

    .tag {
        display: inline-block;
        padding: 0.25rem 0.55rem;
        margin-right: 0.35rem;
        margin-bottom: 0.35rem;
        border-radius: 20px;
        background: #f0f2f5;
        font-size: 0.8rem;
    }

    .bulletin {
        padding: 1.5rem;
        border-radius: 14px;
        background: #f7f7f7;
        border: 1px solid #ddd;
        white-space: pre-wrap;
        font-family: Arial, sans-serif;
    }

    .small-note {
        font-size: 0.8rem;
        color: #777;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🎓 KS5 Progression Hub</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
    Live opportunities for sixth-form students — jobs, apprenticeships,
    trainee and early-career roles.
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# API CREDENTIALS
# ============================================================

def get_credentials():
    """
    Gets Adzuna credentials from Streamlit secrets.

    Required:
        ADZUNA_APP_ID
        ADZUNA_APP_KEY
    """

    try:
        app_id = st.secrets["ADZUNA_APP_ID"]
        app_key = st.secrets["ADZUNA_APP_KEY"]
        return app_id, app_key

    except Exception:
        return None, None


APP_ID, APP_KEY = get_credentials()


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    """Remove HTML and tidy whitespace."""

    if not text:
        return ""

    text = html.unescape(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def truncate(text, length=350):
    """Shorten long descriptions."""

    text = clean_text(text)

    if len(text) <= length:
        return text

    return text[:length].rsplit(" ", 1)[0] + "..."


def format_salary(job):
    """Format salary information safely."""

    minimum = job.get("salary_min")
    maximum = job.get("salary_max")

    if minimum and maximum:
        if int(minimum) == int(maximum):
            return f"£{int(minimum):,}"
        return f"£{int(minimum):,} – £{int(maximum):,}"

    if minimum:
        return f"From £{int(minimum):,}"

    if maximum:
        return f"Up to £{int(maximum):,}"

    return "Salary not stated"


def format_location(job):
    """Get Adzuna's display location."""

    location = job.get("location", {})

    if isinstance(location, dict):
        display_name = location.get("display_name")

        if display_name:
            return display_name

    return "Location not stated"


def format_contract(job):
    """Convert Adzuna contract information into readable text."""

    contract_type = job.get("contract_type")
    contract_time = job.get("contract_time")

    parts = []

    if contract_type:
        parts.append(str(contract_type).replace("_", " ").title())

    if contract_time:
        parts.append(str(contract_time).replace("_", " ").title())

    if not parts:
        return "Contract details not stated"

    return " • ".join(parts)


def format_created_date(job):
    """Format Adzuna's created timestamp."""

    created = job.get("created")

    if not created:
        return "Date not available"

    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return "Date not available"


def get_category(job):
    category = job.get("category", {})

    if isinstance(category, dict):
        return category.get("label", "Other")

    return "Other"


def get_company(job):
    company = job.get("company", {})

    if isinstance(company, dict):
        return company.get("display_name", "Employer not stated")

    return "Employer not stated"


def is_likely_early_career(job):
    """
    Additional local filtering.

    We don't want the bulletin accidentally presenting
    obviously senior jobs as sixth-form opportunities.
    """

    title = clean_text(job.get("title", "")).lower()
    description = clean_text(job.get("description", "")).lower()

    combined = f"{title} {description}"

    positive_terms = [
        "apprentice",
        "apprenticeship",
        "trainee",
        "school leaver",
        "entry level",
        "entry-level",
        "junior",
        "graduate",
        "early career",
        "level 2",
        "level 3",
        "level 4",
        "level 5",
        "level 6",
        "level 7",
    ]

    negative_terms = [
        "senior",
        "head of",
        "director",
        "chief",
        "principal",
        "lead developer",
        "manager",
        "management",
    ]

    has_positive = any(term in combined for term in positive_terms)
    has_negative = any(term in title for term in negative_terms)

    if has_negative and not "trainee" in title and not "apprentice" in title:
        return False

    return has_positive


def deduplicate_jobs(jobs):
    """Remove duplicate adverts."""

    seen = set()
    unique = []

    for job in jobs:

        job_id = str(job.get("id", ""))

        if not job_id:
            job_id = (
                str(job.get("title", "")).lower()
                + str(job.get("company", "")).lower()
            )

        if job_id in seen:
            continue

        seen.add(job_id)
        unique.append(job)

    return unique


# ============================================================
# ADZUNA API
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def search_adzuna(
    app_id,
    app_key,
    what="",
    where="",
    results_per_page=30,
    sort_by="date",
    full_time=False,
    permanent=False,
):
    """
    Query the live Adzuna UK jobs API.

    Cache for 15 minutes to avoid repeatedly hitting the API.
    """

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "sort_by": sort_by,
        "content-type": "application/json",
    }

    if what:
        params["what"] = what

    if where:
        params["where"] = where

    if full_time:
        params["full_time"] = 1

    if permanent:
        params["permanent"] = 1

    try:

        response = requests.get(
            ADZUNA_URL,
            params=params,
            timeout=20,
            headers={
                "Accept": "application/json",
                "User-Agent": "KS5-Progression-Hub/1.0",
            },
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Adzuna returned HTTP {response.status_code}",
                "jobs": [],
                "count": 0,
            }

        data = response.json()

        jobs = data.get("results", [])

        return {
            "success": True,
            "error": None,
            "jobs": jobs,
            "count": data.get("count", len(jobs)),
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Adzuna took too long to respond.",
            "jobs": [],
            "count": 0,
        }

    except requests.exceptions.RequestException as exc:
        return {
            "success": False,
            "error": f"Could not connect to Adzuna: {exc}",
            "jobs": [],
            "count": 0,
        }

    except ValueError:
        return {
            "success": False,
            "error": "Adzuna returned an unexpected response.",
            "jobs": [],
            "count": 0,
        }


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🔎 Find opportunities")

    search_type = st.selectbox(
        "Opportunity type",
        list(SEARCHES.keys()),
    )

    custom_search = st.text_input(
        "Search for a specific role",
        placeholder="e.g. accounting, nursing, engineering",
    )

    location = st.text_input(
        "Location",
        placeholder="e.g. Liverpool, Manchester, London",
    )

    remote_only = st.checkbox("🏠 Remote opportunities only")

    st.divider()

    st.subheader("📚 Career area")

    career_area = st.selectbox(
        "Career area",
        ["All"] + POPULAR_CAREERS,
    )

    st.divider()

    results_limit = st.slider(
        "Number of results",
        min_value=10,
        max_value=50,
        value=30,
        step=10,
    )

    st.divider()

    early_career_only = st.checkbox(
        "🎓 Prioritise sixth-form / early-career roles",
        value=True,
    )

    st.divider()

    st.caption(
        "Live job data supplied by Adzuna."
    )

    refresh = st.button(
        "🔄 Refresh live jobs",
        use_container_width=True,
    )

# ============================================================
# CHECK CREDENTIALS
# ============================================================

if not APP_ID or not APP_KEY:

    st.error("⚠️ Adzuna API credentials have not been configured.")

    st.markdown(
        """
        ### Add your credentials

        Create this file:

        `.streamlit/secrets.toml`

        Then add:

        ```toml
        ADZUNA_APP_ID = "YOUR_APPLICATION_ID"
        ADZUNA_APP_KEY = "YOUR_APPLICATION_KEY"
        ```

        **Do not put your API key directly into `app.py`.**

        Once you've added the keys, restart Streamlit.
        """
    )

    st.stop()


# ============================================================
# BUILD SEARCH
# ============================================================

if custom_search.strip():

    search_term = custom_search.strip()

else:

    search_term = SEARCHES[search_type]


# Add career area to search where appropriate.
if career_area != "All":

    if search_term:
        search_term = f"{search_term} {career_area}"
    else:
        search_term = career_area


# ============================================================
# LOAD JOBS
# ============================================================

if refresh:
    st.cache_data.clear()


with st.spinner("🔎 Searching live Adzuna vacancies..."):

    result = search_adzuna(
        APP_ID,
        APP_KEY,
        what=search_term,
        where=location.strip(),
        results_per_page=results_limit,
        sort_by="date",
    )


# ============================================================
# ERROR
# ============================================================

if not result["success"]:

    st.error("Unable to retrieve live jobs.")

    st.code(result["error"])

    st.info(
        "Check that your Adzuna Application ID and Application Key "
        "are correctly entered in Streamlit Secrets."
    )

    st.stop()


jobs = result["jobs"]


# ============================================================
# EARLY CAREER FILTER
# ============================================================

if early_career_only:

    filtered_jobs = [
        job for job in jobs
        if is_likely_early_career(job)
    ]

    # If filtering removes everything, don't leave the user
    # with a blank page.
    if filtered_jobs:
        jobs = filtered_jobs


# ============================================================
# REMOTE FILTER
# ============================================================

if remote_only:

    jobs = [
        job for job in jobs
        if "remote" in (
            clean_text(job.get("title", "")) + " "
            + clean_text(job.get("description", ""))
        ).lower()
    ]


# ============================================================
# DEDUPLICATE
# ============================================================

jobs = deduplicate_jobs(jobs)


# ============================================================
# DASHBOARD STATS
# ============================================================

st.markdown("### 📊 Opportunity snapshot")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-number">{len(jobs)}</div>
            <div class="stat-label">Opportunities found</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:

    apprenticeship_count = sum(
        1
        for job in jobs
        if "apprent" in (
            clean_text(job.get("title", "")) + " "
            + clean_text(job.get("description", ""))
        ).lower()
    )

    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-number">{apprenticeship_count}</div>
            <div class="stat-label">Apprenticeship-type roles</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:

    trainee_count = sum(
        1
        for job in jobs
        if "trainee" in (
            clean_text(job.get("title", "")) + " "
            + clean_text(job.get("description", ""))
        ).lower()
    )

    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-number">{trainee_count}</div>
            <div class="stat-label">Trainee roles</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:

    salaries = [
        job.get("salary_max")
        for job in jobs
        if job.get("salary_max")
    ]

    average_salary = (
        int(sum(salaries) / len(salaries))
        if salaries
        else 0
    )

    salary_text = (
        f"£{average_salary:,}"
        if average_salary
        else "—"
    )

    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-number">{salary_text}</div>
            <div class="stat-label">Average advertised max salary</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.write("")


# ============================================================
# TABS
# ============================================================

tab_jobs, tab_bulletin, tab_about = st.tabs(
    [
        "💼 Live opportunities",
        "📢 Teams bulletin",
        "ℹ️ About",
    ]
)


# ============================================================
# JOB LIST
# ============================================================

with tab_jobs:

    st.markdown("### 💼 Live opportunities")

    if not jobs:

        st.warning(
            "No matching early-career opportunities were found. "
            "Try a broader search or switch off the early-career filter."
        )

    else:

        st.caption(
            f"Showing {len(jobs)} current opportunities returned by Adzuna."
        )

        for index, job in enumerate(jobs):

            title = clean_text(
                job.get("title", "Untitled opportunity")
            )

            company = get_company(job)
            location_name = format_location(job)
            salary = format_salary(job)
            contract = format_contract(job)
            category = get_category(job)
            created = format_created_date(job)

            description = truncate(
                job.get("description", ""),
                450,
            )

            url = job.get("redirect_url", "#")

            st.markdown(
                f"""
                <div class="job-card">

                    <div class="job-title">
                        {html.escape(title)}
                    </div>

                    <div class="job-company">
                        🏢 {html.escape(company)}
                    </div>

                    <div class="job-meta">
                        📍 {html.escape(location_name)}
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        💷 {html.escape(salary)}
                    </div>

                    <div class="job-meta">
                        📋 {html.escape(contract)}
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        📚 {html.escape(category)}
                    </div>

                    <div class="job-meta">
                        🕐 Listed: {html.escape(created)}
                    </div>

                    <p>
                        {html.escape(description)}
                    </p>

                </div>
                """,
                unsafe_allow_html=True,
            )

            if url and url != "#":

                st.link_button(
                    "View / apply for this opportunity →",
                    url,
                    use_container_width=False,
                )

            st.markdown(
                '<div class="small-note">Jobs by Adzuna</div>',
                unsafe_allow_html=True,
            )

            if index < len(jobs) - 1:
                st.divider()


# ============================================================
# TEAMS BULLETIN GENERATOR
# ============================================================

def create_bulletin(jobs, search_description):
    """Create Teams-ready bulletin text."""

    today = datetime.now().strftime("%d %B %Y")

    lines = []

    lines.append("🎓 KS5 PROGRESSION BULLETIN")
    lines.append("")
    lines.append(f"📅 Week commencing: {today}")
    lines.append("")
    lines.append(
        "💼 LIVE JOB & EARLY-CAREER OPPORTUNITIES"
    )
    lines.append("")
    lines.append(
        "Looking for your next step after sixth form? "
        "Here are some current opportunities worth exploring."
    )
    lines.append("")

    if search_description:
        lines.append(
            f"🔎 Search focus: {search_description}"
        )
        lines.append("")

    if not jobs:

        lines.append(
            "No matching opportunities were found today."
        )

    else:

        # Limit the Teams bulletin to the strongest first 10.
        for number, job in enumerate(jobs[:10], start=1):

            title = clean_text(
                job.get("title", "Opportunity")
            )

            company = get_company(job)
            location_name = format_location(job)
            salary = format_salary(job)
            contract = format_contract(job)
            category = get_category(job)
            url = job.get("redirect_url", "")

            lines.append(
                f"{number}. {title}"
            )

            lines.append(
                f"🏢 Employer: {company}"
            )

            lines.append(
                f"📍 Location: {location_name}"
            )

            lines.append(
                f"💷 Salary: {salary}"
            )

            lines.append(
                f"📋 Type: {contract}"
            )

            lines.append(
                f"📚 Area: {category}"
            )

            if url:
                lines.append(
                    f"🔗 Apply / view vacancy: {url}"
                )

            lines.append("")

    lines.append("────────────────────────")
    lines.append("")
    lines.append(
        "⭐ REMEMBER"
    )
    lines.append("")
    lines.append(
        "Always check the full vacancy before applying. "
        "Entry requirements, closing dates and vacancy details "
        "can change."
    )
    lines.append("")
    lines.append(
        "💡 Need help with applications, CVs, interviews or "
        "choosing your next step? Speak to the sixth-form "
        "careers/progression team."
    )
    lines.append("")
    lines.append(
        "Jobs by Adzuna"
    )

    return "\n".join(lines)


with tab_bulletin:

    st.markdown("### 📢 Generate your Teams bulletin")

    st.write(
        """
        This creates a clean text version that you can copy into
        Microsoft Teams, a Teams post, newsletter or student bulletin.
        """
    )

    bulletin = create_bulletin(
        jobs,
        search_term if search_term else "All early-career opportunities",
    )

    st.text_area(
        "Teams-ready bulletin",
        bulletin,
        height=700,
    )

    st.download_button(
        "⬇️ Download bulletin as TXT",
        data=bulletin,
        file_name="ks5_progression_bulletin.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.markdown("---")

    st.markdown(
        """
        ### 💡 Suggested Teams introduction

        **🚀 This week's progression opportunities are here!**

        Whether you're thinking about university, an apprenticeship,
        employment or another route after sixth form, take a look at
        this week's opportunities.

        Don't leave applications until the last minute — check the
        requirements and closing dates carefully.
        """
    )


# ============================================================
# ABOUT
# ============================================================

with tab_about:

    st.markdown("### ℹ️ About the KS5 Progression Hub")

    st.write(
        """
        The KS5 Progression Hub is designed to help sixth-form students
        find genuine current opportunities without relying on static
        lists that quickly become out of date.
        """
    )

    st.markdown(
        """
        #### Current data source

        **Adzuna**

        The application currently uses Adzuna's live UK job search API.

        Jobs are retrieved when the bulletin is generated and are not
        manually invented or stored as static examples.

        #### Planned future sources

        🎓 Government apprenticeship vacancies

        ⭐ Amazing Apprenticeships resources

        🏫 Verified university open days

        🧑‍💼 Work experience opportunities

        These can be added later without replacing the Adzuna system.
        """
    )

    st.markdown(
        """
        #### Important

        Vacancy information can change. Students should always check
        the original vacancy page before applying.
        """
    )

    st.markdown(
        '<div class="small-note">Jobs by Adzuna</div>',
        unsafe_allow_html=True,
    )
