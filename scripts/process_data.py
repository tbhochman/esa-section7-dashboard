#!/usr/bin/env python3
"""
Process Section 7 TAILS data (2008-2018) into aggregated JS for the dashboard.
Usage: python3 scripts/process_data.py path/to/section7_tails_2008_2018.csv
"""

import csv
import json
import sys
import re
from collections import Counter, defaultdict
from statistics import median, mean
from datetime import datetime

def parse_date(s):
    if not s or s == "NA":
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d")
    except ValueError:
        return None

def clean_str(s):
    if not s or s == "NA":
        return ""
    return s.strip().strip('"')

def safe_int(s):
    if not s or s == "NA":
        return 0
    try:
        return int(s)
    except ValueError:
        return 0

def safe_float(s):
    if not s or s == "NA":
        return None
    try:
        return float(s)
    except ValueError:
        return None

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "section7_tails_2008_2018.csv"

    rows = []
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Loaded {len(rows)} rows")

    # --- Filter to valid FY 2008-2016 ---
    valid_rows = []
    for r in rows:
        fy = safe_int(r.get("FY", ""))
        if 2008 <= fy <= 2016:
            valid_rows.append(r)

    print(f"Valid FY 2008-2016: {len(valid_rows)} rows")
    rows = valid_rows

    # --- KPIs ---
    total = len(rows)
    formal_count = sum(1 for r in rows if clean_str(r.get("formal_consult", "")) == "Yes")
    informal_count = total - formal_count

    # Duration stats are formal consultations only
    elapsed_days = []
    for r in rows:
        if clean_str(r.get("formal_consult", "")) == "Yes":
            e = safe_int(r.get("elapsed", ""))
            if e > 0:
                elapsed_days.append(e)

    median_elapsed = round(median(elapsed_days), 1) if elapsed_days else 0
    mean_elapsed = round(mean(elapsed_days), 1) if elapsed_days else 0

    timely_yes = sum(1 for r in rows if clean_str(r.get("timely_concl", "")) == "Yes")
    timely_total = sum(1 for r in rows if clean_str(r.get("timely_concl", "")) in ("Yes", "No"))
    timely_pct = round(100 * timely_yes / timely_total, 1) if timely_total else 0

    jeop_count = sum(1 for r in rows if safe_int(r.get("n_jeop", "")) > 0)

    # --- By Fiscal Year ---
    by_fy = defaultdict(lambda: {"total": 0, "formal": 0, "informal": 0, "elapsed": [], "jeop": 0})
    for r in rows:
        fy = safe_int(r.get("FY", ""))
        d = by_fy[fy]
        d["total"] += 1
        is_formal = clean_str(r.get("formal_consult", "")) == "Yes"
        if is_formal:
            d["formal"] += 1
            e = safe_int(r.get("elapsed", ""))
            if e > 0:
                d["elapsed"].append(e)
        else:
            d["informal"] += 1
        if safe_int(r.get("n_jeop", "")) > 0:
            d["jeop"] += 1

    years = sorted(by_fy.keys())
    annual_data = []
    for y in years:
        d = by_fy[y]
        annual_data.append({
            "year": y,
            "total": d["total"],
            "formal": d["formal"],
            "informal": d["informal"],
            "median_elapsed": round(median(d["elapsed"]), 1) if d["elapsed"] else 0,
            "mean_elapsed": round(mean(d["elapsed"]), 1) if d["elapsed"] else 0,
            "jeop": d["jeop"],
        })

    # --- By Lead Agency (top 20) ---
    agency_counter = Counter()
    agency_elapsed = defaultdict(list)  # formal only
    agency_formal = Counter()
    agency_jeop = Counter()
    for r in rows:
        a = clean_str(r.get("lead_agency", ""))
        if not a:
            a = "Unknown"
        agency_counter[a] += 1
        is_formal = clean_str(r.get("formal_consult", "")) == "Yes"
        if is_formal:
            agency_formal[a] += 1
            e = safe_int(r.get("elapsed", ""))
            if e > 0:
                agency_elapsed[a].append(e)
        if safe_int(r.get("n_jeop", "")) > 0:
            agency_jeop[a] += 1

    top_agencies = [a for a, _ in agency_counter.most_common(20)]
    agency_data = []
    for a in top_agencies:
        agency_data.append({
            "name": a,
            "count": agency_counter[a],
            "median_elapsed": round(median(agency_elapsed[a]), 1) if agency_elapsed[a] else 0,
            "formal": agency_formal[a],
            "jeop": agency_jeop[a],
        })

    # --- By Work Category (top 20) ---
    cat_counter = Counter()
    cat_elapsed = defaultdict(list)  # formal only
    cat_formal = Counter()
    for r in rows:
        c = clean_str(r.get("work_category", ""))
        if not c or c in ("Standard", "Informal Consultation", "No", "Yes"):
            c = "other"
        cat_counter[c] += 1
        is_formal = clean_str(r.get("formal_consult", "")) == "Yes"
        if is_formal:
            cat_formal[c] += 1
            e = safe_int(r.get("elapsed", ""))
            if e > 0:
                cat_elapsed[c].append(e)

    top_cats = [c for c, _ in cat_counter.most_common(20)]
    category_data = []
    for c in top_cats:
        category_data.append({
            "name": c,
            "count": cat_counter[c],
            "median_elapsed": round(median(cat_elapsed[c]), 1) if cat_elapsed[c] else 0,
            "formal": cat_formal[c],
        })

    # --- By State ---
    state_counter = Counter()
    state_elapsed = defaultdict(list)  # formal only
    state_formal = Counter()
    for r in rows:
        s = clean_str(r.get("state", ""))
        if not s:
            s = "Unknown"
        state_counter[s] += 1
        is_formal = clean_str(r.get("formal_consult", "")) == "Yes"
        if is_formal:
            state_formal[s] += 1
            e = safe_int(r.get("elapsed", ""))
            if e > 0:
                state_elapsed[s].append(e)

    state_data = []
    for s, cnt in state_counter.most_common(50):
        state_data.append({
            "name": s,
            "count": cnt,
            "median_elapsed": round(median(state_elapsed[s]), 1) if state_elapsed[s] else 0,
            "formal": state_formal[s],
        })

    # --- By FWS Region ---
    region_counter = Counter()
    region_elapsed = defaultdict(list)
    region_formal = Counter()
    region_names = {
        "1": "Pacific (1)",
        "2": "Southwest (2)",
        "3": "Great Lakes (3)",
        "4": "Southeast (4)",
        "5": "Northeast (5)",
        "6": "Mountain-Prairie (6)",
        "7": "Alaska (7)",
        "8": "Pacific Southwest (8)",
    }
    for r in rows:
        reg = clean_str(r.get("region", ""))
        rname = region_names.get(reg, f"Region {reg}" if reg else "Unknown")
        region_counter[rname] += 1
        is_formal = clean_str(r.get("formal_consult", "")) == "Yes"
        if is_formal:
            region_formal[rname] += 1
            e = safe_int(r.get("elapsed", ""))
            if e > 0:
                region_elapsed[rname].append(e)

    region_data = []
    for rname, cnt in region_counter.most_common():
        region_data.append({
            "name": rname,
            "count": cnt,
            "median_elapsed": round(median(region_elapsed[rname]), 1) if region_elapsed[rname] else 0,
            "formal": region_formal[rname],
        })

    # --- Consultation Type Breakdown ---
    consult_type_counter = Counter()
    for r in rows:
        ct = clean_str(r.get("consult_type", ""))
        if ct:
            consult_type_counter[ct] += 1

    consult_type_data = [{"name": k, "count": v} for k, v in consult_type_counter.most_common()]

    # --- Consultation Complexity ---
    complexity_counter = Counter()
    for r in rows:
        cx = clean_str(r.get("consult_complex", ""))
        if cx:
            complexity_counter[cx] += 1

    complexity_data = [{"name": k, "count": v} for k, v in complexity_counter.most_common(10)]

    # --- Species Analysis ---
    species_counter = Counter()
    species_jeop = Counter()
    for r in rows:
        spp_list = clean_str(r.get("spp_ev_ls", ""))
        if not spp_list:
            continue
        # Parse species: "Name, common (Scientific name); Name2, ..."
        species = [s.strip() for s in spp_list.split(";") if s.strip()]
        for sp in species:
            # Extract common name portion before the parenthetical
            match = re.match(r"^(.+?)\s*\(", sp)
            if match:
                name = match.group(1).strip().rstrip(",")
                # Normalize: "Trout, bull" -> "Bull Trout"
                parts = [p.strip() for p in name.split(",")]
                if len(parts) == 2:
                    name = f"{parts[1].title()} {parts[0].title()}"
                else:
                    name = name.title()
                species_counter[name] += 1

        # Check jeopardy per species from BO list
        bo_list = clean_str(r.get("spp_BO_ls", ""))
        if "jeopardy" in bo_list.lower() and "non-jeopardy" not in bo_list.lower():
            # This is rare; let's count jeopardy at the consultation level
            pass

    # For jeopardy by species, parse spp_BO_ls more carefully
    for r in rows:
        bo_list = clean_str(r.get("spp_BO_ls", ""))
        if not bo_list:
            continue
        # Format: "species name: BO = Jeopardy; CH = ..., species2: ..."
        entries = bo_list.split("),")
        for entry in entries:
            if "jeopardy" in entry.lower():
                is_non_jeop = "non-jeopardy" in entry.lower()
                is_jeop = "jeopardy" in entry.lower() and not is_non_jeop
                if is_jeop:
                    # Extract species name
                    match = re.match(r"^\s*(.+?):\s*BO", entry)
                    if match:
                        name = match.group(1).strip().title()
                        species_jeop[name] += 1

    top_species = [{"name": k, "count": v} for k, v in species_counter.most_common(30)]

    # Jeopardy species
    top_jeop_species = [{"name": k, "count": v} for k, v in species_jeop.most_common(20)]

    # --- Elapsed Distribution (histogram buckets) ---
    elapsed_buckets = {"1-30": 0, "31-60": 0, "61-90": 0, "91-180": 0, "181-365": 0, "366+": 0}
    for e in elapsed_days:
        if e <= 30:
            elapsed_buckets["1-30"] += 1
        elif e <= 60:
            elapsed_buckets["31-60"] += 1
        elif e <= 90:
            elapsed_buckets["61-90"] += 1
        elif e <= 180:
            elapsed_buckets["91-180"] += 1
        elif e <= 365:
            elapsed_buckets["181-365"] += 1
        else:
            elapsed_buckets["366+"] += 1

    elapsed_dist = [{"bucket": k, "count": v} for k, v in elapsed_buckets.items()]

    # --- Informal consultation elapsed distribution (kept as reference) ---
    informal_elapsed = []
    for r in rows:
        if clean_str(r.get("formal_consult", "")) != "Yes":
            e = safe_int(r.get("elapsed", ""))
            if e > 0:
                informal_elapsed.append(e)

    informal_elapsed_buckets = {"1-30": 0, "31-60": 0, "61-90": 0, "91-180": 0, "181-365": 0, "366+": 0}
    for e in informal_elapsed:
        if e <= 30:
            informal_elapsed_buckets["1-30"] += 1
        elif e <= 60:
            informal_elapsed_buckets["31-60"] += 1
        elif e <= 90:
            informal_elapsed_buckets["61-90"] += 1
        elif e <= 180:
            informal_elapsed_buckets["91-180"] += 1
        elif e <= 365:
            informal_elapsed_buckets["181-365"] += 1
        else:
            informal_elapsed_buckets["366+"] += 1

    # --- Findings breakdown (for formal consultations) ---
    total_jeop = sum(safe_int(r.get("n_jeop", "")) for r in rows)
    total_non_jeop_formal = formal_count  # approximate
    total_rpa = sum(safe_int(r.get("n_rpa", "")) for r in rows)
    total_admo = sum(safe_int(r.get("n_admo", "")) for r in rows)

    # Total species evaluated and in BOs
    total_spp_eval = sum(safe_int(r.get("n_spp_eval", "")) for r in rows)
    total_spp_bo = sum(safe_int(r.get("n_spp_BO", "")) for r in rows)
    total_nofx = sum(safe_int(r.get("n_nofx", "")) for r in rows)
    total_nlaa = sum(safe_int(r.get("n_NLAA", "")) for r in rows)
    total_conc = sum(safe_int(r.get("n_conc", "")) for r in rows)

    # --- Build output ---
    output = {
        "meta": {
            "total_consultations": total,
            "date_range": "FY 2008-2016",
            "generated": datetime.now().strftime("%Y-%m-%d"),
        },
        "kpis": {
            "total": total,
            "formal": formal_count,
            "informal": informal_count,
            "formal_pct": round(100 * formal_count / total, 1) if total else 0,
            "median_elapsed_days": median_elapsed,
            "mean_elapsed_days": mean_elapsed,
            "jeopardy_consultations": jeop_count,
            "jeopardy_pct": round(100 * jeop_count / total, 2) if total else 0,
        },
        "species_totals": {
            "total_evaluated": total_spp_eval,
            "total_in_bo": total_spp_bo,
            "no_effect": total_nofx,
            "nlaa": total_nlaa,
            "concurrences": total_conc,
            "jeopardy_findings": total_jeop,
            "rpa": total_rpa,
            "adverse_modification": total_admo,
        },
        "annual": annual_data,
        "by_agency": agency_data,
        "by_category": category_data,
        "by_state": state_data,
        "by_region": region_data,
        "consult_types": consult_type_data,
        "complexity": complexity_data,
        "top_species": top_species,
        "jeopardy_species": top_jeop_species,
        "elapsed_distribution": elapsed_dist,
        "informal_elapsed_dist": [{"bucket": k, "count": v} for k, v in informal_elapsed_buckets.items()],
        "informal_stats": {
            "median_elapsed": round(median(informal_elapsed), 1) if informal_elapsed else 0,
            "mean_elapsed": round(mean(informal_elapsed), 1) if informal_elapsed else 0,
        },
    }

    js_content = f"// ESA Section 7 TAILS Dashboard Data\n// {total} consultations, FY 2008-2016\n// Duration data reflects formal consultations only\n// Generated: {output['meta']['generated']}\n\nconst DATA = {json.dumps(output, indent=2)};\n"

    out_path = "data.js"
    with open(out_path, "w") as f:
        f.write(js_content)

    print(f"Wrote {out_path} ({len(js_content)} bytes)")
    print(f"KPIs: {json.dumps(output['kpis'], indent=2)}")

if __name__ == "__main__":
    main()
