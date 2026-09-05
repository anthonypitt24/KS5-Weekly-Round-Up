import streamlit as st
import requests
import html
import re
from datetime import datetime, date
from urllib.parse import quote_plus


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
# STYLING
# ============================================================

st.markdown("""
<style>

.main {
    background-color: #f7f9fc;
}

.hero {
    padding: 28px;
    border-radius: 18px;
    background: linear-gradient(135deg, #172554, #2563eb);
    color: white;
    margin-bottom: 25px;
}

.hero h1 {
    font-size: 38px;
    margin-bottom: 5px;
}

.hero p {
    font-size: 17px;
    opacity: 0.95;
}

.card {
    background: white;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    margin-bottom: 14px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.04);
}

.card h3 {
    margin-top: 0;
}

.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 20px;
    background: #e0e7ff;
    color: #3730a3;
    font-size: 12px;
    font-weight: 700;
    margin-right: 5px;
}

.source {
    font-size: 12px;
    color: #6b7280;
}

.bulletin {
    background: white;
    padding: 28px;
    border-radius: 16px;
    border: 1px solid #d1d5db;
}

.small {
    font-size: 13px;
    color: #6b7280;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTS
# ============================================================

TODAY = date.today()

ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/gb/search/1"

CAREER_AREAS = [
    "All subjects",
    "Accounting & Finance",
    "Administration & Business",
    "Construction",
    "Creative & Design",
    "Education",
    "Engineering",
    "Healthcare",
    "IT & Technology",
    "Law",
    "Marketing",
    "Media",
    "Science",
    "Social Care",
    "Sport",
    "Other"
]

YEAR_GROUPS = [
    "All KS5",
    "Year 12",
    "Year 13",
    "Year 12 & 13"
]

LOCATIONS = [
    "All locations",
    "UK-wide",
    "England",
    "Scotland",
    "Wales",
    "Northern Ireland",
    "North West",
    "North East",
    "Yorkshire",
    "West Midlands",
    "East Midlands",
    "East of England",
    "London",
    "South East",
    "South West"
]


# ============================================================
# SESSION STATE
# ============================================================

if "opportunities" not in st.session_state:
    st.session_state.opportunities = []

if "custom_opportunities" not in st.session_state:
    st.session_state.custom_opportunities = []

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def make_opportunity(
    title,
    organisation,
    category,
    description,
    location,
    date_text,
    closing_date,
    url,
    source,
    year_group="All KS5",
    subject="All subjects",
    verified=False
):
    return {
        "id": f"{category}-{title}-{organisation}-{url}",
        "title": clean_text(title),
        "organisation": clean_text(organisation),
        "category": category,
        "description": clean_text(description),
        "location": clean_text(location),
        "date": clean_text(date_text),
        "closing_date": clean_text(closing_date),
        "url": url,
        "source": source,
        "year_group": year_group,
        "subject": subject,
        "verified": verified
    }


# ============================================================
# ADZUNA
# ============================================================

def get_adzuna_credentials():

    try:
        app_id = st.secrets["ADZUNA_APP_ID"]
        app_key = st.secrets["ADZUNA_APP_KEY"]

        return app_id, app_key

    except Exception:
        return None, None


def search_adzuna_apprenticeships(
    subject="All subjects",
    location="All locations",
    results=30
):

    app_id, app_key = get_adzuna_credentials()

    if not app_id or not app_key:
        return []

    keywords = [
        "apprentice",
        "apprenticeship",
        "trainee",
        "school leaver",
        "degree apprenticeship"
    ]

    if subject != "All subjects":
        subject_keywords = {
            "Accounting & Finance": "accounting finance",
            "Administration & Business": "business administration",
            "Construction": "construction",
            "Creative & Design": "creative design",
            "Education": "education teaching",
            "Engineering": "engineering",
            "Healthcare": "healthcare",
            "IT & Technology": "IT technology software",
            "Law": "law legal",
            "Marketing": "marketing",
            "Media": "media",
            "Science": "science laboratory",
            "Social Care": "social care",
            "Sport": "sport"
        }

        keywords.append(
            subject_keywords.get(subject, subject)
        )

    query = " ".join(keywords)

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results,
        "what": query,
        "content-type": "application/json",
        "sort_by": "date",
        "max_days_old": 30
    }

    if location != "All locations":
        params["where"] = location

    try:

        response = requests.get(
            ADZUNA_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

    except Exception as e:

        st.warning(
            f"Adzuna could not be reached: {e}"
        )

        return []

    opportunities = []

    for job in data.get("results", []):

        title = clean_text(
            job.get("title", "")
        )

        description = clean_text(
            job.get("description", "")
        )

        combined = (
            title + " " + description
        ).lower()

        # ----------------------------------------------------
        # STRICT STUDENT/APPRENTICESHIP FILTER
        # ----------------------------------------------------

        positive_terms = [
            "apprentice",
            "apprenticeship",
            "trainee",
            "school leaver",
            "degree apprentice",
            "higher apprentice",
            "level 2",
            "level 3",
            "level 4",
            "level 5",
            "level 6",
            "level 7"
        ]

        negative_terms = [
            "senior",
            "manager",
            "director",
            "head of",
            "lead engineer",
            "principal",
            "experienced professional",
            "minimum 5 years",
            "minimum 3 years",
            "qualified accountant"
        ]

        if not any(
            term in combined
            for term in positive_terms
        ):
            continue

        if any(
            term in combined
            for term in negative_terms
        ):
            continue

        company = clean_text(
            job.get("company", {}).get(
                "display_name",
                ""
            )
        )

        location_name = clean_text(
            job.get("location", {}).get(
                "display_name",
                ""
            )
        )

        url = job.get("redirect_url", "")

        salary = ""

        minimum = job.get("salary_min")
        maximum = job.get("salary_max")

        if minimum and maximum:
            salary = (
                f"Salary: £{minimum:,.0f}–"
                f"£{maximum:,.0f}"
            )
        elif minimum:
            salary = f"Salary from £{minimum:,.0f}"

        description_final = description

        if salary:
            description_final += f" {salary}"

        opportunities.append(
            make_opportunity(
                title=title,
                organisation=company,
                category="🎓 Apprenticeship",
                description=description_final,
                location=location_name,
                date_text="Live vacancy",
                closing_date="Check vacancy",
                url=url,
                source="Adzuna",
                year_group="Year 12 & 13",
                subject=subject,
                verified=False
            )
        )

    return opportunities


# ============================================================
# UCAS
# ============================================================

def ucas_open_days_link():

    return (
        "https://www.ucas.com/explore/search/events"
        "?eventType=Open%20day"
    )


def get_ucas_opportunities():

    return [

        make_opportunity(
            title="UCAS Open Days & Events",
            organisation="UCAS",
            category="🏫 University Open Days",
            description=(
                "Search university open days, exhibitions "
                "and other higher education events. "
                "Use the UCAS filters to find events by "
                "institution, location and event type."
            ),
            location="UK",
            date_text="Dates shown on UCAS",
            closing_date="Varies",
            url=ucas_open_days_link(),
            source="UCAS",
            year_group="Year 12 & 13",
            subject="All subjects",
            verified=True
        ),

        make_opportunity(
            title="UCAS University Open Days Guide",
            organisation="UCAS",
            category="🏫 University Open Days",
            description=(
                "UCAS guidance explaining what happens at "
                "open days and how students can use them "
                "when choosing where to study."
            ),
            location="UK",
            date_text="Guidance",
            closing_date="N/A",
            url=(
                "https://www.ucas.com/applying/"
                "before-you-apply/what-and-where-to-study/"
                "university-open-days"
            ),
            source="UCAS",
            year_group="All KS5",
            subject="All subjects",
            verified=True
        )
    ]


# ============================================================
# AMAZING APPRENTICESHIPS
# ============================================================

def get_amazing_apprenticeships():

    return [

        make_opportunity(
            title="Higher & Degree Apprenticeship Vacancy Listing",
            organisation="Amazing Apprenticeships",
            category="🎓 Apprenticeship",
            description=(
                "A specialist listing of higher and degree "
                "apprenticeship vacancies from employers. "
                "Particularly useful for Year 13 students "
                "considering degree-level apprenticeships."
            ),
            location="UK",
            date_text="Current listings",
            closing_date="Check individual vacancy",
            url=(
                "https://www.amazingapprenticeships.com/"
                "higher-degree-listing/"
            ),
            source="Amazing Apprenticeships",
            year_group="Year 13",
            subject="All subjects",
            verified=True
        ),

        make_opportunity(
            title="Apprenticeship Resources",
            organisation="Amazing Apprenticeships",
            category="📚 Resource",
            description=(
                "Student-friendly resources covering "
                "apprenticeships, employers, careers, "
                "application guidance and progression."
            ),
            location="Online",
            date_text="Available now",
            closing_date="N/A",
            url=(
                "https://www.amazingapprenticeships.com/"
                "resources/"
            ),
            source="Amazing Apprenticeships",
            year_group="All KS5",
            subject="All subjects",
            verified=True
        )
    ]


# ============================================================
# OTHER VERIFIED RESOURCES
# ============================================================

def get_resources():

    return [

        make_opportunity(
            title="UCAS Discover",
            organisation="UCAS",
            category="📚 Resource",
            description=(
                "Explore university subjects, careers, "
                "apprenticeships and progression options."
            ),
            location="Online",
            date_text="Available now",
            closing_date="N/A",
            url="https://www.ucas.com/discover",
            source="UCAS",
            year_group="All KS5",
            subject="All subjects",
            verified=True
        ),

        make_opportunity(
            title="UCAS Apprenticeships",
            organisation="UCAS",
            category="📚 Resource",
            description=(
                "Information about apprenticeships, "
                "including degree apprenticeships and "
                "how to search for opportunities."
            ),
            location="Online",
            date_text="Available now",
            closing_date="N/A",
            url="https://www.ucas.com/apprenticeships",
            source="UCAS",
            year_group="All KS5",
            subject="All subjects",
            verified=True
        ),

        make_opportunity(
            title="Find an Apprenticeship",
            organisation="GOV.UK",
            category="🎓 Apprenticeship",
            description=(
                "Official Government apprenticeship vacancy "
                "search. Students can search and apply for "
                "live apprenticeship vacancies."
            ),
            location="UK",
            date_text="Live vacancies",
            closing_date="Varies",
            url=(
                "https://www.gov.uk/apply-apprenticeship"
            ),
            source="GOV.UK",
            year_group="All KS5",
            subject="All subjects",
            verified=True
        )
    ]


# ============================================================
# WORK EXPERIENCE
# ============================================================

def get_work_experience():

    return [

        make_opportunity(
            title="Work Experience – Find Local Opportunities",
            organisation="GOV.UK",
            category="💼 Work Experience",
            description=(
                "Use the Government careers service to "
                "explore careers, employers and routes into "
                "different sectors. Check individual "
                "employers for current work experience "
                "availability."
            ),
            location="UK",
            date_text="Check employer availability",
            closing_date="Varies",
            url=(
                "https://nationalcareers.service.gov.uk/"
            ),
            source="National Careers Service",
            year_group="All KS5",
            subject="All subjects",
            verified=True
        )
    ]


# ============================================================
# FILTERING
# ============================================================

def filter_opportunities(
    opportunities,
    category,
    subject,
    year_group,
    location
):

    filtered = []

    for item in opportunities:

        if category != "All opportunities":
            if item["category"] != category:
                continue

        if subject != "All subjects":

            if (
                item["subject"] != "All subjects"
                and item["subject"] != subject
            ):
                continue

        if year_group != "All KS5":

            if (
                item["year_group"] != "All KS5"
                and year_group not in item["year_group"]
            ):
                continue

        if location != "All locations":

            item_location = item["location"].lower()

            if location.lower() not in item_location:
                continue

        filtered.append(item)

    return filtered


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(items):

    seen = set()
    result = []

    for item in items:

        key = (
            item["title"].lower(),
            item["organisation"].lower(),
            item["url"]
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


# ============================================================
# DISPLAY OPPORTUNITY
# ============================================================

def display_opportunity(item, index):

    st.markdown(
        f"""
        <div class="card">

        <span class="badge">{item["category"]}</span>

        <h3>{html.escape(item["title"])}</h3>

        <strong>
        {html.escape(item["organisation"])}
        </strong>

        <p>
        {html.escape(item["description"])}
        </p>

        <p>
        📍 {html.escape(item["location"])}
        </p>

        <p>
        📅 {html.escape(item["date"])}
        </p>

        <p>
        ⏰ Closing: {html.escape(item["closing_date"])}
        </p>

        <p class="source">
        Source: {html.escape(item["source"])}
        {" • ✓ Verified source" if item["verified"] else ""}
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 5])

    with col1:

        if item["url"]:

            st.link_button(
                "Open opportunity",
                item["url"]
            )

    with col2:

        if st.button(
            "🗑️ Remove",
            key=f"remove_{index}_{item['id']}"
        ):

            st.session_state.opportunities = [
                x for x in st.session_state.opportunities
                if x["id"] != item["id"]
            ]

            st.rerun()


# ============================================================
# BULLETIN GENERATOR
# ============================================================

def create_bulletin(items):

    today_text = TODAY.strftime("%d %B %Y")

    lines = []

    lines.append("🎓 KS5 PROGRESSION BULLETIN")
    lines.append("")
    lines.append(
        f"Week commencing {today_text}"
    )
    lines.append("")
    lines.append(
        "Here are this week's opportunities, "
        "events and resources for KS5 students."
    )
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    categories = [
        "🎓 Apprenticeship",
        "🏫 University Open Days",
        "💼 Work Experience",
        "🌟 Other Opportunity",
        "📚 Resource"
    ]

    for category in categories:

        category_items = [
            x for x in items
            if x["category"] == category
        ]

        if not category_items:
            continue

        lines.append(category.upper())
        lines.append("")

        for item in category_items:

            lines.append(
                f"🔹 {item['title']}"
            )

            if item["organisation"]:
                lines.append(
                    f"Organisation: {item['organisation']}"
                )

            if item["date"]:
                lines.append(
                    f"📅 {item['date']}"
                )

            if item["closing_date"]:
                lines.append(
                    f"⏰ Closing: {item['closing_date']}"
                )

            if item["location"]:
                lines.append(
                    f"📍 {item['location']}"
                )

            if item["description"]:
                lines.append(
                    item["description"]
                )

            if item["url"]:
                lines.append(
                    f"🔗 {item['url']}"
                )

            lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )
        lines.append("")

    lines.append(
        "💡 Don't leave it until the deadline. "
        "Check the opportunity details carefully "
        "before applying."
    )

    return "\n".join(lines)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🔎 Bulletin filters")

    selected_category = st.selectbox(
        "Opportunity type",
        [
            "All opportunities",
            "🎓 Apprenticeship",
            "🏫 University Open Days",
            "💼 Work Experience",
            "🌟 Other Opportunity",
            "📚 Resource"
        ]
    )

    selected_subject = st.selectbox(
        "Subject / career area",
        CAREER_AREAS
    )

    selected_year = st.selectbox(
        "Year group",
        YEAR_GROUPS
    )

    selected_location = st.selectbox(
        "Location",
        LOCATIONS
    )

    st.divider()

    st.subheader("🔄 Refresh")

    if st.button(
        "Find latest opportunities",
        use_container_width=True
    ):

        with st.spinner(
            "Searching progression sources..."
        ):

            all_items = []

            # Apprenticeships
            all_items.extend(
                search_adzuna_apprenticeships(
                    subject=selected_subject,
                    location=selected_location
                )
            )

            # UCAS
            all_items.extend(
                get_ucas_opportunities()
            )

            # Amazing Apprenticeships
            all_items.extend(
                get_amazing_apprenticeships()
            )

            # Work experience
            all_items.extend(
                get_work_experience()
            )

            # Resources
            all_items.extend(
                get_resources()
            )

            st.session_state.opportunities = (
                remove_duplicates(all_items)
            )

            st.session_state.last_refresh = (
                datetime.now().strftime(
                    "%d %B %Y %H:%M"
                )
            )

        st.success("Progression sources refreshed.")


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="hero">

    <h1>🎓 KS5 Progression Hub</h1>

    <p>
    Your weekly source of apprenticeships,
    university open days, work experience,
    progression opportunities and useful resources.
    </p>

    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FIRST LOAD
# ============================================================

if not st.session_state.opportunities:

    st.info(
        "👈 Choose your filters and click "
        "**Find latest opportunities** to build "
        "this week's progression bulletin."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🎓 Apprenticeships",
            "Live"
        )

    with col2:
        st.metric(
            "🏫 Open Days",
            "UCAS"
        )

    with col3:
        st.metric(
            "💼 Work Experience",
            "Opportunities"
        )

else:

    # ========================================================
    # FILTER CURRENT RESULTS
    # ========================================================

    filtered = filter_opportunities(
        st.session_state.opportunities,
        selected_category,
        selected_subject,
        selected_year,
        selected_location
    )

    # ========================================================
    # DASHBOARD METRICS
    # ========================================================

    apprenticeships = sum(
        1 for x in filtered
        if x["category"] == "🎓 Apprenticeship"
    )

    open_days = sum(
        1 for x in filtered
        if x["category"] == "🏫 University Open Days"
    )

    work_experience = sum(
        1 for x in filtered
        if x["category"] == "💼 Work Experience"
    )

    resources = sum(
        1 for x in filtered
        if x["category"] == "📚 Resource"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "🎓 Apprenticeships",
            apprenticeships
        )

    with col2:
        st.metric(
            "🏫 Open Days",
            open_days
        )

    with col3:
        st.metric(
            "💼 Work Experience",
            work_experience
        )

    with col4:
        st.metric(
            "📚 Resources",
            resources
        )

    if st.session_state.last_refresh:

        st.caption(
            f"Last refreshed: "
            f"{st.session_state.last_refresh}"
        )

    # ========================================================
    # TABS
    # ========================================================

    tab1, tab2, tab3 = st.tabs(
        [
            "🔎 Opportunities",
            "📢 Teams Bulletin",
            "✍️ Add Opportunity"
        ]
    )

    # ========================================================
    # OPPORTUNITIES
    # ========================================================

    with tab1:

        st.subheader(
            f"{len(filtered)} progression items"
        )

        if not filtered:

            st.warning(
                "No opportunities match these filters. "
                "Try broadening your search."
            )

        else:

            for index, item in enumerate(filtered):

                display_opportunity(
                    item,
                    index
                )

    # ========================================================
    # TEAMS BULLETIN
    # ========================================================

    with tab2:

        st.subheader(
            "📢 Microsoft Teams Bulletin"
        )

        bulletin = create_bulletin(
            filtered
        )

        st.markdown(
            "Copy the bulletin below directly into "
            "Microsoft Teams."
        )

        st.text_area(
            "Teams-ready bulletin",
            bulletin,
            height=650
        )

        st.download_button(
            "📥 Download bulletin",
            bulletin,
            file_name=(
                f"KS5_Progression_Bulletin_"
                f"{TODAY.strftime('%Y-%m-%d')}.txt"
            ),
            mime="text/plain"
        )

    # ========================================================
    # ADD OWN OPPORTUNITY
    # ========================================================

    with tab3:

        st.subheader(
            "✍️ Add your own opportunity"
        )

        with st.form(
            "custom_opportunity"
        ):

            custom_title = st.text_input(
                "Opportunity title"
            )

            custom_org = st.text_input(
                "Organisation"
            )

            custom_category = st.selectbox(
                "Category",
                [
                    "🎓 Apprenticeship",
                    "🏫 University Open Days",
                    "💼 Work Experience",
                    "🌟 Other Opportunity",
                    "📚 Resource"
                ]
            )

            custom_description = st.text_area(
                "Description"
            )

            custom_date = st.text_input(
                "Date / availability"
            )

            custom_deadline = st.text_input(
                "Closing date"
            )

            custom_location = st.text_input(
                "Location"
            )

            custom_url = st.text_input(
                "Link"
            )

            submitted = st.form_submit_button(
                "➕ Add to bulletin"
            )

            if submitted:

                if not custom_title:

                    st.error(
                        "Please enter an opportunity title."
                    )

                else:

                    new_item = make_opportunity(
                        title=custom_title,
                        organisation=custom_org,
                        category=custom_category,
                        description=custom_description,
                        location=custom_location,
                        date_text=custom_date,
                        closing_date=custom_deadline,
                        url=custom_url,
                        source="College added",
                        year_group="All KS5",
                        subject="All subjects",
                        verified=False
                    )

                    st.session_state.opportunities.append(
                        new_item
                    )

                    st.success(
                        "Opportunity added to the bulletin."
                    )

                    st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🎓 KS5 Progression Hub • "
    "Designed for sixth-form progression teams • "
    "Always check the original source before applying."
)
