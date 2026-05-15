"""May Budget Diff — Slush Fund dashboard.

Shows line-by-line May FC changes (true original vs current paid marketing budget)
across Havenly, Burrow, Citizenry, and Interior Define. Positive amounts =
savings cut; negative amounts = added spend. Net per brand at the top.

Multi-user shared deploy. Storage: Turso (libSQL). No password (fully public).
"""

from __future__ import annotations

import streamlit as st

import db


# ---------------------------------------------------------------------------
# Page config + theme
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="May Budget Diff — Slush Fund",
    page_icon="💰",
    layout="wide",
)

st.markdown(
    """
    <style>
      .rts-title { font-size: 32px; font-weight: 800; letter-spacing: -0.5px; margin: 0; }
      .rts-sub { color: #94a3b8; margin: 4px 0 16px; font-size: 14px; }
      .rts-total-card {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: #042f24;
        padding: 18px 22px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(16,185,129,0.35);
        text-align: right;
      }
      .rts-total-card.negative {
        background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
        color: #2a0a0a;
        box-shadow: 0 10px 30px rgba(248,113,113,0.35);
      }
      .rts-total-label {
        font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px;
        font-weight: 700; opacity: 0.85;
      }
      .rts-total-value { font-size: 32px; font-weight: 800; letter-spacing: -1px; line-height: 1.1; margin-top: 2px; }
      .rts-total-meta { font-size: 13px; opacity: 0.85; margin-top: 2px; font-weight: 600; }

      .rts-section-title {
        font-size: 13px; color: #94a3b8; font-weight: 700;
        text-transform: uppercase; letter-spacing: 1px;
        margin: 8px 0 12px;
      }

      .rts-brand-head {
        display: flex; justify-content: space-between; align-items: baseline;
        padding-bottom: 4px; margin-top: 8px;
      }
      .rts-brand-name { font-size: 20px; font-weight: 700; margin: 0; }
      .rts-brand-net { font-size: 20px; font-weight: 800; font-variant-numeric: tabular-nums; }
      .rts-brand-net.pos { color: #10b981; }
      .rts-brand-net.neg { color: #f87171; }
      .rts-brand-net .sub { display: block; font-size: 10px; font-weight: 600; color: #94a3b8;
        text-transform: uppercase; letter-spacing: 1px; text-align: right; }
    </style>
    """,
    unsafe_allow_html=True,
)


BRANDS = ["Havenly", "Burrow", "Citizenry", "Interior Define"]


def fmt_signed(n: float) -> str:
    n = float(n or 0)
    sign = "-" if n < 0 else ""
    return f"{sign}${abs(int(round(n))):,}"


def fmt_with_plus(n: float) -> str:
    n = float(n or 0)
    if n >= 0:
        return f"+${int(round(n)):,}"
    return f"-${abs(int(round(n))):,}"


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
items = db.list_items()


def brand_cuts(brand: str) -> float:
    return sum(it["amount"] for it in items if it["brand"] == brand and it["amount"] > 0)


def brand_adds(brand: str) -> float:
    return sum(it["amount"] for it in items if it["brand"] == brand and it["amount"] < 0)


def brand_net(brand: str) -> float:
    return brand_cuts(brand) + brand_adds(brand)


grand_total = sum(brand_net(b) for b in BRANDS)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
header_l, header_r = st.columns([3, 2])
with header_l:
    st.markdown('<div class="rts-title">💰 May Budget Diff — Slush Fund</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rts-sub">May FC (true original) vs May FC (current). '
        '<span style="color:#10b981;">Green</span> = cut/savings, '
        '<span style="color:#f87171;">red</span> = added spend.</div>',
        unsafe_allow_html=True,
    )
with header_r:
    n_brands = len({it["brand"] for it in items})
    card_class = "rts-total-card negative" if grand_total < 0 else "rts-total-card"
    st.markdown(
        f"""
        <div class="{card_class}">
          <div class="rts-total-label">Total net May savings</div>
          <div class="rts-total-value">{fmt_with_plus(grand_total)}</div>
          <div class="rts-total-meta">{len(items)} item{'s' if len(items) != 1 else ''} · {n_brands} brands</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Brand summary table
# ---------------------------------------------------------------------------
st.markdown('<div class="rts-section-title">📊 Net May change by brand</div>', unsafe_allow_html=True)

import pandas as pd

summary_rows = []
for b in BRANDS:
    cuts = brand_cuts(b)
    adds = brand_adds(b)
    net = cuts + adds
    if cuts == 0 and adds == 0:
        continue
    summary_rows.append({
        "Brand": b,
        "Cuts": cuts,
        "Added": adds,
        "Net": net,
    })

if summary_rows:
    total_cuts = sum(r["Cuts"] for r in summary_rows)
    total_adds = sum(r["Added"] for r in summary_rows)
    summary_rows.append({
        "Brand": "Total",
        "Cuts": total_cuts,
        "Added": total_adds,
        "Net": total_cuts + total_adds,
    })
    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(
        summary_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Brand": st.column_config.TextColumn("Brand"),
            "Cuts": st.column_config.NumberColumn("Cuts", format="$%d"),
            "Added": st.column_config.NumberColumn("Added", format="$%d"),
            "Net": st.column_config.NumberColumn("Net", format="$%d"),
        },
    )

st.divider()


# ---------------------------------------------------------------------------
# Add form
# ---------------------------------------------------------------------------
st.markdown('<div class="rts-section-title">➕ Add a line item</div>', unsafe_allow_html=True)

with st.form("add_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        new_brand = st.selectbox("Brand", options=BRANDS)
        new_type = st.selectbox("Type", options=["Cut (savings)", "Added (new spend)"])
    with c2:
        new_channel = st.text_input("Channel / Line item", placeholder="e.g., Pinterest")
        new_summary = st.text_area("Summary (optional)", placeholder="What changed?", height=80)
    with c3:
        new_amount = st.number_input("Amount $ (absolute, no sign)", min_value=0.0, step=100.0, value=0.0)
    submitted = st.form_submit_button("Add", type="primary")

if submitted:
    if not new_channel.strip():
        st.error("Channel is required.")
    elif new_amount <= 0:
        st.error("Amount must be greater than 0.")
    else:
        signed_amount = float(new_amount) if new_type.startswith("Cut") else -float(new_amount)
        db.add_item(
            brand=new_brand,
            channel=new_channel.strip(),
            amount=signed_amount,
            summary=new_summary.strip(),
        )
        st.success(f"Added {new_channel.strip()} ({fmt_with_plus(signed_amount)}) to {new_brand}.")
        st.rerun()

st.divider()


# ---------------------------------------------------------------------------
# Per-brand editable line items
# ---------------------------------------------------------------------------
for brand in BRANDS:
    brand_items = [it for it in items if it["brand"] == brand]
    if not brand_items:
        continue

    net = brand_net(brand)
    net_class = "pos" if net >= 0 else "neg"
    st.markdown(
        f"""
        <div class="rts-brand-head">
          <h3 class="rts-brand-name">{brand}</h3>
          <div class="rts-brand-net {net_class}">{fmt_with_plus(net)}
            <span class="sub">net May change</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sort: cuts first (descending), then adds (most-negative first)
    brand_items.sort(key=lambda it: (it["amount"] <= 0, -abs(it["amount"])))

    df = pd.DataFrame(brand_items)
    df["Type"] = df["amount"].apply(lambda x: "Cut" if x > 0 else "Added")
    df["Delete?"] = False
    df = df[["id", "Type", "channel", "amount", "summary", "Delete?"]]
    df = df.rename(columns={
        "channel": "Channel / Line item",
        "amount": "Amount $ (signed)",
        "summary": "Summary",
    })

    edited = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "id": None,
            "Type": st.column_config.TextColumn("Type", disabled=True, width="small"),
            "Channel / Line item": st.column_config.TextColumn("Channel / Line item", required=True),
            "Amount $ (signed)": st.column_config.NumberColumn(
                "Amount $ (signed)",
                format="$%d",
                help="Positive = cut/savings. Negative = added spend.",
            ),
            "Summary": st.column_config.TextColumn("Summary"),
            "Delete?": st.column_config.CheckboxColumn("Delete?", help="Tick + click Apply"),
        },
        num_rows="fixed",
        key=f"editor_{brand}",
    )

    if st.button(f"Apply changes — {brand}", key=f"apply_{brand}"):
        changes = 0
        deletes = 0
        original_by_id = {it["id"]: it for it in brand_items}
        for _, row in edited.iterrows():
            row_id = row["id"]
            if row.get("Delete?"):
                db.delete_item(row_id)
                deletes += 1
                continue
            orig = original_by_id.get(row_id)
            if not orig:
                continue
            new_channel = (row["Channel / Line item"] or "").strip()
            new_amount = float(row["Amount $ (signed)"] or 0)
            new_summary = row["Summary"] or ""
            if not new_channel:
                st.error("Skipped a row with empty channel.")
                continue
            if (
                new_channel != orig["channel"]
                or new_amount != orig["amount"]
                or new_summary != orig["summary"]
            ):
                db.update_item(
                    row_id,
                    brand=brand,
                    channel=new_channel,
                    amount=new_amount,
                    summary=new_summary,
                )
                changes += 1
        if changes or deletes:
            msg = []
            if changes:
                msg.append(f"updated {changes} item{'s' if changes != 1 else ''}")
            if deletes:
                msg.append(f"deleted {deletes} item{'s' if deletes != 1 else ''}")
            st.success(" • ".join(msg).capitalize() + ".")
            st.rerun()
        else:
            st.info("No changes to apply.")

st.caption("Data is shared via Turso. Anyone with the URL sees and edits the same list.")
