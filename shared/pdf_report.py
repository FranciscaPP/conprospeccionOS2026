"""Generación del PDF del Reporte Mensual (fpdf2 — Python puro, corre en Streamlit Cloud)."""
from fpdf import FPDF

from shared.kpis import KPI_LABEL

GBS_PURPLE = (124, 58, 237)
DARK       = (30, 41, 59)
GREY       = (100, 116, 139)
BORDER     = (221, 214, 254)
BG         = (250, 245, 255)


def _lat(s) -> str:
    """fpdf2 con fuentes core usa latin-1: reemplaza caracteres fuera de rango."""
    return (str(s).replace("—", "-").replace("–", "-").replace("→", "->")
            .encode("latin-1", "replace").decode("latin-1"))


def construir_pdf(cliente_nombre: str, periodo: str, seleccion: list[str], comp: dict) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Banda superior morada
    pdf.set_fill_color(*GBS_PURPLE)
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(14, 8)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 9, _lat(f"Reporte Mensual - {cliente_nombre}"), ln=1)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, _lat(f"Periodo: {periodo}"), ln=1)

    # Tarjetas KPI (grid 2 columnas)
    x0, y0 = 14, 42
    col_w, gap, row_h = 90, 8, 28
    for i, kid in enumerate(seleccion):
        valor, sub = comp.get(kid, ("-", ""))
        row, col = divmod(i, 2)
        x = x0 + col * (col_w + gap)
        y = y0 + row * (row_h + 6)
        pdf.set_draw_color(*BORDER)
        pdf.set_fill_color(*BG)
        pdf.rect(x, y, col_w, row_h, "DF")
        pdf.set_xy(x + 5, y + 4)
        pdf.set_text_color(*GREY)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w - 10, 4, _lat(KPI_LABEL.get(kid, kid).upper()), ln=2)
        pdf.set_x(x + 5)
        pdf.set_text_color(*GBS_PURPLE)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(col_w - 10, 9, _lat(valor), ln=2)
        pdf.set_x(x + 5)
        pdf.set_text_color(*GREY)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(col_w - 10, 4, _lat(sub))

    # Pie
    pdf.set_y(-16)
    pdf.set_text_color(*GREY)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 6, _lat("Powered by Conprospeccion - Confidencial"), align="C")

    out = pdf.output()
    return bytes(out)
