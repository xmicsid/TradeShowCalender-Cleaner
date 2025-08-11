# clean_tradeshow.py
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urljoin
from typing import Iterable
import pandas as pd
from bs4 import BeautifulSoup

MONTHS = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
          "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}

BASE_URL = "https://thetradeshowcalendar.com/ttn/index.php"

def _parse_count(txt: str | None) -> int | None:
    if not txt:
        return None
    s = re.sub(r'[\s,~+]', '', txt.lower())
    # handle ranges like "20k-50k" -> midpoint
    m = re.match(r'(.+?)-(.+)$', s)
    def _to_num(part: str | None) -> int | None:
        if not part:
            return None
        m2 = re.match(r'(\d+(?:\.\d+)?)([km])?$', part)
        if m2:
            base = float(m2.group(1))
            unit = m2.group(2)
            if unit == 'k': base *= 1_000
            if unit == 'm': base *= 1_000_000
            return int(round(base))
        digits = re.findall(r'\d+', part)
        return int(digits[0]) if digits else None
    if m:
        a, b = _to_num(m.group(1)), _to_num(m.group(2))
        return int((a + b) / 2) if a and b else (a or b)
    return _to_num(s)

def _parse_date_part(part: str | None):
    if not part:
        return (None, None, None)
    t = part.strip().upper().replace(' ', '')
    m = re.match(r'([A-Z]{3})/(\d{1,2})(?:/(\d{2,4}))?$', t)
    if not m:
        return (None, None, None)
    mon = MONTHS.get(m.group(1))
    day = int(m.group(2))
    yr  = m.group(3)
    if yr:
        y = int(yr)
        if y < 100:  # '25' -> 2025
            y += 2000
    else:
        y = None
    return (mon, day, y)

def _parse_date_range(txt: str | None):
    if not txt:
        return (None, None)
    t = re.sub(r'\s+', '', txt.upper())
    parts = t.split('-')
    start = parts[0] if len(parts) > 0 else None
    end   = parts[1] if len(parts) > 1 else None
    sm, sd, sy = _parse_date_part(start)
    em, ed, ey = _parse_date_part(end)
    yr = ey or sy
    sdte = date(yr, sm, sd) if (yr and sm and sd) else None
    edte = date(yr, em, ed) if (yr and em and ed) else None
    return (sdte, edte)

def parse_html_bytes(html_bytes: bytes, base_url: str = BASE_URL) -> pd.DataFrame:
    soup = BeautifulSoup(html_bytes, 'lxml')
    rows = []
    for tr in soup.select('table tr:has(td)'):
        tds = tr.find_all('td')
        if len(tds) < 6:
            continue
        name = tds[0].get_text(strip=True)
        if not name:
            continue
        a = tds[0].find('a')
        href = a['href'] if (a and a.has_attr('href')) else None
        url = urljoin(base_url, href) if href else None

        next_dates = tds[1].get_text(' ', strip=True)
        cityraw    = tds[2].get_text(' ', strip=True)
        country    = tds[3].get_text(' ', strip=True)
        attendees_raw  = tds[4].get_text(' ', strip=True)
        exhibitors_raw = tds[5].get_text(' ', strip=True)

        # "Tampa, FL" -> City/State
        city, state = (cityraw.split(',', 1) + [None])[:2]
        city  = city.strip() if city else None
        state = state.strip() if state else None

        sd, ed = _parse_date_range(next_dates)

        rows.append({
            "Show Name": name,
            "Event URL": url,
            "Start Date": sd.isoformat() if sd else None,
            "End Date":   ed.isoformat() if ed else None,
            "City": (city or "").upper() or None,
            "State": (state or "").upper() or None,
            "Country": (country or "").upper() or None,
            "Attendees": _parse_count(attendees_raw),
            "Exhibitors": _parse_count(exhibitors_raw),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["Show Name"]).drop_duplicates()
    return df

def parse_many(files: Iterable[bytes]) -> pd.DataFrame:
    frames = []
    for b in files:
        frames.append(parse_html_bytes(b))
    if not frames:
        return pd.DataFrame(columns=[
            "Show Name","Event URL","Start Date","End Date",
            "City","State","Country","Attendees","Exhibitors"
        ])
    df = pd.concat(frames, ignore_index=True)
    # basic canonicalization
    for col in ["City","State","Country"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.upper().replace({"NONE": ""})
    # helpful sort
    df = df.sort_values(["Exhibitors","Attendees","Start Date"], ascending=[False, False, True], na_position="last")
    return df.reset_index(drop=True)
