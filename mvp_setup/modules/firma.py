import base64
from pathlib import Path


def imagen_a_base64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read()
        ext = Path(path).suffix.lower().replace(".", "")
        mime = {"svg": "image/svg+xml", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp"}.get(ext, "image/png")
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"
    except Exception:
        return ""


def _logo_tag(logo_path, max_h=50, max_w=180, mb=10):
    if not logo_path:
        return ""
    b64 = imagen_a_base64(str(logo_path))
    if not b64:
        return ""
    return f'<img src="{b64}" alt="logo" style="max-height:{max_h}px;max-width:{max_w}px;display:block;margin-bottom:{mb}px;" />'


def _href(url):
    if not url:
        return ""
    return url if url.startswith("http") else "https://" + url


def _display(url):
    return url.replace("https://", "").replace("http://", "").rstrip("/") if url else ""


def _li_icon():
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAAvklEQVQ4je2TsQ3CMBBFnxMFsgdskA2ywQaMwAaswAaMwAaMkA0YgQ0YgQ0YISVSJCTkc4EUKRIg7g5+0p3u3n/2WZIkSZIkSZIk/SVJKSU5RES+qlVV1cx+gBVQgHdgDRTAFbgDS+C5AZxzznX3gKqqqr2ZmZmZ2dLMFh/oAJxzzjVgZgDMzDlX3XsAoLUGQEScAAAAAElFTkSuQmCC"


# ─── PLANTILLA 1: Clásica ────────────────────────────────────────────────────
def _tpl_clasica(d, logo_path, color1, color2):
    logo = _logo_tag(logo_path, 50, 180, 10)
    web_href = _href(d.get("web", ""))
    web_disp = _display(web_href)
    li_href  = _href(d.get("linkedin", ""))
    tw_href  = _href(d.get("twitter", ""))
    addr     = d.get("direccion", "")

    rows = ""
    if d.get("email"):
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#444;'>📧 <a href='mailto:{d['email']}' style='color:{color1};text-decoration:none;'>{d['email']}</a></td></tr>"
    if d.get("telefono"):
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#444;'>📞 {d['telefono']}</td></tr>"
    if d.get("movil"):
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#444;'>📱 {d['movil']}</td></tr>"
    if web_href:
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#444;'>🌐 <a href='{web_href}' style='color:{color1};text-decoration:none;'>{web_disp}</a></td></tr>"
    if li_href:
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#444;'>🔗 <a href='{li_href}' style='color:{color1};text-decoration:none;'>LinkedIn</a></td></tr>"
    if tw_href:
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#444;'>𝕏 <a href='{tw_href}' style='color:{color1};text-decoration:none;'>Twitter / X</a></td></tr>"
    if addr:
        rows += f"<tr><td style='padding:2px 0;font-size:11px;color:#888;'>📍 {addr}</td></tr>"

    empresa = f"<p style='margin:0 0 6px 0;font-size:11px;font-weight:600;color:{color1};letter-spacing:0.5px;text-transform:uppercase;'>{d.get('empresa','')}</p>" if d.get("empresa") else ""

    return f"""<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;max-width:520px;font-family:Arial,Helvetica,sans-serif;">
  <tr>
    <td style="border-left:4px solid {color1};padding:14px 18px;vertical-align:top;">
      {logo}
      {empresa}
      <p style="margin:0 0 1px 0;font-size:15px;font-weight:700;color:#111;">{d.get('nombre','')}</p>
      <p style="margin:0 0 10px 0;font-size:12px;color:{color2};">{d.get('cargo','')}</p>
      <table cellpadding="0" cellspacing="0" border="0">{rows}</table>
    </td>
  </tr>
</table>"""


# ─── PLANTILLA 2: Horizontal Pro ────────────────────────────────────────────
def _tpl_horizontal(d, logo_path, color1, color2):
    logo = _logo_tag(logo_path, 55, 160, 0)
    web_href = _href(d.get("web", ""))
    web_disp = _display(web_href)
    li_href  = _href(d.get("linkedin", ""))
    tw_href  = _href(d.get("twitter", ""))

    info_items = []
    if d.get("email"):
        info_items.append(f"<a href='mailto:{d['email']}' style='color:{color1};text-decoration:none;font-size:12px;'>{d['email']}</a>")
    if d.get("telefono"):
        info_items.append(f"<span style='color:#555;font-size:12px;'>{d['telefono']}</span>")
    if d.get("movil"):
        info_items.append(f"<span style='color:#555;font-size:12px;'>{d['movil']}</span>")
    if web_href:
        info_items.append(f"<a href='{web_href}' style='color:{color1};text-decoration:none;font-size:12px;'>{web_disp}</a>")

    social = ""
    if li_href:
        social += f" &nbsp;<a href='{li_href}' style='color:{color1};font-size:12px;text-decoration:none;'>LinkedIn</a>"
    if tw_href:
        social += f" &nbsp;<a href='{tw_href}' style='color:{color1};font-size:12px;text-decoration:none;'>Twitter/X</a>"

    info_html = " &nbsp;|&nbsp; ".join(info_items)

    empresa = d.get("empresa", "")

    return f"""<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;max-width:580px;font-family:Arial,Helvetica,sans-serif;">
  <tr>
    <td style="padding:12px 20px 12px 12px;vertical-align:middle;width:170px;">
      {logo if logo else f'<p style="margin:0;font-size:13px;font-weight:700;color:{color1};">{empresa}</p>'}
    </td>
    <td style="border-left:1px solid #e0e0e0;padding:12px 0 12px 20px;vertical-align:middle;">
      <p style="margin:0 0 1px 0;font-size:15px;font-weight:700;color:#111;">{d.get('nombre','')}</p>
      <p style="margin:0 0 2px 0;font-size:12px;color:{color2};">{d.get('cargo','')}{(' &nbsp;·&nbsp; ' + empresa) if empresa and not logo else ''}</p>
      <p style="margin:4px 0 0 0;">{info_html}</p>
      {f'<p style="margin:3px 0 0 0;">{social.strip()}</p>' if social.strip() else ''}
    </td>
  </tr>
  <tr><td colspan="2" style="padding-top:0;"><div style="height:3px;background:linear-gradient(90deg,{color1},{color2});border-radius:2px;"></div></td></tr>
</table>"""


# ─── PLANTILLA 3: Moderna con banner ────────────────────────────────────────
def _tpl_moderna(d, logo_path, color1, color2):
    logo = _logo_tag(logo_path, 40, 140, 0)
    web_href = _href(d.get("web", ""))
    web_disp = _display(web_href)
    li_href  = _href(d.get("linkedin", ""))
    tw_href  = _href(d.get("twitter", ""))
    addr     = d.get("direccion", "")

    contact_pills = ""
    if d.get("email"):
        contact_pills += f"<a href='mailto:{d['email']}' style='display:inline-block;margin:2px 4px 2px 0;padding:3px 10px;background:#f1f5f9;border-radius:20px;font-size:11px;color:{color1};text-decoration:none;'>✉ {d['email']}</a>"
    if d.get("telefono"):
        contact_pills += f"<span style='display:inline-block;margin:2px 4px 2px 0;padding:3px 10px;background:#f1f5f9;border-radius:20px;font-size:11px;color:#555;'>📞 {d['telefono']}</span>"
    if d.get("movil"):
        contact_pills += f"<span style='display:inline-block;margin:2px 4px 2px 0;padding:3px 10px;background:#f1f5f9;border-radius:20px;font-size:11px;color:#555;'>📱 {d['movil']}</span>"
    if web_href:
        contact_pills += f"<a href='{web_href}' style='display:inline-block;margin:2px 4px 2px 0;padding:3px 10px;background:#f1f5f9;border-radius:20px;font-size:11px;color:{color1};text-decoration:none;'>🌐 {web_disp}</a>"
    if li_href:
        contact_pills += f"<a href='{li_href}' style='display:inline-block;margin:2px 4px 2px 0;padding:3px 10px;background:{color1};border-radius:20px;font-size:11px;color:#fff;text-decoration:none;'>in LinkedIn</a>"
    if tw_href:
        contact_pills += f"<a href='{tw_href}' style='display:inline-block;margin:2px 4px 2px 0;padding:3px 10px;background:#000;border-radius:20px;font-size:11px;color:#fff;text-decoration:none;'>𝕏 Twitter</a>"
    if addr:
        contact_pills += f"<span style='display:block;margin-top:6px;font-size:11px;color:#888;'>📍 {addr}</span>"

    logo_cell = f"<td style='padding-right:14px;vertical-align:middle;'>{logo}</td><td style='border-left:1px solid rgba(255,255,255,0.3);padding-left:14px;vertical-align:middle;'>" if logo else "<td>"

    return f"""<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;max-width:520px;font-family:Arial,Helvetica,sans-serif;">
  <tr>
    <td style="background:linear-gradient(135deg,{color1},{color2});border-radius:10px 10px 0 0;padding:14px 18px;">
      <table cellpadding="0" cellspacing="0" border="0"><tr>
        {logo_cell}
          <p style="margin:0 0 1px 0;font-size:15px;font-weight:700;color:#fff;">{d.get('nombre','')}</p>
          <p style="margin:0;font-size:12px;color:rgba(255,255,255,0.85);">{d.get('cargo','')}{(' · ' + d.get('empresa','')) if d.get('empresa') else ''}</p>
        </td>
      </tr></table>
    </td>
  </tr>
  <tr>
    <td style="background:#fff;border:1px solid #e8ecf0;border-top:none;border-radius:0 0 10px 10px;padding:12px 18px;">
      {contact_pills}
    </td>
  </tr>
</table>"""


# ─── PLANTILLA 4: Minimalista ────────────────────────────────────────────────
def _tpl_minimalista(d, logo_path, color1, color2):
    logo = _logo_tag(logo_path, 35, 130, 8)
    web_href = _href(d.get("web", ""))
    web_disp = _display(web_href)
    li_href  = _href(d.get("linkedin", ""))

    partes = []
    if d.get("email"):
        partes.append(f"<a href='mailto:{d['email']}' style='color:{color1};text-decoration:none;'>{d['email']}</a>")
    if d.get("telefono"):
        partes.append(f"<span style='color:#666;'>{d['telefono']}</span>")
    if d.get("movil"):
        partes.append(f"<span style='color:#666;'>{d['movil']}</span>")
    if web_href:
        partes.append(f"<a href='{web_href}' style='color:{color1};text-decoration:none;'>{web_disp}</a>")
    if li_href:
        partes.append(f"<a href='{li_href}' style='color:{color1};text-decoration:none;'>LinkedIn</a>")

    sep = f" <span style='color:#ccc;'>|</span> "
    contact_line = sep.join(partes)

    return f"""<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;max-width:500px;font-family:Georgia,serif;">
  <tr>
    <td style="padding:12px 0;border-top:2px solid {color1};border-bottom:1px solid #e8e8e8;">
      {logo}
      <p style="margin:0 0 1px 0;font-size:14px;font-weight:700;color:#111;font-family:Arial,sans-serif;">{d.get('nombre','')}</p>
      <p style="margin:0 0 8px 0;font-size:12px;color:{color2};font-family:Arial,sans-serif;">{d.get('cargo','')}{(' — ' + d.get('empresa','')) if d.get('empresa') else ''}</p>
      <p style="margin:0;font-size:11px;line-height:1.8;">{contact_line}</p>
    </td>
  </tr>
</table>"""


# ─── PLANTILLA 5: Dos columnas con foto/iniciales ────────────────────────────
def _tpl_dos_columnas(d, logo_path, color1, color2):
    logo = _logo_tag(logo_path, 50, 150, 8)
    web_href = _href(d.get("web", ""))
    web_disp = _display(web_href)
    li_href  = _href(d.get("linkedin", ""))
    tw_href  = _href(d.get("twitter", ""))
    addr     = d.get("direccion", "")

    iniciales = "".join(p[0].upper() for p in d.get("nombre", "AB").split()[:2])

    rows = ""
    if d.get("email"):
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#444;'>✉ <a href='mailto:{d['email']}' style='color:{color1};text-decoration:none;'>{d['email']}</a></td></tr>"
    if d.get("telefono"):
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#555;'>☎ {d['telefono']}</td></tr>"
    if d.get("movil"):
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#555;'>📱 {d['movil']}</td></tr>"
    if web_href:
        rows += f"<tr><td style='padding:2px 0;font-size:12px;color:#555;'>🌐 <a href='{web_href}' style='color:{color1};text-decoration:none;'>{web_disp}</a></td></tr>"
    if addr:
        rows += f"<tr><td style='padding:2px 0;font-size:11px;color:#888;'>📍 {addr}</td></tr>"

    social = ""
    if li_href:
        social += f"<a href='{li_href}' style='display:inline-block;background:{color1};color:#fff;font-size:10px;font-weight:700;padding:4px 10px;border-radius:4px;text-decoration:none;margin-right:4px;'>in</a>"
    if tw_href:
        social += f"<a href='{tw_href}' style='display:inline-block;background:#000;color:#fff;font-size:10px;font-weight:700;padding:4px 10px;border-radius:4px;text-decoration:none;'>𝕏</a>"

    return f"""<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;max-width:540px;font-family:Arial,Helvetica,sans-serif;">
  <tr>
    <td style="padding:14px 16px 14px 0;vertical-align:top;width:70px;">
      <div style="width:60px;height:60px;border-radius:50%;background:{color1};display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;color:#fff;text-align:center;line-height:60px;">{iniciales}</div>
    </td>
    <td style="padding:14px 0 14px 16px;border-left:1px solid #e8ecf0;vertical-align:top;">
      <p style="margin:0 0 1px 0;font-size:15px;font-weight:700;color:#111;">{d.get('nombre','')}</p>
      <p style="margin:0 0 2px 0;font-size:12px;color:{color2};">{d.get('cargo','')}</p>
      {f'<p style="margin:0 0 8px 0;font-size:11px;color:#888;">{d.get("empresa","")}</p>' if d.get("empresa") else '<div style="margin-bottom:8px;"></div>'}
      {logo if logo else ''}
      <table cellpadding="0" cellspacing="0" border="0">{rows}</table>
      {f'<div style="margin-top:8px;">{social}</div>' if social else ''}
    </td>
  </tr>
</table>"""


PLANTILLAS = {
    "Clásica (barra lateral)":      _tpl_clasica,
    "Horizontal Pro":                _tpl_horizontal,
    "Moderna con banner":            _tpl_moderna,
    "Minimalista":                   _tpl_minimalista,
    "Dos columnas con iniciales":    _tpl_dos_columnas,
}


def generar_firma_html(datos: dict, logo_path: str = None, plantilla: str = "Clásica (barra lateral)") -> str:
    color1 = datos.get("color_marca", "#1a56db")
    color2 = datos.get("color_secundario", "#64748b")
    fn = PLANTILLAS.get(plantilla, _tpl_clasica)
    body = fn(datos, logo_path, color1, color2)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;">{body}</body>
</html>"""


def generar_firma_texto(datos: dict) -> str:
    lineas = [f"--\n{datos.get('nombre_prospector', datos.get('nombre', ''))}"]
    for k in ("cargo", "email", "telefono", "movil", "web", "empresa"):
        v = datos.get(k, "")
        if v:
            lineas.append(v)
    return "\n".join(lineas)
