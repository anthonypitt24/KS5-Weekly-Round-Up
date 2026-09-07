# ============================================================
# KS5 PROGRESSION HUB
# Weekly progression intelligence for sixth-form students
#
# Designed for:
# - Weekly Microsoft Teams bulletin
# - North West university open days
# - Degree / Higher Apprenticeships
# - Live progression opportunities
# - College-created activities and events
# - One practical weekly student action
#
# No Government Apprenticeship API key required.
# ============================================================

import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import re
import html
import hashlib
import json
import os
from urllib.parse import quote, urljoin, urlparse


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="KS5 Progression Hub",
    page_icon="🎓",
    layout="wide",
)


# ============================================================
# CONSTANTS
# ============================================================

TODAY = date.today()

DATA_FILE = "ks5_progression_custom.json"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/139 Safari/537.36"
    )
}


# ============================================================
# NORTH WEST UNIVERSITY WATCHLIST
# ============================================================

NORTH_WEST_UNIVERSITIES = {
    "University of Liverpool": {
        "city": "Liverpool",
        "domain": "liverpool.ac.uk",
    },
    "Liverpool John Moores University": {
        "city": "Liverpool",
        "domain": "ljmu.ac.uk",
    },
    "Liverpool Hope University": {
        "city": "Liverpool",
        "domain": "hope.ac.uk",
    },
    "Edge Hill University": {
        "city": "Ormskirk",
        "domain": "edgehill.ac.uk",
    },
    "University of Chester": {
        "city": "Chester",
        "domain": "chester.ac.uk",
    },
    "University of Manchester": {
        "city": "Manchester",
        "domain": "manchester.ac.uk",
    },
    "Manchester Metropolitan University": {
        "city": "Manchester",
        "domain": "mmu.ac.uk",
    },
    "University of Salford": {
        "city": "Salford",
        "domain": "salford.ac.uk",
    },
    "University of Bolton": {
        "city": "Bolton",
        "domain": "bolton.ac.uk",
    },
    "University of Central Lancashire": {
        "city": "Preston",
        "domain": "uclan.ac.uk",
    },
    "Lancaster University": {
        "city": "Lancaster",
        "domain": "lancaster.ac.uk",
    },
    "University of Cumbria": {
        "city": "Carlisle",
        "domain": "cumbria.ac.uk",
    },
    "Liverpool Institute for Performing Arts": {
        "city": "Liverpool",
        "domain": "lipa.ac.uk",
    },
}


# ============================================================
# CAREER KEYWORDS
# ============================================================

CAREER_KEYWORDS = {
    "All categories": [],

    "Digital & Technology": [
        "digital",
        "software",
        "computing",
        "computer",
        "cyber",
        "technology",
        "data",
        "artificial intelligence",
        "ai",
        "programming",
        "developer",
        "it",
    ],

    "Engineering": [
        "engineering",
        "engineer",
        "mechanical",
        "electrical",
        "civil",
        "aerospace",
        "manufacturing",
        "automotive",
        "design engineer",
    ],

    "Business & Administration": [
        "business",
        "management",
        "administration",
        "operations",
        "project management",
        "marketing",
        "human resources",
        "hr",
    ],

    "Finance & Legal": [
        "finance",
        "accounting",
        "accountancy",
        "banking",
        "economics",
        "tax",
        "audit",
        "legal",
        "law",
    ],

    "Health & Science": [
        "health",
        "healthcare",
        "nursing",
        "science",
        "laboratory",
        "pharmacy",
        "medicine",
        "clinical",
        "biomedical",
    ],

    "Creative & Media": [
        "creative",
        "media",
        "film",
        "television",
        "design",
        "graphic",
        "journalism",
        "music",
        "performing arts",
        "advertising",
    ],

    "Construction": [
        "construction",
        "quantity surveying",
        "building",
        "property",
        "architecture",
        "surveying",
    ],

    "Education": [
        "education",
        "teaching",
        "teacher",
        "early years",
        "childcare",
    ],
}


# ============================================================
# WEEKLY ACTIONS
# ============================================================

WEEKLY_ACTIONS = [
    {
        "title": "🔎 Career Research",
        "text": (
            "Choose one career you're considering and spend 20 minutes "
            "finding out what qualifications, skills and routes are needed."
        ),
        "target": "Write down 3 things you have learned.",
    },
    {
        "title": "📄 Build Your CV",
        "text": (
            "Create your first CV or improve your existing one. "
            "Include your education, experience, achievements and skills."
        ),
        "target": "Finish one section of your CV.",
    },
    {
        "title": "🎓 Compare University Courses",
        "text": (
            "Choose one subject you might study and compare three "
            "university courses. Look at entry requirements and modules."
        ),
        "target": "Write down your favourite course and why.",
    },
    {
        "title": "🎓 Explore Degree Apprenticeships",
        "text": (
            "Find three degree apprenticeship routes linked to careers "
            "you are interested in."
        ),
        "target": "Save three opportunities and check their entry requirements.",
    },
    {
        "title": "💼 Find Work Experience",
        "text": (
            "Search for one work-experience, volunteering or employer "
            "opportunity connected to an area you might pursue."
        ),
        "target": "Identify one opportunity you could apply for.",
    },
    {
        "title": "🧠 Skills Audit",
        "text": (
            "Think about the career or course you want. Identify the "
            "skills employers or universities are looking for."
        ),
        "target": "Choose one skill you can develop this term.",
    },
    {
        "title": "✍️ Personal Statement",
        "text": (
            "Write 100–150 words explaining why you are interested in "
            "your chosen subject or career."
        ),
        "target": "Save your first draft.",
    },
    {
        "title": "🏫 Book an Open Day",
        "text": (
            "Find an upcoming university open day and investigate whether "
            "it is worth attending."
        ),
        "target": "Book one open day or add it to your calendar.",
    },
    {
        "title": "🏢 Research Employers",
        "text": (
            "Choose three employers you might like to work for and "
            "investigate their graduate or apprenticeship routes."
        ),
        "target": "Save three employer websites.",
    },
    {
        "title": "🎤 Interview Practice",
        "text": (
            "Practise answering five common interview questions, "
            "using examples from school, college, work or your interests."
        ),
        "target": "Record or write your strongest answer.",
    },
    {
        "title": "🌐 Improve Your Profile",
        "text": (
            "Review your online professional profile or create one. "
            "Make sure your skills, interests and achievements are clear."
        ),
        "target": "Add one achievement or skill.",
    },
    {
        "title": "📚 Super-Curricular Learning",
        "text": (
            "Spend 30 minutes learning something beyond your normal "
            "lessons in a subject you might study."
        ),
        "target": "Record what you learned and one question it raised.",
    },
]


# ============================================================
# SESSION STATE
# ============================================================

if "items" not in st.session_state:
    st.session_state.items = []

if "custom_items" not in st.session_state:
    st.session_state.custom_items = []

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = ""

if "source_status" not in st.session_state:
    st.session_state.source_status = {}

if "removed" not in st.session_state:
    st.session_state.removed = set()


# ============================================================
# CUSTOM DATA STORAGE
# ============================================================

def load_custom_items():
    """Load college-created activities/events from JSON."""

    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def save_custom_items(items):
    """Save college-created activities/events."""

    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                items,
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception:
        pass


if not st.session_state.custom_items:
    st.session_state.custom_items = load_custom_items()


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

.hero {
    padding: 2rem;
    border-radius: 18px;
    margin-bottom: 1.5rem;
    background: linear-gradient(
        135deg,
        #172554,
        #1e3a8a
    );
    color: white;
}

.hero h1 {
    font-size: 2.5rem;
    margin-bottom: 0.3rem;
}

.hero p {
    font-size: 1.1rem;
    opacity: 0.92;
}

.feature-card {
    padding: 1.25rem;
    border-radius: 15px;
    border: 1px solid #e5e7eb;
    margin-bottom: 0.8rem;
    background: white;
}

.action-card {
    padding: 1.5rem;
    border-radius: 18px;
    border: 2px solid #dbeafe;
    background: #eff6ff;
    margin-bottom: 1rem;
}

.small-muted {
    color: #6b7280;
    font-size: 0.85rem;
}

.badge {
    display: inline-block;
    padding: 0.25rem 0.55rem;
    margin-right: 0.3rem;
    margin-bottom: 0.4rem;
    border-radius: 999px;
    font-size: 0.78rem;
    background: #e0e7ff;
}

.badge-red {
    background: #fee2e2;
}

.badge-orange {
    background: #ffedd5;
}

.badge-green {
    background: #dcfce7;
}

.badge-blue {
    background: #dbeafe;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    value = BeautifulSoup(
        str(value),
        "html.parser",
    ).get_text(" ", strip=True)

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def safe_get(url, timeout=15):
    try:
        response = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=timeout,
        )

        if response.status_code == 200:
            return response.text

    except Exception:
        pass

    return ""


def make_id(*parts):
    raw = "|".join(
        str(x)
        for x in parts
    )

    return hashlib.md5(
        raw.encode("utf-8")
    ).hexdigest()[:12]


def parse_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    value = str(value).strip()

    patterns = [
        "%d %B %Y",
        "%d %b %Y",
        "%A %d %B %Y",
        "%a %d %b %Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d %B",
        "%d %b",
    ]

    for pattern in patterns:
        try:
            parsed = datetime.strptime(
                value,
                pattern,
            ).date()

            if "%Y" not in pattern:
                parsed = parsed.replace(
                    year=TODAY.year
                )

            return parsed

        except Exception:
            continue

    return None


def format_date(value):
    parsed = parse_date(value)

    if not parsed:
        return str(value)

    return parsed.strftime(
        "%d %b %Y"
    )


def days_until(value):
    parsed = parse_date(value)

    if not parsed:
        return None

    return (parsed - TODAY).days


def category_items(items, category):
    return [
        item
        for item in items
        if item.get("category") == category
    ]


def get_week_number():
    return TODAY.isocalendar().week


def weekly_action():
    index = (
        get_week_number()
        - 1
    ) % len(WEEKLY_ACTIONS)

    return WEEKLY_ACTIONS[index]


def truncate(text, length=170):
    text = clean_text(text)

    if len(text) <= length:
        return text

    return text[:length].rsplit(
        " ",
        1,
    )[0] + "..."


# ============================================================
# ITEM CREATION
# ============================================================

def make_item(
    title,
    organisation="",
    category="",
    description="",
    event_date="",
    closing_date="",
    location="",
    url="",
    source="",
    tags=None,
    priority=0,
    verified=False,
    published_date="",
    level="",
    salary="",
    featured=False,
):

    if tags is None:
        tags = []

    return {
        "id": make_id(
            title,
            organisation,
            event_date,
            url,
        ),
        "title": clean_text(title),
        "organisation": clean_text(
            organisation
        ),
        "category": category,
        "description": clean_text(
            description
        ),
        "event_date": clean_text(
            event_date
        ),
        "closing_date": clean_text(
            closing_date
        ),
        "location": clean_text(
            location
        ),
        "url": url,
        "source": source,
        "tags": tags,
        "priority": priority,
        "verified": verified,
        "published_date": published_date,
        "level": level,
        "salary": salary,
        "featured": featured,
    }


# ============================================================
# DATE EXTRACTION
# ============================================================

MONTHS = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December"
)

DATE_PATTERN = re.compile(
    rf"\b("
    rf"\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}}"
    rf"|"
    rf"\d{{1,2}}\s+(?:{MONTHS})"
    rf"|"
    rf"(?:{MONTHS})\s+\d{{1,2}},\s+\d{{4}}"
    rf")\b",
    re.IGNORECASE,
)


def extract_dates(text):
    if not text:
        return []

    found = DATE_PATTERN.findall(
        text
    )

    results = []

    for value in found:
        parsed = parse_date(value)

        if parsed:
            results.append(
                (
                    value,
                    parsed,
                )
            )

    return results


def nearest_future_date(text):
    candidates = extract_dates(text)

    future = [
        x
        for x in candidates
        if x[1] >= TODAY
    ]

    if not future:
        return None

    future.sort(
        key=lambda x: x[1]
    )

    return future[0]


# ============================================================
# DUCKDUCKGO SEARCH
# ============================================================

def web_search(
    query,
    max_results=8,
):
    """
    Uses DuckDuckGo's HTML results.

    This deliberately avoids requiring an API key.
    """

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    html_text = safe_get(
        url,
        timeout=20,
    )

    if not html_text:
        return []

    soup = BeautifulSoup(
        html_text,
        "html.parser",
    )

    results = []

    for result in soup.select(
        ".result"
    ):

        link = result.select_one(
            ".result__a"
        )

        snippet = result.select_one(
            ".result__snippet"
        )

        if not link:
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        href = link.get(
            "href",
            "",
        )

        description = ""

        if snippet:
            description = clean_text(
                snippet.get_text(
                    " ",
                    strip=True,
                )
            )

        results.append(
            {
                "title": title,
                "url": href,
                "description": description,
            }
        )

        if len(results) >= max_results:
            break

    return results


# ============================================================
# UNIVERSITY OPEN DAYS
# ============================================================

def search_university_open_days(
    months_ahead=3
):
    items = []
    statuses = {}

    cutoff = TODAY + timedelta(
        days=months_ahead * 30
    )

    for university, details in NORTH_WEST_UNIVERSITIES.items():

        domain = details["domain"]
        city = details["city"]

        query = (
            f'site:{domain} '
            f'("open day" OR "open days") '
            f'2026 OR 2027'
        )

        results = web_search(
            query,
            max_results=5,
        )

        found = 0

        for result in results:

            combined = (
                result["title"]
                + " "
                + result["description"]
            )

            if "open day" not in combined.lower():
                continue

            future = nearest_future_date(
                combined
            )

            if not future:
                continue

            raw_date, event_date = future

            if event_date > cutoff:
                continue

            days = (
                event_date - TODAY
            ).days

            if days <= 7:
                tags = [
                    "🔥 This week",
                    "📍 North West",
                ]
                priority = 900
            elif days <= 14:
                tags = [
                    "📅 Coming up",
                    "📍 North West",
                ]
                priority = 700
            else:
                tags = [
                    "📍 North West",
                ]
                priority = 450

            items.append(
                make_item(
                    title=(
                        f"{university} — "
                        f"Open Day"
                    ),
                    organisation=university,
                    category=(
                        "🏫 University Open Day"
                    ),
                    description=(
                        "University open day. "
                        "Check the university page "
                        "for booking and course-specific "
                        "information."
                    ),
                    event_date=format_date(
                        event_date
                    ),
                    location=city,
                    url=result["url"],
                    source=(
                        f"{university} official website"
                    ),
                    tags=tags,
                    priority=priority,
                    verified=False,
                )
            )

            found += 1

        statuses[
            university
        ] = (
            f"{found} event(s) found"
            if found
            else "No dated event found"
        )

    return items, statuses


# ============================================================
# DEGREE / HIGHER APPRENTICESHIPS
# ============================================================

DEGREE_APPRENTICESHIP_QUERIES = [
    (
        '"degree apprenticeship" '
        '"Liverpool" 2026 OR 2027'
    ),
    (
        '"degree apprenticeship" '
        '"Manchester" 2026 OR 2027'
    ),
    (
        '"degree apprenticeship" '
        '"North West" 2026 OR 2027'
    ),
    (
        '"higher apprenticeship" '
        '"North West" 2026 OR 2027'
    ),
    (
        '"level 6 apprenticeship" '
        '"Liverpool"'
    ),
    (
        '"level 6 apprenticeship" '
        '"Manchester"'
    ),
    (
        '"level 7 apprenticeship" '
        '"North West"'
    ),
]


def is_degree_apprenticeship(text):
    text = text.lower()

    terms = [
        "degree apprenticeship",
        "degree apprenticeships",
        "level 6 apprenticeship",
        "level 7 apprenticeship",
        "higher apprenticeship",
        "higher apprenticeships",
        "chartered apprenticeship",
    ]

    return any(
        term in text
        for term in terms
    )


def infer_level(text):
    lower = text.lower()

    if (
        "level 7" in lower
        or "degree apprenticeship" in lower
    ):
        return "Level 6/7"

    if "level 6" in lower:
        return "Level 6"

    if "higher apprenticeship" in lower:
        return "Higher Apprenticeship"

    return "Higher / Degree"


def infer_location(text):
    lower = text.lower()

    places = [
        "Liverpool",
        "Manchester",
        "Chester",
        "Preston",
        "Lancaster",
        "Salford",
        "Bolton",
        "Carlisle",
        "Blackburn",
        "Warrington",
        "Wirral",
    ]

    for place in places:
        if place.lower() in lower:
            return place

    return "North West / UK"


def search_degree_apprenticeships(
    selected_career="All categories"
):
    items = []
    seen = set()

    queries = list(
        DEGREE_APPRENTICESHIP_QUERIES
    )

    keywords = CAREER_KEYWORDS.get(
        selected_career,
        [],
    )

    if keywords:
        queries.extend(
            [
                (
                    f'"degree apprenticeship" '
                    f'"{keyword}" '
                    f'"North West"'
                )
                for keyword in keywords[:4]
            ]
        )

    for query in queries:

        results = web_search(
            query,
            max_results=8,
        )

        for result in results:

            title = result["title"]
            description = result[
                "description"
            ]
            url = result["url"]

            combined = (
                title
                + " "
                + description
            )

            if not is_degree_apprenticeship(
                combined
            ):
                continue

            key = url or title

            if key in seen:
                continue

            seen.add(key)

            future = nearest_future_date(
                combined
            )

            closing_date = ""

            if future:
                closing_date = format_date(
                    future[1]
                )

            location = infer_location(
                combined
            )

            days = days_until(
                closing_date
            )

            if days is not None:
                if days <= 3:
                    priority = 1000
                    tags = [
                        "🔴 Closing soon",
                        "🎓 Degree apprenticeship",
                    ]
                elif days <= 7:
                    priority = 950
                    tags = [
                        "🔥 This week",
                        "🎓 Degree apprenticeship",
                    ]
                else:
                    priority = 800
                    tags = [
                        "🎓 Degree apprenticeship",
                    ]
            else:
                priority = 650
                tags = [
                    "🎓 Degree apprenticeship",
                ]

            if (
                location
                not in [
                    "North West / UK",
                    "UK",
                ]
            ):
                tags.append(
                    "📍 North West"
                )

            items.append(
                make_item(
                    title=title,
                    organisation=(
                        urlparse(url).netloc
                        if url
                        else ""
                    ),
                    category=(
                        "🎓 Degree Apprenticeship"
                    ),
                    description=truncate(
                        description,
                        240,
                    ),
                    closing_date=closing_date,
                    location=location,
                    url=url,
                    source="Web search",
                    tags=tags,
                    priority=priority,
                    verified=False,
                    level=infer_level(
                        combined
                    ),
                )
            )

    return items


# ============================================================
# GENERAL APPRENTICESHIPS
# ============================================================

def search_general_apprenticeships(
    selected_career="All categories"
):

    queries = [
        '"apprenticeship vacancy" Liverpool 2026',
        '"apprenticeship vacancy" Manchester 2026',
        '"apprenticeships" "North West" 2026',
    ]

    keywords = CAREER_KEYWORDS.get(
        selected_career,
        [],
    )

    if keywords:
        queries.extend(
            [
                (
                    f'apprenticeship vacancy '
                    f'"{keyword}" '
                    f'Liverpool Manchester 2026'
                )
                for keyword in keywords[:3]
            ]
        )

    items = []
    seen = set()

    for query in queries:

        results = web_search(
            query,
            max_results=6,
        )

        for result in results:

            title = result["title"]
            description = result[
                "description"
            ]
            url = result["url"]

            combined = (
                title
                + " "
                + description
            )

            lower = combined.lower()

            if (
                "apprenticeship"
                not in lower
            ):
                continue

            if is_degree_apprenticeship(
                combined
            ):
                continue

            key = url or title

            if key in seen:
                continue

            seen.add(key)

            future = nearest_future_date(
                combined
            )

            closing_date = ""

            if future:
                closing_date = format_date(
                    future[1]
                )

            days = days_until(
                closing_date
            )

            priority = 350

            if days is not None:
                if days <= 3:
                    priority = 850
                elif days <= 7:
                    priority = 750

            items.append(
                make_item(
                    title=title,
                    organisation=(
                        urlparse(url).netloc
                        if url
                        else ""
                    ),
                    category="🎓 Apprenticeship",
                    description=truncate(
                        description,
                        220,
                    ),
                    closing_date=closing_date,
                    location=infer_location(
                        combined
                    ),
                    url=url,
                    source="Web search",
                    tags=[
                        "🎓 Apprenticeship"
                    ],
                    priority=priority,
                    verified=False,
                )
            )

    return items


# ============================================================
# UCAS DEADLINES
# ============================================================

def get_ucas_deadlines():

    return [
        make_item(
            title=(
                "UCAS application deadline — "
                "check the official timetable"
            ),
            organisation="UCAS",
            category="📅 Key Date",
            description=(
                "Check the official UCAS application "
                "deadline timetable for the course "
                "and application cycle you are using."
            ),
            url="https://www.ucas.com/",
            source="UCAS",
            tags=[
                "📅 Key date"
            ],
            priority=500,
            verified=True,
        )
    ]


# ============================================================
# COLLEGE ACTIVITIES
# ============================================================

def custom_activity_items():
    return [
        item
        for item in st.session_state.custom_items
        if item.get("id")
        not in st.session_state.removed
    ]


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_items(items):

    result = []
    seen = set()

    for item in items:

        key = (
            item.get("title", "").lower(),
            item.get("organisation", "").lower(),
            item.get("event_date", "").lower(),
            item.get("url", "").lower(),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


# ============================================================
# FILTERING
# ============================================================

def career_matches(
    item,
    selected_career
):

    if selected_career == "All categories":
        return True

    keywords = CAREER_KEYWORDS.get(
        selected_career,
        [],
    )

    searchable = " ".join(
        [
            item.get("title", ""),
            item.get("description", ""),
            item.get("organisation", ""),
        ]
    ).lower()

    return any(
        keyword.lower()
        in searchable
        for keyword in keywords
    )


# ============================================================
# REFRESH ALL DATA
# ============================================================

def refresh_all(
    selected_career,
    months_ahead,
):

    all_items = []

    statuses = {}

    # --------------------------------------------------------
    # UNIVERSITY OPEN DAYS
    # --------------------------------------------------------

    open_days, university_status = (
        search_university_open_days(
            months_ahead
        )
    )

    all_items.extend(
        open_days
    )

    statuses[
        "North West universities"
    ] = university_status

    # --------------------------------------------------------
    # DEGREE APPRENTICESHIPS
    # --------------------------------------------------------

    degree_apps = (
        search_degree_apprenticeships(
            selected_career
        )
    )

    all_items.extend(
        degree_apps
    )

    statuses[
        "Degree apprenticeships"
    ] = (
        f"{len(degree_apps)} results"
    )

    # --------------------------------------------------------
    # GENERAL APPRENTICESHIPS
    # --------------------------------------------------------

    apprenticeships = (
        search_general_apprenticeships(
            selected_career
        )
    )

    all_items.extend(
        apprenticeships
    )

    statuses[
        "General apprenticeships"
    ] = (
        f"{len(apprenticeships)} results"
    )

    # --------------------------------------------------------
    # KEY DATES
    # --------------------------------------------------------

    all_items.extend(
        get_ucas_deadlines()
    )

    # --------------------------------------------------------
    # COLLEGE ACTIVITIES
    # --------------------------------------------------------

    all_items.extend(
        custom_activity_items()
    )

    # --------------------------------------------------------
    # FILTER CAREER
    # --------------------------------------------------------

    if (
        selected_career
        != "All categories"
    ):
        filtered = []

        for item in all_items:

            if (
                item.get("category")
                == "🏫 University Open Day"
            ):
                filtered.append(item)

            elif (
                item.get("category")
                == "📅 Key Date"
            ):
                filtered.append(item)

            elif career_matches(
                item,
                selected_career,
            ):
                filtered.append(item)

            elif item.get(
                "source"
            ) == "College added":
                filtered.append(item)

        all_items = filtered

    all_items = deduplicate_items(
        all_items
    )

    # --------------------------------------------------------
    # REMOVE DELETED ITEMS
    # --------------------------------------------------------

    all_items = [
        item
        for item in all_items
        if item.get("id")
        not in st.session_state.removed
    ]

    return all_items, statuses


# ============================================================
# RANKING
# ============================================================

def ranking_score(item):

    score = int(
        item.get(
            "priority",
            0,
        )
    )

    tags = item.get(
        "tags",
        [],
    )

    category = item.get(
        "category",
        "",
    )

    if "🔴 Closing soon" in tags:
        score += 500

    if "🔥 This week" in tags:
        score += 350

    if (
        "📍 North West"
        in tags
    ):
        score += 250

    if (
        category
        == "🎓 Degree Apprenticeship"
    ):
        score += 300

    if item.get(
        "featured",
        False,
    ):
        score += 450

    if item.get(
        "source"
    ) == "College added":
        score += 400

    # Date urgency

    closing = days_until(
        item.get(
            "closing_date",
            "",
        )
    )

    event = days_until(
        item.get(
            "event_date",
            "",
        )
    )

    if closing is not None:
        if closing <= 3:
            score += 600
        elif closing <= 7:
            score += 400
        elif closing <= 14:
            score += 150

    if event is not None:
        if event <= 7:
            score += 450
        elif event <= 14:
            score += 200

    return score


def get_priorities(items):

    ranked = sorted(
        items,
        key=ranking_score,
        reverse=True,
    )

    return ranked


# ============================================================
# SHORT WEEKLY SELECTION
# ============================================================

def weekly_highlights(items):

    ranked = get_priorities(
        items
    )

    selected = []

    # --------------------------------------------------------
    # 1. URGENT / CLOSING
    # --------------------------------------------------------

    urgent = [
        item
        for item in ranked
        if (
            days_until(
                item.get(
                    "closing_date",
                    "",
                )
            )
            is not None
            and days_until(
                item.get(
                    "closing_date",
                    "",
                )
            )
            <= 7
        )
    ]

    for item in urgent:
        if item not in selected:
            selected.append(item)

        if len(selected) >= 2:
            break

    # --------------------------------------------------------
    # 2. NORTH WEST OPEN DAY
    # --------------------------------------------------------

    open_days = [
        item
        for item in ranked
        if item.get(
            "category"
        ) == "🏫 University Open Day"
    ]

    for item in open_days:

        event_days = days_until(
            item.get(
                "event_date",
                "",
            )
        )

        if (
            event_days is not None
            and event_days <= 30
            and item not in selected
        ):
            selected.append(item)
            break

    # --------------------------------------------------------
    # 3. DEGREE APPRENTICESHIP
    # --------------------------------------------------------

    degree_apps = [
        item
        for item in ranked
        if item.get(
            "category"
        ) == "🎓 Degree Apprenticeship"
    ]

    for item in degree_apps:

        if item not in selected:
            selected.append(item)
            break

    # --------------------------------------------------------
    # 4. COLLEGE ACTIVITY
    # --------------------------------------------------------

    college = [
        item
        for item in ranked
        if item.get(
            "source"
        ) == "College added"
        and item not in selected
    ]

    if college:
        selected.append(
            college[0]
        )

    # --------------------------------------------------------
    # 5. FILL ONLY IF NECESSARY
    # --------------------------------------------------------

    for item in ranked:

        if item in selected:
            continue

        selected.append(item)

        if len(selected) >= 5:
            break

    return selected[:5]


# ============================================================
# DISPLAY CARD
# ============================================================

def display_card(
    item,
    key_suffix,
    removable=True,
):

    title = item.get(
        "title",
        "Untitled",
    )

    organisation = item.get(
        "organisation",
        "",
    )

    description = item.get(
        "description",
        "",
    )

    badges = ""

    for tag in item.get(
        "tags",
        [],
    )[:5]:

        if (
            "🔴" in tag
            or "Closing" in tag
        ):
            css = "badge badge-red"

        elif (
            "🔥" in tag
            or "Soon" in tag
        ):
            css = "badge badge-orange"

        elif "🆕" in tag:
            css = "badge badge-green"

        else:
            css = "badge badge-blue"

        badges += (
            f'<span class="{css}">'
            f'{html.escape(tag)}'
            f'</span>'
        )

    st.markdown(
        f"""
        <div class="feature-card">

        {badges}

        <h3>
        {html.escape(title)}
        </h3>

        <p>
        <strong>
        {html.escape(organisation)}
        </strong>
        </p>

        <p>
        {html.escape(
            truncate(description, 300)
        )}
        </p>

        <p>
        📍 {html.escape(
            item.get("location", "")
        )}
        </p>

        <p>
        📅 {html.escape(
            item.get("event_date", "")
        )}
        </p>

        <p>
        ⏰ {html.escape(
            item.get("closing_date", "")
        )}
        </p>

        <p class="small-muted">
        Source: {html.escape(
            item.get("source", "")
        )}
        </p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(
        [3, 1]
    )

    with c1:

        if item.get("url"):

            st.link_button(
                "🔗 View opportunity",
                item["url"],
            )

    with c2:

        if removable:

            if st.button(
                "🗑️ Remove",
                key=(
                    "remove_"
                    + str(
                        item.get(
                            "id",
                            "",
                        )
                    )
                    + "_"
                    + key_suffix
                ),
            ):

                st.session_state.removed.add(
                    item.get("id")
                )

                st.session_state.items = [
                    x
                    for x
                    in st.session_state.items
                    if x.get("id")
                    != item.get("id")
                ]

                st.rerun()


# ============================================================
# WEEKLY ACTION DISPLAY
# ============================================================

def display_weekly_action():

    action = weekly_action()

    st.markdown(
        f"""
        <div class="action-card">

        <div class="small-muted">
        💡 YOUR ACTION THIS WEEK
        </div>

        <h2>
        {html.escape(action["title"])}
        </h2>

        <p>
        {html.escape(action["text"])}
        </p>

        <strong>
        ✅ {html.escape(action["target"])}
        </strong>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# TEAMS BULLETIN
#
# VERY IMPORTANT:
# This intentionally contains only a SMALL number of items.
# ============================================================

def build_bulletin(items):

    highlights = weekly_highlights(
        items
    )

    action = weekly_action()

    lines = []

    lines.append(
        "🎓 KS5 PROGRESSION — THIS WEEK"
    )

    lines.append(
        f"Week commencing "
        f"{TODAY.strftime('%d %B %Y')}"
    )

    lines.append("")

    # --------------------------------------------------------
    # WEEKLY ACTION
    # --------------------------------------------------------

    lines.append(
        "💡 YOUR ACTION THIS WEEK"
    )

    lines.append(
        action["title"]
    )

    lines.append(
        action["text"]
    )

    lines.append(
        f"✅ {action['target']}"
    )

    lines.append("")

    # --------------------------------------------------------
    # DON'T MISS
    # --------------------------------------------------------

    if highlights:

        lines.append(
            "🔥 DON'T MISS"
        )

        lines.append("")

        for item in highlights:

            title = item.get(
                "title",
                "Opportunity",
            )

            lines.append(
                f"• {title}"
            )

            if item.get(
                "organisation"
            ):
                lines.append(
                    f"  {item['organisation']}"
                )

            if item.get(
                "event_date"
            ):
                lines.append(
                    f"  📅 {item['event_date']}"
                )

            if item.get(
                "closing_date"
            ):
                lines.append(
                    f"  ⏰ Closes "
                    f"{item['closing_date']}"
                )

            if item.get(
                "location"
            ):
                lines.append(
                    f"  📍 {item['location']}"
                )

            if item.get(
                "url"
            ):
                lines.append(
                    f"  🔗 {item['url']}"
                )

            lines.append("")

    # --------------------------------------------------------
    # KEEP THIS SHORT
    # --------------------------------------------------------

    lines.append(
        "📚 Want more?"
    )

    lines.append(
        "Open the KS5 Progression Hub "
        "to explore all current opportunities."
    )

    return "\n".join(
        lines
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "🎛️ Bulletin Controls"
    )

    selected_career = st.selectbox(
        "Career area",
        list(
            CAREER_KEYWORDS.keys()
        ),
    )

    months_ahead = st.slider(
        "University look-ahead",
        min_value=1,
        max_value=6,
        value=2,
    )

    st.divider()

    if st.button(
        "🚀 BUILD THIS WEEK'S BULLETIN",
        type="primary",
        use_container_width=True,
    ):

        with st.spinner(
            "Checking universities, apprenticeships and opportunities..."
        ):

            new_items, statuses = (
                refresh_all(
                    selected_career,
                    months_ahead,
                )
            )

            st.session_state.items = (
                new_items
            )

            st.session_state.source_status = (
                statuses
            )

            st.session_state.last_refresh = (
                datetime.now().strftime(
                    "%d %B %Y at %H:%M"
                )
            )

        st.success(
            "Weekly bulletin built."
        )

        st.rerun()


# ============================================================
# HERO
# ============================================================

st.markdown(
    f"""
    <div class="hero">

    <h1>
    🎓 KS5 Progression Hub
    </h1>

    <p>
    What do students actually need to know
    this week?
    </p>

    <p>
    📍 North West universities
    &nbsp; • &nbsp;
    🎓 Degree apprenticeships
    &nbsp; • &nbsp;
    💼 Opportunities
    &nbsp; • &nbsp;
    💡 Weekly action
    </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FIRST RUN
# ============================================================

if not st.session_state.items:

    st.info(
        """
        ### Ready to build this week's progression update

        The Hub will look for:

        🏫 **North West university open days**

        🎓 **Degree and higher apprenticeships**

        💼 **Live apprenticeship opportunities**

        📅 **Important progression dates**

        🏫 **Your own college activities**

        💡 **A weekly student action**

        The Teams bulletin will deliberately show only
        the **most important items**, rather than dumping
        every search result onto students.
        """
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "🏫 Universities",
            len(
                NORTH_WEST_UNIVERSITIES
            ),
        )

    with c2:
        st.metric(
            "🎓 Degree routes",
            "LIVE",
        )

    with c3:
        st.metric(
            "💡 Weekly action",
            "1",
        )

    with c4:
        st.metric(
            "📢 Teams items",
            "MAX 5",
        )

    st.stop()


# ============================================================
# DATA
# ============================================================

items = [
    item
    for item
    in st.session_state.items
    if isinstance(item, dict)
]


priorities = get_priorities(
    items
)

highlights = weekly_highlights(
    items
)

open_days = category_items(
    items,
    "🏫 University Open Day",
)

degree_apps = category_items(
    items,
    "🎓 Degree Apprenticeship",
)

apprenticeships = category_items(
    items,
    "🎓 Apprenticeship",
)

key_dates = category_items(
    items,
    "📅 Key Date",
)

college_items = [
    item
    for item
    in items
    if item.get("source")
    == "College added"
]


# ============================================================
# DASHBOARD
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric(
        "🔥 This week's picks",
        len(highlights),
    )

with c2:
    st.metric(
        "🏫 Open days",
        len(open_days),
    )

with c3:
    st.metric(
        "🎓 Degree apprenticeships",
        len(degree_apps),
    )

with c4:
    st.metric(
        "💼 Other apprenticeships",
        len(apprenticeships),
    )

with c5:
    st.metric(
        "🏫 College activities",
        len(college_items),
    )


if st.session_state.last_refresh:

    st.caption(
        "Last refreshed: "
        + st.session_state.last_refresh
    )


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "🔥 This Week",
        "💡 Weekly Action",
        "🎓 Degree Apprenticeships",
        "🏫 North West Open Days",
        "💼 Apprenticeships",
        "📅 Key Dates",
        "🏫 College Activities",
        "📢 Teams Bulletin",
        "➕ Add Activity",
        "🔎 All Opportunities",
        "⚙️ Sources",
    ]
)


# ============================================================
# THIS WEEK
# ============================================================

with tabs[0]:

    st.header(
        "🔥 This Week"
    )

    st.write(
        "The most important progression information "
        "for students this week."
    )

    display_weekly_action()

    st.subheader(
        "🔥 Don't miss"
    )

    if not highlights:

        st.success(
            "No major opportunities were identified."
        )

    else:

        for index, item in enumerate(
            highlights
        ):

            display_card(
                item,
                f"highlight_{index}",
            )


# ============================================================
# WEEKLY ACTION
# ============================================================

with tabs[1]:

    st.header(
        "💡 Weekly Student Action"
    )

    st.write(
        "One practical task designed to move "
        "students' post-18 plans forward."
    )

    display_weekly_action()

    st.subheader(
        "📚 The action programme"
    )

    for index, action in enumerate(
        WEEKLY_ACTIONS,
        start=1,
    ):

        with st.expander(
            f"{index}. {action['title']}"
        ):

            st.write(
                action["text"]
            )

            st.success(
                action["target"]
            )


# ============================================================
# DEGREE APPRENTICESHIPS
# ============================================================

with tabs[2]:

    st.header(
        "🎓 Degree & Higher Apprenticeships"
    )

    st.info(
        """
        This section is specifically designed to find
        **degree-level apprenticeship routes**, including
        Level 6, Level 7, higher and chartered apprenticeships.

        These are kept separate from ordinary Level 2–5
        apprenticeship vacancies.
        """
    )

    search = st.text_input(
        "🔎 Search degree apprenticeships",
        placeholder=(
            "Try: digital, engineering, finance, law, "
            "Liverpool, Manchester..."
        ),
        key="degree_search",
    )

    filtered = [
        item
        for item in degree_apps
        if search.lower()
        in (
            item.get("title", "")
            + " "
            + item.get(
                "description",
                "",
            )
            + " "
            + item.get(
                "location",
                "",
            )
        ).lower()
    ]

    filtered.sort(
        key=ranking_score,
        reverse=True,
    )

    if not filtered:

        st.warning(
            "No degree apprenticeship results matched."
        )

    else:

        for index, item in enumerate(
            filtered
        ):

            display_card(
                item,
                f"degree_{index}",
            )


# ============================================================
# NORTH WEST OPEN DAYS
# ============================================================

with tabs[3]:

    st.header(
        "🏫 North West University Open Days"
    )

    st.info(
        """
        The Hub prioritises universities in the North West,
        including Liverpool, Manchester, Chester, Lancashire
        and Cumbria.
        """
    )

    search = st.text_input(
        "🔎 Search university open days",
        placeholder=(
            "Liverpool, Manchester, engineering..."
        ),
        key="university_search",
    )

    filtered = [
        item
        for item in open_days
        if search.lower()
        in (
            item.get("title", "")
            + " "
            + item.get(
                "organisation",
                "",
            )
            + " "
            + item.get(
                "location",
                "",
            )
        ).lower()
    ]

    filtered.sort(
        key=lambda x: (
            parse_date(
                x.get(
                    "event_date",
                    "",
                )
            )
            or date.max
        )
    )

    if not filtered:

        st.warning(
            "No upcoming North West open days found."
        )

    else:

        for index, item in enumerate(
            filtered
        ):

            display_card(
                item,
                f"uni_{index}",
            )


# ============================================================
# APPRENTICESHIPS
# ============================================================

with tabs[4]:

    st.header(
        "💼 Apprenticeships"
    )

    search = st.text_input(
        "🔎 Search apprenticeships",
        placeholder=(
            "engineering, finance, digital..."
        ),
        key="general_apprenticeship_search",
    )

    filtered = [
        item
        for item in apprenticeships
        if search.lower()
        in (
            item.get("title", "")
            + " "
            + item.get(
                "description",
                "",
            )
            + " "
            + item.get(
                "location",
                "",
            )
        ).lower()
    ]

    filtered.sort(
        key=ranking_score,
        reverse=True,
    )

    if not filtered:

        st.warning(
            "No apprenticeship results matched."
        )

    else:

        for index, item in enumerate(
            filtered
        ):

            display_card(
                item,
                f"apprenticeship_{index}",
            )


# ============================================================
# KEY DATES
# ============================================================

with tabs[5]:

    st.header(
        "📅 Important Dates"
    )

    for index, item in enumerate(
        key_dates
    ):

        display_card(
            item,
            f"date_{index}",
            removable=False,
        )


# ============================================================
# COLLEGE ACTIVITIES
# ============================================================

with tabs[6]:

    st.header(
        "🏫 College Activities & Events"
    )

    st.write(
        "Activities you have added yourself."
    )

    if not college_items:

        st.info(
            "You haven't added any college activities yet."
        )

    else:

        for index, item in enumerate(
            college_items
        ):

            display_card(
                item,
                f"college_{index}",
            )


# ============================================================
# TEAMS BULLETIN
# ============================================================

with tabs[7]:

    st.header(
        "📢 Microsoft Teams Bulletin"
    )

    st.success(
        """
        This is intentionally short.

        The bulletin contains the weekly action plus
        a maximum of five priority opportunities/events.
        """
    )

    bulletin = build_bulletin(
        items
    )

    st.text_area(
        "Copy this into Microsoft Teams",
        bulletin,
        height=600,
    )

    st.download_button(
        "📥 Download Teams bulletin",
        bulletin,
        file_name=(
            "KS5_Progression_"
            + TODAY.isoformat()
            + ".txt"
        ),
        mime="text/plain",
        use_container_width=True,
    )

    st.divider()

    st.subheader(
        "Why is it short?"
    )

    st.write(
        """
        Students are more likely to act on a small number
        of clear messages than a long list of opportunities.

        The full opportunity database remains available
        inside the Hub.
        """
    )


# ============================================================
# ADD ACTIVITY
# ============================================================

with tabs[8]:

    st.header(
        "➕ Add Your Own Activity or Event"
    )

    st.write(
        """
        Add anything that students at your sixth form
        need to know about. Your own activities can be
        promoted alongside live external opportunities.
        """
    )

    with st.form(
        "add_college_activity"
    ):

        title = st.text_input(
            "Activity / event title",
            placeholder=(
                "e.g. CV Workshop"
            ),
        )

        organisation = st.text_input(
            "Organisation",
            value="College",
        )

        category = st.selectbox(
            "Type",
            [
                "🏫 College Activity",
                "💼 Work Experience",
                "🎓 University Session",
                "🎓 Apprenticeship Session",
                "📅 College Deadline",
                "🎤 Employer Talk",
                "📝 Application Workshop",
                "Other",
            ],
        )

        description = st.text_area(
            "Short description",
            placeholder=(
                "Keep this short and student-friendly."
            ),
        )

        event_date = st.date_input(
            "Date",
            value=TODAY,
        )

        closing_date = st.date_input(
            "Closing / booking date",
            value=TODAY,
        )

        location = st.text_input(
            "Location",
            placeholder=(
                "e.g. Careers Centre / Room 12 / Online"
            ),
        )

        url = st.text_input(
            "Booking / information link",
            placeholder="https://...",
        )

        featured = st.checkbox(
            "🔥 Feature this in this week's bulletin",
            value=True,
        )

        submitted = st.form_submit_button(
            "➕ Add activity",
            type="primary",
        )

        if submitted:

            if not title.strip():

                st.error(
                    "Please enter a title."
                )

            else:

                new_item = make_item(
                    title=title,
                    organisation=organisation,
                    category=(
                        "🏫 College Activity"
                    ),
                    description=description,
                    event_date=(
                        event_date.strftime(
                            "%d %B %Y"
                        )
                    ),
                    closing_date=(
                        closing_date.strftime(
                            "%d %B %Y"
                        )
                    ),
                    location=location,
                    url=url,
                    source="College added",
                    tags=[
                        "🏫 College activity"
                    ],
                    priority=850,
                    verified=True,
                    featured=featured,
                )

                st.session_state.custom_items.append(
                    new_item
                )

                save_custom_items(
                    st.session_state.custom_items
                )

                st.session_state.items.append(
                    new_item
                )

                st.success(
                    "Activity added to the Hub."
                )

                st.rerun()


# ============================================================
# ALL OPPORTUNITIES
# ============================================================

with tabs[9]:

    st.header(
        "🔎 All Opportunities"
    )

    st.write(
        "This is the full database. It is deliberately "
        "separate from the short weekly Teams bulletin."
    )

    search = st.text_input(
        "🔎 Search everything",
        placeholder=(
            "Try: Liverpool, law, engineering, apprenticeship..."
        ),
        key="all_search",
    )

    filtered = [
        item
        for item in items
        if search.lower()
        in (
            item.get("title", "")
            + " "
            + item.get(
                "organisation",
                "",
            )
            + " "
            + item.get(
                "description",
                "",
            )
            + " "
            + item.get(
                "location",
                "",
            )
        ).lower()
    ]

    filtered.sort(
        key=ranking_score,
        reverse=True,
    )

    st.caption(
        f"{len(filtered)} results"
    )

    for index, item in enumerate(
        filtered
    ):

        display_card(
            item,
            f"all_{index}",
        )


# ============================================================
# SOURCES
# ============================================================

with tabs[10]:

    st.header(
        "⚙️ Sources & Search Coverage"
    )

    st.write(
        """
        The Hub searches public web results rather than
        requiring the Government Apprenticeship API key.
        Always check the original opportunity before applying.
        """
    )

    st.subheader(
        "🏫 North West university watchlist"
    )

    for university, details in (
        NORTH_WEST_UNIVERSITIES.items()
    ):

        st.write(
            f"**{university}** — "
            f"{details['city']} — "
            f"{details['domain']}"
        )

    st.divider()

    st.subheader(
        "🔎 Current search status"
    )

    for source, status in (
        st.session_state.source_status.items()
    ):

        st.write(
            f"**{source}:**"
        )

        if isinstance(
            status,
            dict,
        ):

            for university, result in (
                status.items()
            ):

                st.write(
                    f"- {university}: "
                    f"{result}"
                )

        else:

            st.write(
                status
            )

    st.divider()

    st.warning(
        """
        Search-engine results are used to discover public
        opportunities. Dates and availability can change,
        so students should always use the original source
        before booking or applying.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🎓 KS5 Progression Hub • "
    "Weekly progression intelligence • "
    f"{TODAY.strftime('%d %B %Y')}"
)
