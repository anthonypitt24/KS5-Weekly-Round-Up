import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import re, html, hashlib, json, os
from urllib.parse import quote, urlparse

st.set_page_config(page_title="KS5 Progression Hub", page_icon="🎓", layout="wide")

TODAY = date.today()
DATA_FILE = "ks5_progression_custom.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139 Safari/537.36"}

NORTH_WEST_UNIVERSITIES = {
    "University of Liverpool": ("Liverpool", "liverpool.ac.uk"),
    "Liverpool John Moores University": ("Liverpool", "ljmu.ac.uk"),
    "Liverpool Hope University": ("Liverpool", "hope.ac.uk"),
    "Edge Hill University": ("Ormskirk", "edgehill.ac.uk"),
    "University of Chester": ("Chester", "chester.ac.uk"),
    "University of Manchester": ("Manchester", "manchester.ac.uk"),
    "Manchester Metropolitan University": ("Manchester", "mmu.ac.uk"),
    "University of Salford": ("Salford", "salford.ac.uk"),
    "University of Bolton": ("Bolton", "greatermanchester.ac.uk"),
    "University of Central Lancashire": ("Preston", "uclan.ac.uk"),
    "Lancaster University": ("Lancaster", "lancaster.ac.uk"),
    "University of Cumbria": ("Carlisle", "cumbria.ac.uk"),
    "Liverpool Institute for Performing Arts": ("Liverpool", "lipa.ac.uk"),
}

CAREER_KEYWORDS = {
    "All categories": [],
    "Digital & Technology": ["digital","software","computing","computer","cyber","technology","data","artificial intelligence","programming","developer","it"],
    "Engineering": ["engineering","engineer","mechanical","electrical","civil","aerospace","manufacturing","automotive","design engineer"],
    "Business & Administration": ["business","management","administration","operations","project management","marketing","human resources","hr"],
    "Finance & Legal": ["finance","accounting","accountancy","banking","economics","tax","audit","legal","law"],
    "Health & Science": ["health","healthcare","nursing","science","laboratory","pharmacy","medicine","clinical","biomedical"],
    "Creative & Media": ["creative","media","film","television","design","graphic","journalism","music","performing arts","advertising"],
    "Construction": ["construction","quantity surveying","building","property","architecture","surveying"],
    "Education": ["education","teaching","teacher","early years","childcare"],
}

WEEKLY_ACTIONS = [
    ("🔎 Career Research","Choose one career you're considering and spend 20 minutes finding out what qualifications, skills and routes are needed.","Write down 3 things you have learned."),
    ("📄 Build Your CV","Create your first CV or improve your existing one. Include your education, experience, achievements and skills.","Finish one section of your CV."),
    ("🎓 Compare University Courses","Choose one subject you might study and compare three university courses. Look at entry requirements and modules.","Write down your favourite course and why."),
    ("🎓 Explore Degree Apprenticeships","Find three degree apprenticeship routes linked to careers you are interested in.","Save three opportunities and check their entry requirements."),
    ("💼 Find Work Experience","Search for one work-experience, volunteering or employer opportunity connected to an area you might pursue.","Identify one opportunity you could apply for."),
    ("🧠 Skills Audit","Think about the career or course you want. Identify the skills employers or universities are looking for.","Choose one skill you can develop this term."),
    ("✍️ Personal Statement","Write 100–150 words explaining why you are interested in your chosen subject or career.","Save your first draft."),
    ("🏫 Book an Open Day","Find an upcoming university open day and investigate whether it is worth attending.","Book one open day or add it to your calendar."),
    ("🏢 Research Employers","Choose three employers you might like to work for and investigate their graduate or apprenticeship routes.","Save three employer websites."),
    ("🎤 Interview Practice","Practise answering five common interview questions, using examples from school, college, work or your interests.","Record or write your strongest answer."),
    ("🌐 Improve Your Profile","Review your online professional profile or create one. Make sure your skills, interests and achievements are clear.","Add one achievement or skill."),
    ("📚 Super-Curricular Learning","Spend 30 minutes learning something beyond your normal lessons in a subject you might study.","Record what you learned and one question it raised."),
]

if "items" not in st.session_state: st.session_state["items"] = []
if "custom_items" not in st.session_state: st.session_state["custom_items"] = []
if "removed" not in st.session_state: st.session_state["removed"] = set()
if "last_refresh" not in st.session_state: st.session_state["last_refresh"] = ""
if "source_status" not in st.session_state: st.session_state["source_status"] = {}

def load_custom():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_custom(items):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

if not st.session_state["custom_items"]:
    st.session_state["custom_items"] = load_custom()

def clean(x):
    if not x: return ""
    return re.sub(r"\s+", " ", BeautifulSoup(str(x), "html.parser").get_text(" ", strip=True)).strip()

def get(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""

def make_id(*parts):
    return hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:12]

def parse_date(value):
    if not value: return None
    if isinstance(value, date): return value
    value = str(value).strip()
    for fmt in ("%d %B %Y","%d %b %Y","%A %d %B %Y","%a %d %b %Y","%d/%m/%Y","%d-%m-%Y","%Y-%m-%d","%d %B","%d %b"):
        try:
            d = datetime.strptime(value, fmt).date()
            return d if "%Y" in fmt else d.replace(year=TODAY.year)
        except Exception:
            pass
    return None

def fmt(value):
    d = parse_date(value)
    return d.strftime("%d %b %Y") if d else str(value or "")

def days(value):
    d = parse_date(value)
    return (d - TODAY).days if d else None

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"\b(\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}}|\d{{1,2}}\s+(?:{MONTHS})|(?:{MONTHS})\s+\d{{1,2}},\s+\d{{4}})\b", re.I)

def nearest_future_date(text):
    found = []
    for raw in DATE_RE.findall(text or ""):
        d = parse_date(raw)
        if d and d >= TODAY:
            found.append(d)
    return min(found) if found else None

def make_item(title, organisation="", category="", description="", event_date="", closing_date="", location="", url="", source="", tags=None, priority=0, verified=False, level="", featured=False):
    return {
        "id": make_id(title, organisation, event_date, url),
        "title": clean(title), "organisation": clean(organisation), "category": category,
        "description": clean(description), "event_date": clean(event_date), "closing_date": clean(closing_date),
        "location": clean(location), "url": url, "source": source, "tags": tags or [],
        "priority": priority, "verified": verified, "level": level, "featured": featured
    }

def search_web(query, max_results=8):
    url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    text = get(url, 20)
    if not text: return []
    soup = BeautifulSoup(text, "html.parser")
    out = []
    for result in soup.select(".result"):
        a = result.select_one(".result__a")
        s = result.select_one(".result__snippet")
        if not a: continue
        out.append({
            "title": clean(a.get_text(" ", strip=True)),
            "url": a.get("href", ""),
            "description": clean(s.get_text(" ", strip=True) if s else "")
        })
        if len(out) >= max_results: break
    return out

def infer_location(text):
    for place in ["Liverpool","Manchester","Chester","Preston","Lancaster","Salford","Bolton","Carlisle","Blackburn","Warrington","Wirral"]:
        if place.lower() in text.lower(): return place
    return "North West / UK"

def degree_route(text):
    t = text.lower()
    return any(x in t for x in ["degree apprenticeship","degree apprenticeships","level 6 apprenticeship","level 7 apprenticeship","higher apprenticeship","higher apprenticeships","chartered apprenticeship"])

def infer_level(text):
    t = text.lower()
    if "level 7" in t: return "Level 7"
    if "level 6" in t or "degree apprenticeship" in t: return "Level 6"
    if "higher apprenticeship" in t: return "Higher"
    return "Higher / Degree"

OFFICIAL_OPEN_DAY_PAGES = {
    "University of Liverpool": "https://www.liverpool.ac.uk/undergraduate/open-days-and-visits/",
    "Liverpool John Moores University": "https://www.ljmu.ac.uk/study/undergraduate-students/undergraduate-open-days",
    "Liverpool Hope University": "https://www.hope.ac.uk/opendays/",
    "Edge Hill University": "https://www.edgehill.ac.uk/study/visit-us/open-days/",
    "University of Chester": "https://www.chester.ac.uk/study/visit-us/open-days/",
    "University of Manchester": "https://www.manchester.ac.uk/study/undergraduate/open-days-visits/open-days/",
    "Manchester Metropolitan University": "https://www.mmu.ac.uk/study/open-days/undergraduate",
    "University of Salford": "https://www.salford.ac.uk/undergraduate/open-days",
    "University of Greater Manchester": "https://greatermanchester.ac.uk/open-days/book-an-open-day",
    "University of Central Lancashire": "https://www.ucas.com/events/university-of-central-lancashire-open-day-469911",
    "Lancaster University": "https://www.lancaster.ac.uk/study/open-days/undergraduate-open-days/",
    "University of Cumbria": "https://www.cumbria.ac.uk/events/open-days/",
    "Liverpool Institute for Performing Arts": "https://lipa.ac.uk/open-days",
}

# Verified current 2026 dates used as a safety net if a university page
# changes its HTML or blocks automated requests. These are not guesses:
# they are the dates published by the universities/UCAS and should be
# refreshed each academic year.
VERIFIED_OPEN_DAYS_2026 = {
    "University of Liverpool": ["26 September 2026", "10 October 2026"],
    "Liverpool John Moores University": ["10 October 2026", "6 November 2026", "14 November 2026"],
    "Liverpool Hope University": ["19 September 2026", "28 October 2026"],
    "Edge Hill University": ["17 October 2026", "21 November 2026"],
    "University of Chester": ["17 October 2026", "7 November 2026"],
    "University of Manchester": ["3 October 2026", "10 October 2026"],
    "Manchester Metropolitan University": ["10 October 2026", "17 October 2026", "21 November 2026"],
    "University of Salford": ["10 October 2026", "7 November 2026", "12 December 2026"],
    "University of Greater Manchester": ["4 October 2026"],
    "University of Central Lancashire": ["11 October 2026", "21 November 2026"],
    "Lancaster University": ["12 September 2026", "13 September 2026", "17 October 2026"],
    "University of Cumbria": [
        "26 September 2026", "3 October 2026", "10 October 2026",
        "17 October 2026", "7 November 2026", "14 November 2026", "21 November 2026"
    ],
    "Liverpool Institute for Performing Arts": ["4 October 2026", "11 October 2026", "26 October 2026", "22 November 2026"],
}

def extract_dates_near_open_day(page_text):
    """Extract future dates from text immediately surrounding 'open day'."""
    text = clean(page_text)
    found = set()
    lower = text.lower()

    for match in re.finditer(r"open day", lower):
        start = max(0, match.start() - 350)
        end = min(len(text), match.end() + 1400)
        chunk = text[start:end]
        for raw in DATE_RE.findall(chunk):
            d = parse_date(raw)
            if d and d >= TODAY:
                found.add(d)

    return sorted(found)

def direct_official_open_days(uni, page_url, cutoff):
    """Read the university's own page rather than relying on a search engine."""
    page = get(page_url, 20)
    if not page:
        return []

    soup = BeautifulSoup(page, "html.parser")

    # Prefer visible page text, while also checking JSON-LD event data.
    visible = soup.get_text(" ", strip=True)
    dates = extract_dates_near_open_day(visible)

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        for date_string in re.findall(
            r'"(?:startDate|endDate)"\s*:\s*"([^"]+)"', raw, flags=re.I
        ):
            d = parse_date(date_string[:10])
            if d and d >= TODAY:
                dates.append(d)

    return sorted({d for d in dates if TODAY <= d <= cutoff})

def search_open_days(months_ahead):
    items, status = [], {}
    cutoff = TODAY + timedelta(days=months_ahead * 30)

    for uni, (city, domain) in NORTH_WEST_UNIVERSITIES.items():
        # University of Bolton changed its public-facing name to
        # University of Greater Manchester during 2026.
        lookup_name = "University of Greater Manchester" if uni == "University of Bolton" else uni
        page_url = OFFICIAL_OPEN_DAY_PAGES.get(lookup_name, "")

        page_ok = bool(get(page_url, 20)) if page_url else False
        live_dates = direct_official_open_days(lookup_name, page_url, cutoff) if page_url else []

        verified_dates = [
            parse_date(d) for d in VERIFIED_OPEN_DAYS_2026.get(lookup_name, [])
        ]
        verified_dates = [d for d in verified_dates if d and TODAY <= d <= cutoff]

        # Use live official dates when the page is accessible. Only use the
        # academic-year safety-net dates when the official page cannot be read.
        if page_ok:
            dates_found = sorted(set(live_dates))
            status[uni] = (
                f"{len(dates_found)} event(s) read from official page"
                if dates_found else
                "Official page checked — no upcoming dated event found"
            )
        else:
            dates_found = sorted(set(verified_dates))
            status[uni] = (
                f"{len(dates_found)} safety-net event(s) — official page unavailable"
                if dates_found else
                "Official page unavailable and no safety-net date recorded"
            )

        for d in dates_found:
            diff = (d - TODAY).days
            if diff <= 7:
                tags, priority = ["🔥 This week", "📍 North West"], 950
            elif diff <= 14:
                tags, priority = ["📅 Coming up", "📍 North West"], 750
            else:
                tags, priority = ["📍 North West"], 500

            source_name = lookup_name
            items.append(
                make_item(
                    f"{source_name} — Undergraduate Open Day",
                    source_name,
                    "🏫 University Open Day",
                    "Official university open day. Check the university page for booking, course sessions and any entry requirements.",
                    fmt(d),
                    "",
                    city,
                    page_url,
                    f"{source_name} official website",
                    tags,
                    priority,
                    True,
                )
            )

    return items, status

def search_degree_apprenticeships(career):
    queries = [
        '"degree apprenticeship" "Liverpool" 2026 OR 2027',
        '"degree apprenticeship" "Manchester" 2026 OR 2027',
        '"degree apprenticeship" "North West" 2026 OR 2027',
        '"higher apprenticeship" "North West" 2026 OR 2027',
        '"level 6 apprenticeship" "Liverpool"',
        '"level 6 apprenticeship" "Manchester"',
        '"level 7 apprenticeship" "North West"',
    ]
    keys = CAREER_KEYWORDS.get(career, [])
    queries += [f'"degree apprenticeship" "{k}" "North West"' for k in keys[:4]]
    items, seen = [], set()
    for q in queries:
        for r in search_web(q, 8):
            combined = r["title"] + " " + r["description"]
            if not degree_route(combined): continue
            key = r["url"] or r["title"]
            if key in seen: continue
            seen.add(key)
            d = nearest_future_date(combined)
            closing = fmt(d) if d else ""
            diff = days(closing)
            if diff is not None and diff <= 3: priority, tags = 1000, ["🔴 Closing soon","🎓 Degree apprenticeship"]
            elif diff is not None and diff <= 7: priority, tags = 950, ["🔥 This week","🎓 Degree apprenticeship"]
            else: priority, tags = 800, ["🎓 Degree apprenticeship"]
            loc = infer_location(combined)
            if loc != "North West / UK": tags.append("📍 North West")
            items.append(make_item(r["title"], urlparse(r["url"]).netloc if r["url"] else "",
                "🎓 Degree Apprenticeship", r["description"], "", closing, loc, r["url"], "Web search",
                tags, priority, False, infer_level(combined)))
    return items

def search_apprenticeships(career):
    queries = ['"apprenticeship vacancy" Liverpool 2026','"apprenticeship vacancy" Manchester 2026','"apprenticeships" "North West" 2026']
    queries += [f'apprenticeship vacancy "{k}" Liverpool Manchester 2026' for k in CAREER_KEYWORDS.get(career, [])[:3]]
    items, seen = [], set()
    for q in queries:
        for r in search_web(q, 6):
            combined = r["title"] + " " + r["description"]
            if "apprenticeship" not in combined.lower() or degree_route(combined): continue
            key = r["url"] or r["title"]
            if key in seen: continue
            seen.add(key)
            d = nearest_future_date(combined)
            closing = fmt(d) if d else ""
            diff = days(closing)
            priority = 850 if diff is not None and diff <= 3 else 750 if diff is not None and diff <= 7 else 350
            items.append(make_item(r["title"], urlparse(r["url"]).netloc if r["url"] else "",
                "🎓 Apprenticeship", r["description"], "", closing, infer_location(combined),
                r["url"], "Web search", ["🎓 Apprenticeship"], priority))
    return items

def career_match(item, career):
    if career == "All categories": return True
    text = " ".join([item.get("title",""),item.get("description",""),item.get("organisation","")]).lower()
    return any(k.lower() in text for k in CAREER_KEYWORDS.get(career, []))

def refresh_all(career, months):
    open_days, status = search_open_days(months)
    degree = search_degree_apprenticeships(career)
    apprentices = search_apprenticeships(career)
    dates = [make_item("UCAS application deadlines", "UCAS", "📅 Key Date",
        "Check the official UCAS timetable for the application cycle and course you are using.",
        "", "", "", "https://www.ucas.com/", "UCAS", ["📅 Key date"], 500, True)]
    custom = [x for x in st.session_state["custom_items"] if x.get("id") not in st.session_state["removed"]]
    all_items = open_days + degree + apprentices + dates + custom
    if career != "All categories":
        all_items = [x for x in all_items if x.get("category") in ["🏫 University Open Day","📅 Key Date"] or x.get("source")=="College added" or career_match(x,career)]
    seen, result = set(), []
    for x in all_items:
        key = (x.get("title","").lower(),x.get("organisation","").lower(),x.get("event_date","").lower(),x.get("url","").lower())
        if key not in seen:
            seen.add(key); result.append(x)
    return result, status

def score(item):
    s = int(item.get("priority",0))
    tags = item.get("tags",[])
    if "🔴 Closing soon" in tags: s += 500
    if "🔥 This week" in tags: s += 350
    if "📍 North West" in tags: s += 250
    if item.get("category") == "🎓 Degree Apprenticeship": s += 300
    if item.get("featured"): s += 450
    if item.get("source") == "College added": s += 400
    c, e = days(item.get("closing_date")), days(item.get("event_date"))
    if c is not None: s += 600 if c <= 3 else 400 if c <= 7 else 150 if c <= 14 else 0
    if e is not None: s += 450 if e <= 7 else 200 if e <= 14 else 0
    return s

def ranked(items):
    return sorted(items, key=score, reverse=True)

def highlights(items):
    r, selected = ranked(items), []
    urgent = [x for x in r if days(x.get("closing_date")) is not None and days(x.get("closing_date")) <= 7]
    for x in urgent:
        if x not in selected: selected.append(x)
        if len(selected) >= 2: break
    for x in r:
        if x.get("category")=="🏫 University Open Day" and days(x.get("event_date")) is not None and days(x.get("event_date")) <= 30 and x not in selected:
            selected.append(x); break
    for x in r:
        if x.get("category")=="🎓 Degree Apprenticeship" and x not in selected:
            selected.append(x); break
    for x in r:
        if x.get("source")=="College added" and x.get("featured") and x not in selected:
            selected.append(x); break
    for x in r:
        if x not in selected:
            selected.append(x)
        if len(selected) >= 5: break
    return selected[:5]

def weekly_action():
    return WEEKLY_ACTIONS[(TODAY.isocalendar().week-1) % len(WEEKLY_ACTIONS)]

def bulletin(items):
    action = weekly_action()
    lines = [
        "🎓 KS5 PROGRESSION — THIS WEEK",
        f"Week commencing {TODAY.strftime('%d %B %Y')}",
        "",
        "💡 YOUR ACTION THIS WEEK",
        action[0], action[1], f"✅ {action[2]}", "",
        "🔥 DON'T MISS", ""
    ]
    for x in highlights(items):
        lines.append("• " + x.get("title","Opportunity"))
        if x.get("organisation"): lines.append("  " + x["organisation"])
        if x.get("event_date"): lines.append("  📅 " + x["event_date"])
        if x.get("closing_date"): lines.append("  ⏰ Closes " + x["closing_date"])
        if x.get("location"): lines.append("  📍 " + x["location"])
        if x.get("url"): lines.append("  🔗 " + x["url"])
        lines.append("")
    lines += ["📚 Want more?","Open the KS5 Progression Hub to explore all current opportunities."]
    return "\n".join(lines)

st.markdown("""
<style>
.hero{padding:2rem 2.2rem;border-radius:20px;margin-bottom:1.4rem;background:linear-gradient(135deg,#172554,#1e3a8a);color:white}
.hero h1{font-size:2.55rem;margin:0 0 .35rem 0}.hero p{font-size:1.05rem;margin:.25rem 0}
.kicker{font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;opacity:.8}
.card{padding:1.15rem 1.25rem;border-radius:15px;border:1px solid #e5e7eb;margin-bottom:.75rem;background:white}
.internal{padding:1rem 1.2rem;border-radius:14px;border:1px solid #dbeafe;background:#f8fbff;margin-bottom:1rem}
.action{padding:1.4rem;border-radius:18px;border:2px solid #dbeafe;background:#eff6ff;margin-bottom:1rem}
.muted{color:#6b7280;font-size:.85rem}
.badge{display:inline-block;padding:.22rem .55rem;border-radius:999px;background:#eef2ff;margin-right:.35rem;font-size:.78rem}
.smallgap{margin-top:.35rem}
</style>
""", unsafe_allow_html=True)

# Session state used for internal editorial choices.
if "bulletin_selected" not in st.session_state:
    st.session_state["bulletin_selected"] = set()
if "seen_ids" not in st.session_state:
    st.session_state["seen_ids"] = set()
if "internal_notes" not in st.session_state:
    st.session_state["internal_notes"] = {}

with st.sidebar:
    st.header("⚙️ Internal Controls")
    st.caption("This is an internal sixth-form management tool. Students only see the Teams bulletin you choose to publish.")
    career = st.selectbox("Career area", list(CAREER_KEYWORDS))
    months = st.slider("University look-ahead",1,6,2,format="%d month(s)")
    st.divider()
    build = st.button("🔄 CHECK FOR NEW INTELLIGENCE", type="primary", use_container_width=True)
    if build:
        with st.spinner("Checking official university pages and opportunity sources..."):
            fresh_items, source_status = refresh_all(career,months)
            old_ids = {x.get("id") for x in st.session_state["items"]}
            new_ids = {x.get("id") for x in fresh_items} - old_ids
            st.session_state["items"] = fresh_items
            st.session_state["source_status"] = source_status
            st.session_state["seen_ids"] = new_ids
            st.session_state["last_refresh"] = datetime.now().strftime("%d %B %Y at %H:%M")
            # Start the editorial selection from the automatic top five.
            st.session_state["bulletin_selected"] = {x.get("id") for x in highlights(fresh_items)}
        st.rerun()

st.markdown(f"""
<div class="hero">
<div class="kicker">Internal sixth-form progression intelligence</div>
<h1>🎓 KS5 Progression Intelligence</h1>
<p>Find what has appeared, changed or is happening soon — then decide what students actually need to see.</p>
<p>📍 North West university watch &nbsp;•&nbsp; 🎓 Degree apprenticeships &nbsp;•&nbsp; ⏰ Closing soon &nbsp;•&nbsp; 📢 Teams publishing</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state["items"]:
    st.info("### Ready for this week's intelligence check\n\nUse **CHECK FOR NEW INTELLIGENCE** in the sidebar. The dashboard will check the North West university watchlist, degree/higher apprenticeships, live apprenticeship opportunities, key dates and your own college activities.")
    st.stop()

items = [x for x in st.session_state["items"] if x.get("id") not in st.session_state["removed"]]
top = highlights(items)
open_days = [x for x in items if x.get("category")=="🏫 University Open Day"]
degree = [x for x in items if x.get("category")=="🎓 Degree Apprenticeship"]
apprentices = [x for x in items if x.get("category")=="🎓 Apprenticeship"]
college = [x for x in items if x.get("source")=="College added"]
closing_7 = [x for x in items if days(x.get("closing_date")) is not None and 0 <= days(x.get("closing_date")) <= 7]
new_items = [x for x in items if x.get("id") in st.session_state["seen_ids"]]

# Keep a useful default selection if the current session has none.
valid_ids = {x.get("id") for x in items}
st.session_state["bulletin_selected"] &= valid_ids
if not st.session_state["bulletin_selected"]:
    st.session_state["bulletin_selected"] = {x.get("id") for x in top}

a,b,c,d,e,f = st.columns(6)
a.metric("🔥 Bulletin picks",len(st.session_state["bulletin_selected"]))
b.metric("🆕 New this check",len(new_items))
c.metric("⏰ Closing ≤7 days",len(closing_7))
d.metric("🏫 NW open days",len(open_days))
e.metric("🎓 Degree apprenticeships",len(degree))
f.metric("🏢 College activities",len(college))
if st.session_state["last_refresh"]:
    st.caption("Last intelligence check: " + st.session_state["last_refresh"])

tabs = st.tabs([
    "📊 Overview","🆕 New & Changed","🔥 This Week","🎓 Degree Apprenticeships",
    "🏫 University Watch","💼 Apprenticeships","📅 Key Dates","🏢 College Activities",
    "📢 Build Teams Bulletin","➕ Add Activity","🗂 All Opportunities","⚙️ Sources"
])

def card(x, show_editorial=False, section="main"):
    title = html.escape(x.get("title",""))
    org = html.escape(x.get("organisation",""))
    desc = html.escape(x.get("description",""))
    event = html.escape(x.get("event_date",""))
    close = html.escape(x.get("closing_date",""))
    loc = html.escape(x.get("location",""))
    tags = " ".join(html.escape(t) for t in x.get("tags",[])[:4])
    st.markdown(f"""<div class="card">
    <h3>{title}</h3>
    <p><strong>{org}</strong></p>
    <p>{desc}</p>
    <p>📅 {event or "—"} &nbsp; ⏰ {close or "—"} &nbsp; 📍 {loc or "—"}</p>
    <p><span class="badge">{tags or "Uncategorised"}</span></p>
    </div>""", unsafe_allow_html=True)
    if x.get("url"):
        st.link_button("🔗 Open source",x["url"])
    if show_editorial:
        chosen = x.get("id") in st.session_state["bulletin_selected"]
        if st.checkbox("📢 Include in this week's Teams bulletin", value=chosen, key=f"sel_{section}_{x.get('id')}"):
            st.session_state["bulletin_selected"].add(x.get("id"))
        else:
            st.session_state["bulletin_selected"].discard(x.get("id"))
        note = st.text_input(
            "📝 Internal note",
            value=st.session_state["internal_notes"].get(x.get("id"),""),
            key=f"note_{section}_{x.get('id')}",
            placeholder="Optional — e.g. Good for Y13 Digital students"
        )
        st.session_state["internal_notes"][x.get("id")] = note

def internal_summary(items_to_use):
    if not items_to_use:
        return "No items currently match this view."
    urgent = sum(1 for x in items_to_use if days(x.get("closing_date")) is not None and 0 <= days(x.get("closing_date")) <= 7)
    nw = sum("📍 North West" in x.get("tags",[]) for x in items_to_use)
    return f"{len(items_to_use)} items • {urgent} closing within 7 days • {nw} North West-priority items"

def bulletin_from_selection(items):
    selected = [x for x in items if x.get("id") in st.session_state["bulletin_selected"]]
    selected = ranked(selected)[:5]
    action = weekly_action()
    lines = [
        "🎓 KS5 PROGRESSION — THIS WEEK",
        f"Week commencing {TODAY.strftime('%d %B %Y')}",
        "",
        "💡 YOUR ACTION THIS WEEK",
        action[0], action[1], f"✅ {action[2]}", "",
        "🔥 DON'T MISS", ""
    ]
    for x in selected:
        lines.append("• " + x.get("title","Opportunity"))
        if x.get("organisation"): lines.append("  " + x["organisation"])
        if x.get("event_date"): lines.append("  📅 " + x["event_date"])
        if x.get("closing_date"): lines.append("  ⏰ Closes " + x["closing_date"])
        if x.get("location"): lines.append("  📍 " + x["location"])
        if x.get("url"): lines.append("  🔗 " + x["url"])
        lines.append("")
    lines += ["📚 More opportunities are available in the KS5 Progression Hub."]
    return "\n".join(lines)

with tabs[0]:
    st.header("📊 Overview")
    st.markdown('<div class="internal"><strong>Internal view</strong><br>This page is for you. Use it to scan the week, make editorial decisions and publish only the strongest items to Teams.</div>', unsafe_allow_html=True)
    st.subheader("What needs your attention?")
    for label, data in [
        ("⏰ Closing soon", closing_7),
        ("🆕 New in this check", new_items),
        ("🏫 Next North West open days", sorted(open_days,key=lambda x: parse_date(x.get("event_date")) or date.max)[:5]),
    ]:
        st.markdown(f"### {label}")
        st.caption(internal_summary(data))
        if data:
            for x in ranked(data)[:5]: card(x, show_editorial=True, section="overview")
        else:
            st.info("Nothing currently flagged.")

with tabs[1]:
    st.header("🆕 New & Changed")
    st.write("Items discovered during the most recent intelligence check.")
    if new_items:
        for x in ranked(new_items): card(x, show_editorial=True, section="new")
    else:
        st.info("No newly discovered items are currently flagged. Run another intelligence check to compare the latest results.")

with tabs[2]:
    st.header("🔥 This Week")
    st.caption("Your editorial shortlist. The dashboard recommends five; you decide what gets published.")
    act=weekly_action()
    st.markdown(f"""<div class="action"><div class="muted">💡 WEEKLY STUDENT ACTION</div><h2>{html.escape(act[0])}</h2><p>{html.escape(act[1])}</p><strong>Target: {html.escape(act[2])}</strong></div>""",unsafe_allow_html=True)
    for x in top: card(x, show_editorial=True, section="week")

with tabs[3]:
    st.header("🎓 Degree & Higher Apprenticeships")
    st.caption("Prioritised because these are progression routes with strong relevance to sixth-form students.")
    q=st.text_input("🔎 Search",key="degq")
    data=[x for x in degree if q.lower() in (x.get("title","")+" "+x.get("description","")+" "+x.get("location","")).lower()]
    if not data: st.info("No degree/higher apprenticeship results found in the current check.")
    for x in ranked(data): card(x, show_editorial=True, section="degree")

with tabs[4]:
    st.header("🏫 North West University Watch")
    st.caption("This is a permanent watchlist of North West universities. Open days are checked against official university pages first.")
    q=st.text_input("🔎 Filter university",key="uniq")
    data=[x for x in open_days if q.lower() in (x.get("title","")+" "+x.get("organisation","")+" "+x.get("location","")).lower()]
    data.sort(key=lambda x: parse_date(x.get("event_date")) or date.max)
    for x in data: card(x, show_editorial=True, section="universities")

with tabs[5]:
    st.header("💼 Apprenticeships")
    q=st.text_input("🔎 Search",key="appq")
    data=[x for x in apprentices if q.lower() in (x.get("title","")+" "+x.get("description","")+" "+x.get("location","")).lower()]
    if not data: st.info("No apprenticeship results found in the current check.")
    for x in ranked(data): card(x, show_editorial=True, section="apprenticeships")

with tabs[6]:
    st.header("📅 Key Dates")
    for x in [x for x in items if x.get("category")=="📅 Key Date"]:
        card(x, show_editorial=True, section="dates")

with tabs[7]:
    st.header("🏢 College Activities")
    st.caption("Internal college events can be added here and selectively featured in the Teams bulletin.")
    for x in college:
        card(x, show_editorial=True, section="college")
    if not college: st.info("No college activities have been added yet.")

with tabs[8]:
    st.header("📢 Build Teams Bulletin")
    selected = [x for x in items if x.get("id") in st.session_state["bulletin_selected"]]
    st.info(f"Publishing limit: maximum 5 opportunity/event items + 1 weekly action. Currently selected: {min(len(selected),5)}.")
    st.subheader("Selected items")
    if selected:
        for x in ranked(selected)[:5]:
            st.write("✅", x.get("title",""))
    else:
        st.warning("Select items from the other tabs first.")
    text=bulletin_from_selection(items)
    st.text_area("Copy into Microsoft Teams",text,height=560)
    st.download_button("📥 Download Teams bulletin",text,file_name=f"KS5_Progression_{TODAY.isoformat()}.txt",mime="text/plain",use_container_width=True)
    st.divider()
    st.caption("The bulletin is the student-facing output. Your internal notes, source status and wider opportunity list are not included.")

with tabs[9]:
    st.header("➕ Add Your Own Activity or Event")
    st.caption("Add college events, employer talks, workshops, deadlines or anything else you want the Hub to consider.")
    with st.form("add"):
        title=st.text_input("Activity / event title",placeholder="e.g. CV Workshop")
        organisation=st.text_input("Organisation",value="College")
        kind=st.selectbox("Type",["🏫 College Activity","💼 Work Experience","🎓 University Session","🎓 Apprenticeship Session","📅 College Deadline","🎤 Employer Talk","📝 Application Workshop","Other"])
        desc=st.text_area("Short description")
        event=st.date_input("Date",TODAY)
        closing=st.date_input("Closing / booking date",TODAY)
        location=st.text_input("Location",placeholder="Careers Centre / Room 12 / Online")
        url=st.text_input("Booking / information link",placeholder="https://...")
        featured=st.checkbox("🔥 Recommend this for the Teams bulletin",True)
        submit=st.form_submit_button("➕ Add activity",type="primary")
        if submit:
            if not title.strip(): st.error("Please enter a title.")
            else:
                x=make_item(title,organisation,kind,desc,event.strftime("%d %B %Y"),closing.strftime("%d %B %Y"),location,url,"College added",["🏢 College activity"],850,True,"",featured)
                st.session_state["custom_items"].append(x); save_custom(st.session_state["custom_items"])
                st.session_state["items"].append(x)
                if featured: st.session_state["bulletin_selected"].add(x.get("id"))
                st.success("Activity added.")
                st.rerun()

with tabs[10]:
    st.header("🗂 All Opportunities")
    q=st.text_input("🔎 Search everything",key="allq")
    data=[x for x in items if q.lower() in (x.get("title","")+" "+x.get("organisation","")+" "+x.get("description","")+" "+x.get("location","")).lower()]
    st.caption(f"{len(data)} results")
    for x in ranked(data): card(x, show_editorial=True, section="all")

with tabs[11]:
    st.header("⚙️ Sources & Coverage")
    st.markdown('<div class="internal"><strong>Accuracy rule:</strong> official university pages are checked first. A dated 2026 safety-net is used only if the official page cannot be read automatically. Always open the original source before publishing or booking.</div>', unsafe_allow_html=True)
    st.subheader("🏫 North West university watchlist")
    for uni,(city,domain) in NORTH_WEST_UNIVERSITIES.items():
        st.write(f"**{uni}** — {city} — {domain}")
    st.divider()
    for source,status in st.session_state["source_status"].items():
        st.write(f"**{source}:**")
        if isinstance(status,dict):
            for uni,result in status.items(): st.write(f"- {uni}: {result}")
        else: st.write(status)

st.divider()
st.caption(f"🎓 KS5 Progression Intelligence • Internal use • {TODAY.strftime('%d %B %Y')}")
