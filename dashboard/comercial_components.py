"""Componentes Streamlit reutilizables para el modulo Comercial."""
from __future__ import annotations

from html import escape
from typing import Any, Iterable

import pandas as pd
import streamlit as st

from shared.cp_design import (
    CP_BG,
    CP_BLUE,
    CP_BLUE_BG,
    CP_CARBON,
    CP_GOLD,
    CP_GOLD_SOFT,
    CP_GRAY_BG,
    CP_GREEN,
    CP_GREEN_BG,
    CP_INK,
    CP_LINE,
    CP_LINE_STRONG,
    CP_MUTED,
    CP_MUTED_SURFACE,
    CP_ORANGE,
    CP_ORANGE_BG,
    CP_PURPLE,
    CP_PURPLE_BG,
    CP_RED,
    CP_RED_BG,
    FONT_BODY,
    FONT_HEAD,
    FONT_IMPORT,
)
from shared.comercial import money


STATE_COLORS = {
    "Reunion agendada": (CP_BLUE, CP_BLUE_BG),
    "Preparacion pendiente": (CP_ORANGE, CP_ORANGE_BG),
    "Preparacion lista": (CP_GREEN, CP_GREEN_BG),
    "Reunion realizada": (CP_BLUE, CP_BLUE_BG),
    "Diagnostico procesado": (CP_PURPLE, CP_PURPLE_BG),
    "Investigacion de mercado": (CP_PURPLE, CP_PURPLE_BG),
    "Propuesta en preparacion": (CP_ORANGE, CP_ORANGE_BG),
    "Propuesta enviada": (CP_BLUE, CP_BLUE_BG),
    "En seguimiento": (CP_ORANGE, CP_ORANGE_BG),
    "Aceptada": (CP_GREEN, CP_GREEN_BG),
    "Perdida": (CP_RED, CP_RED_BG),
    "Pausada": (CP_GRAY_BG, CP_MUTED_SURFACE),
}


def inject_commercial_css() -> None:
    st.markdown(
        f"""
<style>
{FONT_IMPORT}
.block-container {{
  max-width: 1320px;
  padding-top: 1rem !important;
}}
.cp-commercial-shell {{
  font-family: {FONT_BODY};
  color: {CP_INK};
}}
.cp-commercial-hero {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:18px;
  background:{CP_CARBON};
  color:#fff;
  border-radius:12px;
  padding:18px 22px;
  margin-bottom:16px;
  border:1px solid #242424;
}}
.cp-commercial-hero h1 {{
  font-family:{FONT_HEAD};
  font-size:25px;
  margin:0;
  line-height:1.1;
}}
.cp-commercial-hero p {{
  color:#D8D8D5;
  font-size:12px;
  margin:6px 0 0;
  line-height:1.45;
}}
.cp-hero-mark {{
  background:#fff;
  border:1px solid {CP_LINE};
  border-radius:8px;
  color:{CP_INK};
  font-weight:900;
  padding:9px 11px;
  white-space:nowrap;
}}
.cp-grid {{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px;
}}
.cp-module-grid {{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:14px;
  margin:14px 0 18px;
}}
.cp-module-card {{
  background:#fff;
  border:1px solid {CP_LINE};
  border-radius:8px;
  padding:18px 20px;
  min-height:176px;
}}
.cp-module-card h3 {{
  margin:0 0 12px;
  color:{CP_INK};
  font-size:17px;
  line-height:1.2;
}}
.cp-module-card p {{
  margin:0;
  color:{CP_MUTED};
  font-size:13px;
  line-height:1.55;
}}
.cp-module-pill {{
  display:inline-flex;
  margin-top:16px;
  border-radius:999px;
  padding:5px 10px;
  background:{CP_GOLD_SOFT};
  border:1px solid #F0D28D;
  color:{CP_INK};
  font-size:11px;
  font-weight:850;
}}
.cp-action-row {{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:14px;
  margin-bottom:14px;
}}
.cp-table-note {{
  color:{CP_MUTED};
  font-size:12px;
  margin:5px 0 10px;
}}
.cp-board {{
  display:grid;
  grid-template-columns:repeat(4,minmax(260px,1fr));
  gap:14px;
  margin-top:14px;
}}
.cp-column {{
  background:{CP_MUTED_SURFACE};
  border:1px solid {CP_LINE};
  border-radius:8px;
  padding:12px;
  min-height:360px;
}}
.cp-column-title {{
  background:#fff;
  border:1px solid {CP_LINE_STRONG};
  border-radius:8px;
  padding:12px 14px;
  margin-bottom:12px;
  color:{CP_INK};
  font-size:15px;
  font-weight:900;
  box-shadow:inset 4px 0 0 var(--stage-color, {CP_GOLD});
}}
.cp-opp-card {{
  background:#fff;
  border:1px solid {CP_LINE};
  border-radius:8px;
  padding:13px 14px;
  margin-bottom:10px;
}}
.cp-opp-card:hover {{
  border-color:{CP_GOLD};
  background:#FFFDF0;
}}
.cp-opp-top {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:8px;
  margin-bottom:10px;
}}
.cp-opp-tags {{
  display:flex;
  flex-wrap:wrap;
  gap:6px;
  min-width:0;
}}
.cp-opp-title {{
  color:{CP_INK};
  font-size:15px;
  font-weight:900;
  line-height:1.25;
  margin:4px 0 6px;
}}
.cp-opp-sub {{
  color:{CP_MUTED};
  font-size:12px;
  line-height:1.4;
  margin-bottom:8px;
}}
.cp-opp-meta {{
  color:#4B4B49;
  display:grid;
  gap:4px;
  font-size:11px;
}}
.cp-opp-meta b {{
  color:{CP_INK};
}}
.cp-mini-pill {{
  align-items:center;
  border:1px solid {CP_LINE};
  border-radius:7px;
  color:{CP_INK};
  display:inline-flex;
  font-size:11px;
  font-weight:850;
  min-height:26px;
  padding:4px 9px;
  background:#fff;
}}
.cp-mini-pill.gold {{
  background:{CP_GOLD_SOFT};
  border-color:#F0D28D;
  color:{CP_INK};
}}
.cp-mini-pill.blue {{
  background:{CP_BLUE_BG};
  border-color:{CP_BLUE}33;
  color:{CP_BLUE};
}}
.cp-mini-pill.green {{
  background:{CP_GREEN_BG};
  border-color:{CP_GREEN}33;
  color:{CP_GREEN};
}}
.cp-mini-pill.orange {{
  background:{CP_ORANGE_BG};
  border-color:{CP_ORANGE}33;
  color:{CP_ORANGE};
}}
.cp-kpi {{
  background:#fff;
  border:1px solid {CP_LINE};
  border-radius:8px;
  padding:12px 13px;
  min-height:82px;
}}
.cp-kpi label {{
  display:block;
  color:{CP_MUTED};
  font-size:10px;
  font-weight:800;
  text-transform:uppercase;
  letter-spacing:.03em;
}}
.cp-kpi strong {{
  display:block;
  color:{CP_INK};
  font-family:{FONT_HEAD};
  font-size:22px;
  line-height:1.1;
  margin-top:8px;
}}
.cp-panel {{
  background:#fff;
  border:1px solid {CP_LINE};
  border-radius:8px;
  padding:16px;
  margin-bottom:12px;
}}
.cp-panel h3 {{
  margin:0 0 8px;
  font-family:{FONT_HEAD};
  font-size:17px;
  color:{CP_INK};
}}
.cp-panel p {{
  margin:0;
  color:{CP_MUTED};
  font-size:13px;
  line-height:1.55;
}}
.cp-band {{
  background:{CP_GOLD_SOFT};
  border:1px solid #F0D28D;
  border-left:5px solid {CP_GOLD};
  border-radius:8px;
  padding:13px 15px;
  margin-bottom:12px;
  color:{CP_INK};
  font-size:13px;
  line-height:1.5;
}}
.cp-field-grid {{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:8px;
}}
.cp-field {{
  border:1px solid {CP_LINE};
  border-radius:8px;
  padding:10px 11px;
  background:{CP_BG};
  min-height:62px;
}}
.cp-field span {{
  display:block;
  color:{CP_MUTED};
  font-size:10px;
  font-weight:850;
  text-transform:uppercase;
  margin-bottom:5px;
}}
.cp-field b {{
  display:block;
  color:{CP_INK};
  font-size:13px;
  line-height:1.35;
  overflow-wrap:anywhere;
}}
.cp-badge {{
  display:inline-flex;
  align-items:center;
  border-radius:999px;
  padding:4px 9px;
  font-size:11px;
  font-weight:850;
  border:1px solid transparent;
}}
.cp-timeline {{
  display:grid;
  gap:8px;
}}
.cp-event {{
  display:grid;
  grid-template-columns:145px 80px minmax(0,1fr);
  gap:10px;
  align-items:start;
  border:1px solid {CP_LINE};
  border-radius:8px;
  padding:10px 12px;
  background:#fff;
}}
.cp-event small {{
  color:{CP_MUTED};
  font-size:11px;
}}
.cp-event b {{
  font-size:12px;
  color:{CP_INK};
}}
.cp-slide {{
  min-height:430px;
  background:{CP_CARBON};
  color:#fff;
  border-radius:8px;
  padding:26px;
  border:1px solid #242424;
}}
.cp-slide h2 {{
  margin:0;
  color:{CP_GOLD};
  font-family:{FONT_HEAD};
  font-size:30px;
  line-height:1.1;
}}
.cp-slide h3 {{
  margin:13px 0 8px;
  color:#fff;
  font-size:18px;
}}
.cp-slide p {{
  color:#EDECEA;
  font-size:14px;
  line-height:1.55;
}}
.cp-slide-grid {{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
  margin-top:18px;
}}
.cp-slide-card {{
  border:1px solid #5C5C58;
  border-radius:8px;
  padding:13px;
  background:#3C3C39;
}}
.cp-slide-card b {{
  color:{CP_GOLD};
  display:block;
  margin-bottom:6px;
}}
.cp-slide-card span {{
  color:#F4F4F2;
  font-size:12px;
  line-height:1.45;
}}
@media(max-width:1050px) {{
  .cp-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .cp-module-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .cp-action-row {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .cp-board {{ grid-template-columns:repeat(2,minmax(260px,1fr)); }}
  .cp-field-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .cp-slide-grid {{ grid-template-columns:1fr; }}
}}
@media(max-width:720px) {{
  .cp-commercial-hero {{ align-items:flex-start; flex-direction:column; }}
  .cp-grid {{ grid-template-columns:1fr; }}
  .cp-module-grid {{ grid-template-columns:1fr; }}
  .cp-action-row {{ grid-template-columns:1fr; }}
  .cp-board {{ grid-template-columns:1fr; }}
  .cp-field-grid {{ grid-template-columns:1fr; }}
  .cp-event {{ grid-template-columns:1fr; }}
  .cp-slide {{ padding:18px; min-height:auto; }}
  .cp-slide h2 {{ font-size:24px; }}
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, mark: str = "COMERCIAL") -> None:
    st.markdown(
        f"""
<div class="cp-commercial-shell">
  <div class="cp-commercial-hero">
    <div>
      <h1>{escape(title)}</h1>
      <p>{escape(subtitle)}</p>
    </div>
    <div class="cp-hero-mark">{escape(mark)}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def kpi_grid(items: Iterable[tuple[str, str]]) -> None:
    cards = "".join(
        f'<div class="cp-kpi"><label>{escape(label)}</label><strong>{escape(str(value))}</strong></div>'
        for label, value in items
    )
    st.markdown(f'<div class="cp-grid">{cards}</div>', unsafe_allow_html=True)


def module_cards(items: Iterable[dict[str, str]]) -> None:
    cards = []
    for item in items:
        cards.append(
            '<div class="cp-module-card">'
            f'<h3>{escape(item["title"])}</h3>'
            f'<p>{escape(item["body"])}</p>'
            f'<span class="cp-module-pill">{escape(item["pill"])}</span>'
            "</div>"
        )
    st.markdown(f'<div class="cp-module-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def panel(title: str, body: str) -> None:
    st.markdown(
        f'<div class="cp-panel"><h3>{escape(title)}</h3><p>{escape(body)}</p></div>',
        unsafe_allow_html=True,
    )


def band(body: str) -> None:
    st.markdown(f'<div class="cp-band">{escape(body)}</div>', unsafe_allow_html=True)


def badge(value: str) -> str:
    color, bg = STATE_COLORS.get(value, (CP_MUTED, CP_MUTED_SURFACE))
    return (
        f'<span class="cp-badge" style="color:{color};background:{bg};'
        f'border-color:{color}33">{escape(value)}</span>'
    )


def mini_pill(value: str, tone: str = "") -> str:
    tone_class = f" {tone}" if tone else ""
    return f'<span class="cp-mini-pill{tone_class}">{escape(value)}</span>'


def opportunity_card(opp: dict[str, Any]) -> str:
    amount = opportunity_amount = money(0)
    proposals = opp.get("proposals") or []
    current = next((item for item in proposals if item.get("is_current")), proposals[-1] if proposals else None)
    if current:
        amount = f'{money(current.get("monthly_amount"))} mensual'
        if current.get("total_amount"):
            opportunity_amount = money(current.get("total_amount"))
    else:
        amount = "Pendiente"
        opportunity_amount = "Pendiente"
    status = opp.get("status", "Sin estado")
    color, _bg = STATE_COLORS.get(status, (CP_GOLD, CP_GOLD_SOFT))
    tags = "".join(
        [
            mini_pill(opp.get("industry", "Sin industria"), "green"),
            mini_pill(f'Score {opp.get("score", "-")}', "blue"),
        ]
    )
    return f"""
<div class="cp-opp-card" style="border-top:3px solid {color}">
  <div class="cp-opp-top">
    <div class="cp-opp-tags">{tags}</div>
    {badge(status)}
  </div>
  <div class="cp-opp-title">{escape(opp.get("company", "Sin empresa"))}</div>
  <div class="cp-opp-sub">{escape(opp.get("contact", ""))} - {escape(opp.get("role", ""))}</div>
  <div class="cp-opp-meta">
    <span>Reunion: <b>{escape(str(opp.get("meeting_at") or "Pendiente"))}</b></span>
    <span>Propuesta: <b>{escape(amount)}</b></span>
    <span>Total estimado: <b>{escape(str(opportunity_amount))}</b></span>
    <span>Proximo paso: <b>{escape(str(opp.get("next_followup") or "Pendiente"))}</b></span>
    <span>Responsable: <b>{escape(opp.get("owner", "Sin responsable"))}</b></span>
  </div>
</div>
"""


def field_grid(fields: Iterable[tuple[str, Any]]) -> None:
    items = []
    for label, value in fields:
        text = "Pendiente" if value in (None, "") else str(value)
        items.append(
            f'<div class="cp-field"><span>{escape(label)}</span><b>{escape(text)}</b></div>'
        )
    st.markdown(f'<div class="cp-field-grid">{"".join(items)}</div>', unsafe_allow_html=True)


def timeline(events: Iterable[tuple[str, str, str]]) -> None:
    html = []
    for when, origin, title in events:
        html.append(
            f'<div class="cp-event"><small>{escape(when)}</small>'
            f'<b>{escape(origin)}</b><div>{escape(title)}</div></div>'
        )
    st.markdown(f'<div class="cp-timeline">{"".join(html)}</div>', unsafe_allow_html=True)


def presentation_slide(slide: dict[str, Any], dynamic_intro: dict[str, Any] | None = None) -> None:
    dynamic = ""
    if dynamic_intro:
        prep = dynamic_intro.get("preparation", {}).get("content", "")
        dynamic = (
            '<div class="cp-band" style="background:#fff;color:#1A1A1A;margin-top:16px">'
            f'<b>{escape(dynamic_intro.get("company", "Prospecto"))}</b> - '
            f'{escape(dynamic_intro.get("contact", ""))} - '
            f'{escape(dynamic_intro.get("industry", ""))} - '
            f'{escape(dynamic_intro.get("country", ""))}<br>'
            f'{escape(prep)}</div>'
        )
    sections = "".join(
        f'<div class="cp-slide-card"><b>{escape(title)}</b><span>{escape(text)}</span></div>'
        for title, text in slide.get("sections", [])
    )
    st.markdown(
        f"""
<div class="cp-slide">
  <h2>{escape(slide.get("title", ""))}</h2>
  <h3>{escape(slide.get("headline", ""))}</h3>
  <p>{escape(slide.get("body", ""))}</p>
  {dynamic}
  <div class="cp-slide-grid">{sections}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def proposals_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("Aun no hay propuestas para mostrar.")
        return
    view = []
    for row in rows:
        view.append(
            {
                "Empresa": row["company"],
                "Contacto": row["contact"],
                "Version": row["version"],
                "Setup": money(row["setup_amount"]),
                "Mensualidad": money(row["monthly_amount"]),
                "Monto total": money(row["total_amount"]),
                "Margen esperado": f'{row["expected_margin"]}%',
                "Creacion": row["created_at"],
                "Envio": row["sent_at"] or "Pendiente",
                "Vigencia": row["valid_until"],
                "Estado": row["status"],
                "Proximo seguimiento": row["next_followup"],
                "Responsable": row["owner"],
            }
        )
    st.dataframe(pd.DataFrame(view), use_container_width=True, hide_index=True)
