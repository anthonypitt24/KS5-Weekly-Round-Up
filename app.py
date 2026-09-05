import streamlit as st
import requests
import html
import re
from datetime import datetime

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

SEARCHES = {
    "All suitable opportunities": "",
    "Apprenticeships": "apprentice",
    "Trainee roles": "trainee",
    "School leaver": "school leaver",
    "Entry level": "entry level",
    "Junior roles": "junior",
    "Graduate / early career": "graduate",
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

# Words that strongly suggest a role is NOT suitable
# for a typical sixth-form student.
HARD_EXCLUDE_TITLE = [
    "senior",
    "director",
    "head of",
    "chief",
    "principal",
    "associate director",
    "regional manager",
    "area manager",
    "general manager",
    "operations manager",
    "department manager",
    "store manager",
    "branch manager",
    "project manager",
    "account manager",
    "sales manager",
    "marketing manager",
    "finance manager",
    "hr manager",
    "human resources manager",
    "team manager",
    "shift manager",
    "duty manager",
    "practice manager",
    "office manager",
    "registered manager",
    "service manager",
    "clinical manager",
    "nursing manager",
    "lead developer",
    "lead engineer",
    "lead designer",
    "technical lead",
    "principal engineer",
]

# Positive indicators.
EARLY_CAREER_TERMS = [
    "apprentice",
    "apprenticeship",
    "trainee",
    "school leaver",
    "school-leaver",
    "entry level",
    "entry-level",
    "junior",
    "early career",
    "early-career",
    "graduate scheme",
    "graduate programme",
    "graduate program",
    "level 2",
    "level 3",
    "level 4",
    "level 5",
    "level 6",
    "level 7",
    "foundation",
]

# ============================================================
# PAGE STYLING
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px;
        padding: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HEADER
# ============================================================

st.title("🎓 KS5 Progression Hub")

st.markdown(
    """
    **Your next step starts here.**

    Live jobs and early-career opportunities for sixth-form students,
    powered by Adzuna.
    """
)

st.divider()

# ============================================================
# API CREDENTIALS
# ============================================================

def get_credentials():
    try:
        return (
            st.secrets["ADZUNA_APP_ID"],
            st.secrets["ADZUNA_APP_KEY"],
        )
    except Exception:
        return None, None


APP_ID, APP_KEY = get_credentials()

# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = html.unescape(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def truncate(text, length=320):
    text = clean_text(text)

    if len(text) <= length:
        return text

    return text[:length].rsplit(" ", 1)[0] + "..."


def get_title(job):
    return clean_text(
        job.get("title", "Opportunity")
    )


def get_company(job):
    company = job.get("company", {})

    if isinstance(company, dict):
        return clean_text(
            company.get(
                "display_name",
                "Employer not stated"
            )
        )

    return "Employer not stated"


def get_location(job):
    location = job.get("location", {})

    if isinstance(location, dict):
        return clean_text(
            location.get(
                "display_name",
                "Location not stated"
            )
        )

    return "Location not stated"


def get_category(job):
    category = job.get("category", {})

    if isinstance(category, dict):
        return clean_text(
            category.get(
                "label",
                "Other"
            )
        )

    return "Other"


# ============================================================
# SALARY
# ============================================================

def format_salary(job):

    minimum = job.get("salary_min")
    maximum = job.get("salary_max")

    try:
        if minimum and maximum:

            minimum = int(minimum)
            maximum = int(maximum)

            if minimum == maximum:
                return f"£{minimum:,}"

            return f"£{minimum:,} – £{maximum:,}"

        if minimum:
            return f"From £{int(minimum):,}"

        if maximum:
            return f"Up to £{int(maximum):,}"

    except Exception:
        pass

    return "Salary not stated"


# ============================================================
# CONTRACT
# ============================================================

def format_contract(job):

    contract_type = job.get("contract_type")
    contract_time = job.get("contract_time")

    parts = []

    if contract_type:
        parts.append(
            str(contract_type)
            .replace("_", " ")
            .title()
        )

    if contract_time:
        parts.append(
            str(contract_time)
            .replace("_", " ")
            .title()
        )

    if parts:
        return " • ".join(parts)

    return "Contract details not stated"


# ============================================================
# DATE
# ============================================================

def format_created_date(job):

    created = job.get("created")

    if not created:
        return "Date unavailable"

    try:

        dt = datetime.fromisoformat(
            created.replace("Z", "+00:00")
        )

        return dt.strftime("%d %b %Y")

    except Exception:
        return "Date unavailable"


# ============================================================
# STUDENT SUITABILITY
# ============================================================

def assess_student_suitability(job):

    title = get_title(job).lower()

    description = clean_text(
        job.get("description", "")
    ).lower()

    combined = f"{title} {description}"

    score = 0
    reasons = []

    # --------------------------------------------------------
    # HARD TITLE EXCLUSIONS
    # --------------------------------------------------------

    for term in HARD_EXCLUDE_TITLE:

        if term in title:

            return {
                "score": 0,
                "label": "Not suitable",
                "colour": "🔴",
                "include": False,
                "reasons": [
                    "Role appears to require experienced/senior staff."
                ],
            }

    # --------------------------------------------------------
    # POSITIVE TERMS
    # --------------------------------------------------------

    matched_terms = []

    for term in EARLY_CAREER_TERMS:

        if term in combined:

            matched_terms.append(term)

    # Strongest indicators
    if "apprentice" in combined:
        score += 50
        reasons.append("Apprenticeship/Apprentice role")

    if "trainee" in combined:
        score += 35
        reasons.append("Trainee role")

    if "school leaver" in combined:
        score += 40
        reasons.append("School-leaver friendly")

    if "entry level" in combined or "entry-level" in combined:
        score += 30
        reasons.append("Entry-level role")

    if "junior" in combined:
        score += 25
        reasons.append("Junior role")

    if "graduate" in combined:
        score += 15
        reasons.append("Graduate/early-career opportunity")

    # Qualification indicators
    level_matches = [
        term for term in [
            "level 2",
            "level 3",
            "level 4",
            "level 5",
            "level 6",
            "level 7",
        ]
        if term in combined
    ]

    if level_matches:
        score += 20
        reasons.append(
            "Qualification/apprenticeship level mentioned"
        )

    # --------------------------------------------------------
    # NEGATIVE DESCRIPTION INDICATORS
    # --------------------------------------------------------

    negative_description_terms = [
        "years of experience required",
        "5 years experience",
        "5+ years experience",
        "3 years experience",
        "3+ years experience",
        "experienced professional",
        "extensive experience",
        "proven track record",
    ]

    for term in negative_description_terms:

        if term in combined:
            score -= 15

    # --------------------------------------------------------
    # FINAL CLASSIFICATION
    # --------------------------------------------------------

    if score >= 50:

        return {
            "score": min(score, 100),
            "label": "Excellent student match",
            "colour": "🟢",
            "include": True,
            "reasons": reasons,
        }

    if score >= 30:

        return {
            "score": min(score, 100),
            "label": "Good student match",
            "colour": "🟡",
            "include": True,
            "reasons": reasons,
        }

    if score >= 15:

        return {
            "score": min(score, 100),
            "label": "Potential match",
            "colour": "🟠",
            "include": True,
            "reasons": reasons,
        }

    return {
        "score": score,
        "label": "Low student match",
        "colour": "⚪",
        "include": False,
        "reasons": [],
    }


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_jobs(jobs):

    seen = set()
    output = []

    for job in jobs:

        job_id = str(
            job.get("id", "")
        )

        if not job_id:

            job_id = (
                get_title(job).lower()
                + get_company(job).lower()
            )

        if job_id in seen:
            continue

        seen.add(job_id)
        output.append(job)

    return output


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
):

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "sort_by": "date",
        "content-type": "application/json",
    }

    if what:
        params["what"] = what

    if where:
        params["where"] = where

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
                "jobs": [],
                "count": 0,
                "error": (
                    f"Adzuna returned HTTP "
                    f"{response.status_code}"
                ),
            }

        data = response.json()

        return {
            "success": True,
            "jobs": data.get("results", []),
            "count": data.get("count", 0),
            "error": None,
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "jobs": [],
            "count": 0,
            "error": "Adzuna timed out.",
        }

    except requests.exceptions.RequestException as exc:

        return {
            "success": False,
            "jobs": [],
            "count": 0,
            "error": str(exc),
        }

    except ValueError:

        return {
            "success": False,
            "jobs": [],
            "count": 0,
            "error": "Adzuna returned invalid data.",
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
        "Specific job/career",
        placeholder="e.g. engineering",
    )

    location = st.text_input(
        "Location",
        placeholder="e.g. Liverpool",
    )

    career_area = st.selectbox(
        "Career area",
        ["All"] + POPULAR_CAREERS,
    )

    st.divider()

    early_career_only = st.checkbox(
        "🎓 Student-friendly roles only",
        value=True,
    )

    remote_only = st.checkbox(
        "🏠 Remote opportunities only",
        value=False,
    )

    st.divider()

    results_limit = st.slider(
        "Number of jobs to retrieve",
        10,
        50,
        30,
        10,
    )

    st.divider()

    refresh = st.button(
        "🔄 Refresh live opportunities",
        use_container_width=True,
    )

    st.caption(
        "Live vacancy data supplied by Adzuna."
    )


# ============================================================
# CHECK API
# ============================================================

if not APP_ID or not APP_KEY:

    st.error(
        "⚠️ Adzuna API credentials haven't been configured."
    )

    st.markdown(
        """
        ### Add your Adzuna credentials

        In Streamlit Cloud go to:

        **Manage app → Settings → Secrets**

        Add:

        ```toml
        ADZUNA_APP_ID = "YOUR_APPLICATION_ID"
        ADZUNA_APP_KEY = "YOUR_APPLICATION_KEY"
        ```

        Never put your Application Key directly into this Python file.
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


if career_area != "All":

    if search_term:

        search_term = (
            f"{search_term} {career_area}"
        )

    else:

        search_term = career_area


# ============================================================
# IMPROVE "ALL" SEARCH
# ============================================================

# When the user chooses "All suitable opportunities", we need
# some search terms. Otherwise Adzuna can return completely
# general jobs such as managers and chefs.

if early_career_only and not search_term:

    search_term = (
        "apprentice OR trainee OR junior "
        "OR school leaver OR entry level"
    )


# ============================================================
# LOAD
# ============================================================

if refresh:

    st.cache_data.clear()

with st.spinner(
    "🔎 Finding live opportunities..."
):

    result = search_adzuna(
        APP_ID,
        APP_KEY,
        what=search_term,
        where=location.strip(),
        results_per_page=results_limit,
    )


# ============================================================
# ERROR
# ============================================================

if not result["success"]:

    st.error(
        "Unable to retrieve live Adzuna opportunities."
    )

    st.code(result["error"])

    st.stop()


jobs = deduplicate_jobs(
    result["jobs"]
)


# ============================================================
# SCORE JOBS
# ============================================================

scored_jobs = []

for job in jobs:

    assessment = assess_student_suitability(
        job
    )

    job["_assessment"] = assessment

    if not early_career_only:

        assessment["include"] = True

    if assessment["include"]:

        scored_jobs.append(job)


# Sort best student matches first.
scored_jobs.sort(
    key=lambda x: x["_assessment"]["score"],
    reverse=True,
)


# Remote filtering
if remote_only:

    remote_jobs = []

    for job in scored_jobs:

        text = (
            get_title(job)
            + " "
            + clean_text(
                job.get("description", "")
            )
        ).lower()

        if "remote" in text:

            remote_jobs.append(job)

    scored_jobs = remote_jobs


jobs = scored_jobs


# ============================================================
# TOP HEADER STATS
# ============================================================

st.subheader("📊 Opportunity snapshot")

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Suitable opportunities",
        len(jobs),
    )

with col2:

    apprenticeship_count = sum(
        1
        for job in jobs
        if "apprent" in (
            get_title(job)
            + " "
            + clean_text(
                job.get("description", "")
            )
        ).lower()
    )

    st.metric(
        "Apprenticeships",
        apprenticeship_count,
    )

with col3:

    trainee_count = sum(
        1
        for job in jobs
        if "trainee" in (
            get_title(job)
            + " "
            + clean_text(
                job.get("description", "")
            )
        ).lower()
    )

    st.metric(
        "Trainee roles",
        trainee_count,
    )

with col4:

    salaries = [
        job.get("salary_max")
        for job in jobs
        if job.get("salary_max")
    ]

    if salaries:

        average_salary = int(
            sum(salaries) / len(salaries)
        )

        salary_display = (
            f"£{average_salary:,}"
        )

    else:

        salary_display = "—"

    st.metric(
        "Avg. advertised salary",
        salary_display,
    )


st.divider()


# ============================================================
# TABS
# ============================================================

tab_jobs, tab_bulletin, tab_info = st.tabs(
    [
        "💼 Opportunities",
        "📢 Teams Bulletin",
        "ℹ️ About",
    ]
)


# ============================================================
# JOB RESULTS
# ============================================================

with tab_jobs:

    st.subheader(
        "💼 Live opportunities"
    )

    if not jobs:

        st.warning(
            """
            No suitable student opportunities were found.

            Try:
            - a broader location
            - another career area
            - a different opportunity type
            - switching off "Student-friendly roles only"
            """
        )

    else:

        st.caption(
            f"{len(jobs)} suitable opportunities "
            "found from the current Adzuna results."
        )

        for number, job in enumerate(
            jobs,
            start=1,
        ):

            title = get_title(job)
            company = get_company(job)
            location_name = get_location(job)
            category = get_category(job)
            salary = format_salary(job)
            contract = format_contract(job)
            listed = format_created_date(job)

            description = truncate(
                job.get("description", ""),
                350,
            )

            url = job.get(
                "redirect_url"
            )

            assessment = job[
                "_assessment"
            ]

            with st.container(
                border=True
            ):

                # --------------------------------------------
                # TITLE
                # --------------------------------------------

                st.markdown(
                    f"### {number}. {title}"
                )

                st.caption(
                    f"🏢 {company}"
                )

                # --------------------------------------------
                # SUITABILITY
                # --------------------------------------------

                st.success(
                    f"{assessment['colour']} "
                    f"{assessment['label']} "
                    f"— {assessment['score']}/100"
                )

                # --------------------------------------------
                # INFORMATION
                # --------------------------------------------

                info1, info2 = st.columns(2)

                with info1:

                    st.write(
                        f"📍 **Location:** {location_name}"
                    )

                    st.write(
                        f"💷 **Salary:** {salary}"
                    )

                    st.write(
                        f"📋 **Type:** {contract}"
                    )

                with info2:

                    st.write(
                        f"📚 **Area:** {category}"
                    )

                    st.write(
                        f"🕐 **Listed:** {listed}"
                    )

                    if assessment["reasons"]:

                        st.write(
                            "**Why it may suit students:**"
                        )

                        for reason in assessment[
                            "reasons"
                        ][:3]:

                            st.write(
                                f"• {reason}"
                            )

                # --------------------------------------------
                # DESCRIPTION
                # --------------------------------------------

                if description:

                    st.write(
                        description
                    )

                # --------------------------------------------
                # APPLY
                # --------------------------------------------

                if url:

                    st.link_button(
                        "🔗 View full vacancy / apply",
                        url,
                        use_container_width=True,
                    )

                st.caption(
                    "Jobs by Adzuna • "
                    "Always check the original vacancy "
                    "before applying."
                )


# ============================================================
# BULLETIN
# ============================================================

def create_bulletin(
    jobs,
    search_description,
):

    today = datetime.now().strftime(
        "%d %B %Y"
    )

    lines = []

    lines.append(
        "🎓 KS5 PROGRESSION BULLETIN"
    )

    lines.append(
        f"📅 Updated: {today}"
    )

    lines.append("")

    lines.append(
        "🚀 THIS WEEK'S LIVE OPPORTUNITIES"
    )

    lines.append("")

    lines.append(
        "Looking for your next step after sixth form?"
    )

    lines.append(
        "Here are some current opportunities to explore."
    )

    lines.append("")

    if search_description:

        lines.append(
            f"🔎 Focus: {search_description}"
        )

        lines.append("")

    if not jobs:

        lines.append(
            "No suitable opportunities were found "
            "in this search."
        )

    else:

        # Only the strongest 10 go into the bulletin.

        for number, job in enumerate(
            jobs[:10],
            start=1,
        ):

            title = get_title(job)
            company = get_company(job)
            location_name = get_location(job)
            salary = format_salary(job)
            contract = format_contract(job)
            url = job.get(
                "redirect_url",
                "",
            )

            assessment = job[
                "_assessment"
            ]

            lines.append(
                f"{number}. {title}"
            )

            lines.append(
                f"🏢 {company}"
            )

            lines.append(
                f"📍 {location_name}"
            )

            lines.append(
                f"💷 {salary}"
            )

            lines.append(
                f"📋 {contract}"
            )

            lines.append(
                f"⭐ {assessment['label']}"
            )

            if url:

                lines.append(
                    f"🔗 {url}"
                )

            lines.append("")

    lines.append(
        "────────────────────────"
    )

    lines.append("")

    lines.append(
        "💡 BEFORE YOU APPLY"
    )

    lines.append("")

    lines.append(
        "Always read the full vacancy carefully and "
        "check the entry requirements, salary, location "
        "and application information."
    )

    lines.append("")

    lines.append(
        "Need help with your next step, CV, application "
        "or interview? Speak to the sixth-form "
        "progression/careers team."
    )

    lines.append("")

    lines.append(
        "Jobs by Adzuna"
    )

    return "\n".join(lines)


with tab_bulletin:

    st.subheader(
        "📢 Teams Bulletin Generator"
    )

    st.write(
        """
        The box below contains a ready-to-copy bulletin
        for your Microsoft Teams page.
        """
    )

    bulletin = create_bulletin(
        jobs,
        search_term
        if search_term
        else "All suitable opportunities",
    )

    st.text_area(
        "📋 Copy this into Microsoft Teams",
        bulletin,
        height=650,
    )

    st.download_button(
        "⬇️ Download bulletin",
        data=bulletin,
        file_name=(
            "KS5_Progression_Bulletin.txt"
        ),
        mime="text/plain",
        use_container_width=True,
    )

    st.divider()

    st.subheader(
        "📣 Suggested introduction"
    )

    st.info(
        """
        🚀 **This week's progression opportunities are here!**

        Thinking about university, an apprenticeship,
        employment or another route after sixth form?

        Take a look at this week's opportunities and
        don't leave applications until the last minute.

        If you're unsure which route is right for you,
        speak to the sixth-form progression team.
        """
    )


# ============================================================
# ABOUT
# ============================================================

with tab_info:

    st.subheader(
        "ℹ️ About the KS5 Progression Hub"
    )

    st.write(
        """
        The KS5 Progression Hub is designed to help
        sixth-form students find genuine, current
        opportunities.

        Rather than using a static list of jobs, the
        application retrieves current vacancies from
        Adzuna when searches are performed.
        """
    )

    st.markdown(
        """
        ### Current source

        **💼 Adzuna**

        Used for current UK employment opportunities.

        ### Planned future sources

        **🎓 Government apprenticeship vacancies**

        We can add the official apprenticeship API once
        the access issue is resolved.

        **⭐ Amazing Apprenticeships**

        We can add their resources, guides and relevant
        apprenticeship information.

        **🏫 University opportunities**

        We can later add university open days and other
        events using verified university sources.

        ### Important

        This application does **not** invent vacancies,
        salaries or application links.

        Students should always check the original vacancy
        before applying.
        """
    )

    st.caption(
        "Jobs by Adzuna"
    )
