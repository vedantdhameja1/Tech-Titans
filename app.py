import streamlit as st

# 1. DATA & GRAPH SETUP


ROUTES = [
    ("Delhi", "Jaipur", 280),
    ("Delhi", "Nagpur", 1050),
    ("Delhi", "Kolkata", 1500),
    ("Jaipur", "Ahmedabad", 650),
    ("Ahmedabad", "Mumbai", 530),
    ("Mumbai", "Nagpur", 830),
    ("Mumbai", "Hyderabad", 710),
    ("Nagpur", "Hyderabad", 500),
    ("Nagpur", "Kolkata", 1100),
    ("Hyderabad", "Bengaluru", 570),
    ("Hyderabad", "Chennai", 630),
    ("Bengaluru", "Chennai", 350),
    ("Kolkata", "Chennai", 1670),
]

MODES = {
    "Air": {"speed": 700, "handling": 6, "cost": 12.0, "co2": 600},
    "Rail": {"speed": 45, "handling": 12, "cost": 1.2, "co2": 25},
    "Road": {"speed": 40, "handling": 3, "cost": 2.5, "co2": 90},
}

GRAPH = {}
for a, b, km in ROUTES:
    GRAPH.setdefault(a, []).append((b, km))
    GRAPH.setdefault(b, []).append((a, km))



# 2. CORE LOGIC


def leg_stats(km, mode, tonnes):
    m = MODES[mode]
    time = km / m["speed"] + m["handling"]
    cost = km * tonnes * m["cost"]
    co2 = (km * tonnes * m["co2"]) / 1000.0
    return time, cost, co2


def find_paths(current, end, path):
    if current == end:
        return [path]
    found = []
    for nxt, _ in GRAPH.get(current, []):
        if nxt not in path:
            found += find_paths(nxt, end, path + [nxt])
    return found


def distance(a, b):
    for nxt, km in GRAPH.get(a, []):
        if nxt == b:
            return km
    return 0


def plan_route(src, dst, tonnes, w_co2, w_cost, w_speed):
    max_t = max_c = max_e = 0.0

    for a, b, km in ROUTES:
        for mode in MODES:
            t, c, e = leg_stats(km, mode, tonnes)
            max_t = max(max_t, t)
            max_c = max(max_c, c)
            max_e = max(max_e, e)

    paths = find_paths(src, dst, [src])
    if not paths:
        return None

    best = None

    for path in paths:
        legs = []
        tot_t = tot_c = tot_e = tot_score = 0.0

        for i in range(len(path) - 1):
            km = distance(path[i], path[i + 1])
            choice = None

            for mode in MODES:
                t, c, e = leg_stats(km, mode, tonnes)
                score = (w_co2 * e / max_e) + (w_cost * c / max_c) + (w_speed * t / max_t)
                if choice is None or score < choice[0]:
                    choice = (score, mode, t, c, e)

            score, mode, t, c, e = choice
            legs.append((path[i], path[i + 1], km, mode))
            tot_t += t
            tot_c += c
            tot_e += e
            tot_score += score

        if best is None or tot_score < best["score"]:
            best = {
                "path": path,
                "legs": legs,
                "time": tot_t,
                "cost": tot_c,
                "co2": tot_e,
                "score": tot_score,
            }

    return best


# 3. STREAMLIT UI


st.set_page_config(page_title="EcoTransit Router", layout="wide", page_icon="🌱")

st.title("🌱 EcoTransit: Intermodal Green Freight Router")
st.caption("Balance carbon footprint, financial cost, and delivery speed across multimodal Indian logistics networks.")

hubs = sorted(list(GRAPH.keys()))

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.subheader("Shipment Parameters")
    src = st.selectbox("Origin Hub", hubs, index=hubs.index("Delhi"))
    dst = st.selectbox("Destination Hub", hubs, index=hubs.index("Chennai"))
    tonnes = st.number_input("Cargo Weight (Tonnes)", min_value=0.1, max_value=500.0, value=10.0, step=0.5)

    st.subheader("Priority Distribution")
    co2_pct = st.slider("Carbon Reduction (%)", 0, 100, 60, step=5)
    cost_pct = st.slider("Cost Minimization (%)", 0, 100, 30, step=5)
    speed_pct = st.slider("Transit Speed (%)", 0, 100, 10, step=5)

    total_pct = co2_pct + cost_pct + speed_pct
    if total_pct != 100:
        st.warning(f"Total percentage must equal 100%. Current sum: **{total_pct}%**")
        run_btn = st.button("Calculate Optimal Route", disabled=True)
    else:
        st.success("Priorities balanced (100%)")
        run_btn = st.button("Calculate Optimal Route", type="primary")

with col_right:
    if run_btn:
        if src == dst:
            st.error("Origin and Destination cannot be the same hub.")
        else:
            w_co2 = co2_pct / 100.0
            w_cost = cost_pct / 100.0
            w_speed = speed_pct / 100.0

            eco = plan_route(src, dst, tonnes, w_co2, w_cost, w_speed)
            fast = plan_route(src, dst, tonnes, 0, 0, 1)

            if not eco or not fast:
                st.error("No valid route found between selected hubs.")
            else:
                saved_co2 = fast["co2"] - eco["co2"]
                co2_pct_saved = (saved_co2 / fast["co2"] * 100) if fast["co2"] else 0
                cost_diff = eco["cost"] - fast["cost"]
                time_diff = eco["time"] - fast["time"]

                # High-level Metrics
                st.subheader("Optimization Impact")
                m1, m2, m3 = st.columns(3)
                m1.metric("CO₂ Reduction", f"{saved_co2:,.0f} kg", f"-{co2_pct_saved:.1f}%")
                m2.metric("Cost Impact", f"Rs {abs(cost_diff):,.0f}", f"{'-' if cost_diff <= 0 else '+'}")
                m3.metric("Transit Duration", f"{eco['time']:.1f} hrs", f"+{time_diff:.1f} hrs")

                st.divider()

                # Detailed comparisons
                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("### ✈️ Baseline: Speed-Only Plan")
                    st.markdown(f"**Route:** `{' ➔ '.join(fast['path'])}`")
                    st.write(f"- **Transit Time:** {fast['time']:.1f} hrs")
                    st.write(f"- **Cost:** Rs {fast['cost']:,.0f}")
                    st.write(f"- **CO₂ Emissions:** {fast['co2']:,.0f} kg")
                    st.markdown("**Leg Breakdown:**")
                    for a, b, km, mode in fast["legs"]:
                        st.write(f"- `{a}` to `{b}` ({km} km) via **{mode}**")

                with c2:
                    st.markdown("### 🌿 Optimized EcoTransit Plan")
                    st.markdown(f"**Route:** `{' ➔ '.join(eco['path'])}`")
                    st.write(f"- **Transit Time:** {eco['time']:.1f} hrs")
                    st.write(f"- **Cost:** Rs {eco['cost']:,.0f}")
                    st.write(f"- **CO₂ Emissions:** {eco['co2']:,.0f} kg")
                    st.markdown("**Leg Breakdown:**")
                    for a, b, km, mode in eco["legs"]:
                        st.write(f"- `{a}` to `{b}` ({km} km) via **{mode}**")
