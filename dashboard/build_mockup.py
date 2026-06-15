"""Rebuild previous mockup version."""
import os

with open('dashboard/assets/cp_b64.txt') as f: CP = f.read().strip()
with open('dashboard/assets/trs_b64.txt') as f: TRS = f.read().strip()

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mockup - Portal Reuniones y Validacion - Conprospeccion</title>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700;800;900&family=Barlow+Condensed:wght@600;700;800;900&display=swap" rel="stylesheet">
<style>
:root {
  --gold:       #FFD700;
  --gold-dark:  #C9A800;
  --gold-light: #FFF5A0;
  --carbon:     #333333;
  --carbon-mid: #4a4a4a;
  --carbon-lt:  #5c5c5c;
  --black:      #1a1a1a;
  --white:      #FFFFFF;
  --off-white:  #F8F8F8;
  --border:     #E5E5E5;
  --border-dk:  rgba(255,255,255,0.10);
  --valid:      #22C55E; --valid-lt:   #DCFCE7;
  --invalid:    #EF4444; --invalid-lt: #FEE2E2;
  --reschedule: #F59E0B; --reschedule-lt: #FEF3C7;
  --pending:    #94A3B8; --pending-lt: #F1F5F9;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Rubik', sans-serif; background: var(--off-white); color: var(--carbon); min-height: 100vh; }

.layout { display: flex; min-height: 100vh; }

/* SIDEBAR */
.sidebar { width: 248px; flex-shrink: 0; background: var(--black); display: flex; flex-direction: column; position: sticky; top: 0; height: 100vh; overflow-y: auto; }
.sidebar-brand { padding: 24px 20px 20px; border-bottom: 1px solid var(--border-dk); }
.sidebar-brand .logo-mark { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.sidebar-brand .client-label { font-size: 10px; color: var(--gold); font-weight: 600; letter-spacing: 2px; text-transform: uppercase; margin-top: 6px; }
.sidebar-section { padding: 18px 0 8px; }
.sidebar-section-label { font-size: 9px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: rgba(255,255,255,0.25); padding: 0 20px; margin-bottom: 4px; }
.nav-item { display: flex; align-items: center; gap: 11px; padding: 11px 20px; color: rgba(255,255,255,0.50); font-size: 13px; font-weight: 500; cursor: pointer; border-left: 3px solid transparent; transition: all .15s ease; text-decoration: none; }
.nav-item:hover { color: var(--white); background: rgba(255,255,255,0.04); }
.nav-item.active { color: var(--gold); border-left-color: var(--gold); background: rgba(255,215,0,0.06); font-weight: 600; }
.nav-icon { font-size: 15px; flex-shrink: 0; }
.sidebar-footer { margin-top: auto; padding: 16px 20px; border-top: 1px solid var(--border-dk); }
.sidebar-footer .sync-pill { display: flex; align-items: center; gap: 6px; background: rgba(255,215,0,0.08); border-radius: 6px; padding: 7px 10px; font-size: 11px; color: rgba(255,255,255,0.50); }
.sync-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--valid); flex-shrink: 0; }

/* MAIN */
.main { flex: 1; padding: 28px 32px 40px; max-width: 1100px; }

/* HEADER */
.portal-header { background: var(--carbon); border-radius: 14px; padding: 22px 28px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; }
.header-left { display: flex; align-items: center; gap: 16px; }
.client-logo-box { background: #fff; padding: 8px 16px; border-radius: 10px; border: none; width: auto; height: auto; display: flex; align-items: center; }
.header-titles h1 { font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 26px; letter-spacing: 0.3px; color: var(--white); text-transform: uppercase; line-height: 1.1; }
.header-titles p { font-size: 12px; color: rgba(255,255,255,0.45); margin-top: 4px; font-weight: 400; }
.header-right { text-align: right; }
.conprosp-badge { display: inline-block; background: transparent; padding: 0; border: none; }
.header-sync { font-size: 10px; color: rgba(255,255,255,0.30); margin-top: 6px; display: flex; align-items: center; gap: 5px; justify-content: flex-end; }

/* SECTION LABEL */
.section-label { display: flex; align-items: center; gap: 10px; font-family: 'Barlow Condensed', sans-serif; font-size: 12px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--carbon-lt); margin-bottom: 12px; }
.section-label::after { content: ''; flex: 1; height: 1px; background: var(--border); }

/* KPI CARDS DEL MES */
.kpi-grid-main { display: grid; grid-template-columns: repeat(5,1fr); gap: 12px; margin-bottom: 20px; }
.kpi-card-main { background: var(--carbon); border-radius: 12px; padding: 14px 16px; position: relative; overflow: hidden; }
.kpi-card-main::after { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px; }
.kpi-card-main.total::after   { background: var(--gold); }
.kpi-card-main.valida::after  { background: var(--valid); }
.kpi-card-main.novalida::after{ background: var(--invalid); }
.kpi-card-main.reagendar::after{ background: var(--reschedule); }
.kpi-card-main.pendiente::after{ background: var(--pending); }
.kpi-card-main .kpi-icon { font-size: 16px; margin-bottom: 6px; }
.kpi-card-main .kpi-num { font-family: 'Barlow Condensed', sans-serif; font-weight: 900; font-size: 30px; line-height: 1; color: var(--gold); margin-bottom: 4px; }
.kpi-card-main.valida   .kpi-num { color: var(--valid); }
.kpi-card-main.novalida .kpi-num { color: var(--invalid); }
.kpi-card-main.reagendar .kpi-num { color: var(--reschedule); }
.kpi-card-main.pendiente .kpi-num { color: var(--pending); }
.kpi-card-main .kpi-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: rgba(255,255,255,0.40); }

/* KPI ACUMULADOS */
.kpi-grid-sm { display: grid; grid-template-columns: repeat(5,1fr); gap: 10px; margin-bottom: 24px; }
.kpi-card-sm { background: var(--white); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; display: flex; align-items: center; gap: 12px; }
.kpi-card-sm .sm-icon { font-size: 18px; flex-shrink: 0; }
.kpi-card-sm .sm-num { font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 32px; color: var(--carbon); line-height: 1; }
.kpi-card-sm .sm-lbl { font-size: 9px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--pending); margin-top: 1px; }
.kpi-card-sm.valida   .sm-num { color: var(--valid); }
.kpi-card-sm.novalida .sm-num { color: var(--invalid); }
.kpi-card-sm.reagendar .sm-num { color: var(--reschedule); }

/* FILTERS */
.filters-bar { display: flex; align-items: center; gap: 8px; background: var(--white); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; }
.f-label { font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--pending); white-space: nowrap; }
.f-select { border: 1px solid var(--border); border-radius: 7px; padding: 6px 28px 6px 10px; font-size: 13px; font-family: 'Rubik', sans-serif; font-weight: 500; color: var(--carbon); background: var(--off-white); cursor: pointer; outline: none; }
.f-select:focus { border-color: var(--gold); }
.f-divider { width: 1px; height: 22px; background: var(--border); margin: 0 2px; }
.f-spacer { flex: 1; }
.btn-refresh { display: flex; align-items: center; gap: 6px; background: var(--gold); color: var(--black); border: none; border-radius: 8px; padding: 8px 18px; font-family: 'Rubik', sans-serif; font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }
.btn-refresh:hover { background: var(--gold-dark); }

/* SEARCH */
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.search-input { flex: 1; border: 1px solid var(--border); border-radius: 10px; padding: 11px 16px 11px 42px; font-size: 13px; font-family: 'Rubik', sans-serif; color: var(--carbon); background: var(--white) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%2394a3b8' viewBox='0 0 16 16'%3E%3Cpath d='M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398l3.85 3.85a1 1 0 0 0 1.415-1.415zm-5.242 1.156a5 5 0 1 1 0-10 5 5 0 0 1 0 10z'/%3E%3C/svg%3E") no-repeat 14px center; box-shadow: 0 1px 3px rgba(0,0,0,.04); outline: none; }
.search-input:focus { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(255,215,0,.15); }
.btn-search { background: var(--carbon); color: var(--white); border: none; border-radius: 10px; padding: 11px 22px; font-family: 'Rubik', sans-serif; font-size: 13px; font-weight: 700; cursor: pointer; }

/* SEARCH RESULT */
.search-result { background: var(--white); border: 1.5px solid var(--gold); border-radius: 12px; margin-bottom: 20px; overflow: hidden; box-shadow: 0 0 0 4px rgba(255,215,0,0.10); }
.sr-header { background: var(--gold); padding: 9px 16px; font-family: 'Barlow Condensed', sans-serif; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; color: var(--black); text-transform: uppercase; }

/* SECTION HEADER */
.section-header { background: var(--carbon); border-radius: 10px; padding: 12px 20px; margin-bottom: 14px; display: flex; align-items: center; gap: 10px; font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 15px; letter-spacing: 1px; text-transform: uppercase; color: var(--white); }
.section-header .gold-line { width: 4px; height: 18px; background: var(--gold); border-radius: 2px; flex-shrink: 0; }
.section-header .sh-count { margin-left: auto; background: rgba(255,215,0,0.12); border: 1px solid rgba(255,215,0,0.25); color: var(--gold); padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; text-transform: none; font-family: 'Rubik', sans-serif; }

/* MEETING CARD */
.meeting-card { background: var(--white); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 12px; overflow: hidden; border-left: 4px solid var(--border); box-shadow: 0 1px 4px rgba(0,0,0,.05); transition: box-shadow .15s; }
.meeting-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.10); }
.meeting-card.valida    { border-left-color: var(--valid); }
.meeting-card.novalida  { border-left-color: var(--invalid); }
.meeting-card.reagendar { border-left-color: var(--reschedule); }
.meeting-card.pendiente { border-left-color: var(--carbon-lt); }

/* Card top */
.card-top { display: flex; align-items: center; gap: 12px; padding: 10px 18px; background: #FAFAFA; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.card-company-title { font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 17px; color: var(--carbon); letter-spacing: 0.2px; flex: 1; }
.card-datetime { font-size: 12px; color: var(--carbon-lt); font-weight: 500; white-space: nowrap; }
.card-badge { margin-left: auto; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.badge-valida    { background: var(--valid-lt);     color: var(--valid); }
.badge-novalida  { background: var(--invalid-lt);   color: var(--invalid); }
.badge-reagendar { background: var(--reschedule-lt); color: var(--reschedule); }
.badge-pendiente { background: var(--pending-lt);   color: var(--pending); }

/* Card body */
.card-body { display: grid; grid-template-columns: 1fr 1fr; }
.card-col { padding: 14px 18px; border-right: 1px solid var(--border); }
.card-col:last-child { border-right: none; }
.c-name { font-size: 15px; font-weight: 700; color: var(--carbon); margin-bottom: 3px; }
.c-role { font-size: 12px; color: var(--pending); margin-bottom: 8px; }
.c-info { display: flex; flex-direction: column; gap: 2px; }
.c-info span { font-size: 12px; color: var(--carbon-lt); }
.c-industry-tag { display: inline-block; margin-top: 8px; background: var(--off-white); border: 1px solid var(--border); border-radius: 20px; padding: 2px 10px; font-size: 10px; font-weight: 600; color: var(--pending); text-transform: uppercase; letter-spacing: 0.5px; }

/* Right col - validation */
.val-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--pending); margin-bottom: 8px; }
.val-status-sel { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 7px 10px; font-size: 13px; font-family: 'Rubik', sans-serif; color: var(--carbon); background: var(--off-white); cursor: pointer; outline: none; margin-bottom: 8px; }
.val-status-sel:focus { border-color: var(--gold); }
.val-textarea { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 7px 10px; font-size: 13px; font-family: 'Rubik', sans-serif; resize: none; outline: none; color: var(--carbon); background: var(--white); min-height: 60px; }
.val-textarea:focus { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(255,215,0,.12); }
.val-textarea::placeholder { color: #B0B7C3; }
.btn-save { display: block; margin-top: 8px; width: 100%; background: var(--gold); color: var(--black); border: none; border-radius: 8px; padding: 8px 14px; font-family: 'Rubik', sans-serif; font-size: 13px; font-weight: 700; cursor: pointer; }
.btn-save:hover { background: var(--gold-dark); }
</style>
</head>
<body>
<div class="layout">

<!-- SIDEBAR -->
<nav class="sidebar">
  <div class="sidebar-brand">
    <div class="logo-mark">
      <img src="data:image/png;base64,CP_PLACEHOLDER" alt="Conprospeccion" style="height:32px;width:auto;object-fit:contain;display:block;filter:brightness(0) invert(1);">
    </div>
    <div class="client-label">Portal &middot; Tiresias</div>
  </div>
  <div class="sidebar-section">
    <div class="sidebar-section-label">Mi portal</div>
    <a class="nav-item active"><span class="nav-icon">&#128203;</span> Validacion Reuniones</a>
    <a class="nav-item"><span class="nav-icon">&#128202;</span> Mis KPIs</a>
    <a class="nav-item"><span class="nav-icon">&#128197;</span> Calendario</a>
  </div>
  <div class="sidebar-footer">
    <div class="sync-pill">
      <div class="sync-dot"></div>
      Ultima sync: hace 8 min
    </div>
  </div>
</nav>

<!-- MAIN -->
<main class="main">

  <!-- PORTAL HEADER -->
  <div class="portal-header">
    <div class="header-left">
      <div class="client-logo-box">
        <img src="data:image/png;base64,TRS_PLACEHOLDER" alt="Tiresias" style="height:36px;width:auto;object-fit:contain;display:block;">
      </div>
      <div class="header-titles">
        <h1>Portal reuniones y validacion</h1>
        <p>Evalua y registra el estado comercial de cada reunion</p>
      </div>
    </div>
    <div class="header-right">
      <div class="conprosp-badge">
        <img src="data:image/png;base64,CP_PLACEHOLDER" alt="Conprospeccion" style="height:28px;width:auto;object-fit:contain;filter:brightness(0) invert(1);display:block;">
      </div>
      <div class="header-sync">
        <div class="sync-dot"></div>
        Ultima sincronizacion: hace 8 min
      </div>
    </div>
  </div>

  <!-- KPIs DEL MES -->
  <div class="section-label">&#128197; KPIs del mes</div>
  <div class="kpi-grid-main">
    <div class="kpi-card-main total"><div class="kpi-icon">&#128197;</div><div class="kpi-num">14</div><div class="kpi-label">Total reuniones</div></div>
    <div class="kpi-card-main valida"><div class="kpi-icon">&#9989;</div><div class="kpi-num">6</div><div class="kpi-label">Validas</div></div>
    <div class="kpi-card-main novalida"><div class="kpi-icon">&#10060;</div><div class="kpi-num">2</div><div class="kpi-label">No validas</div></div>
    <div class="kpi-card-main reagendar"><div class="kpi-icon">&#128260;</div><div class="kpi-num">3</div><div class="kpi-label">Reagendar</div></div>
    <div class="kpi-card-main pendiente"><div class="kpi-icon">&#9203;</div><div class="kpi-num">3</div><div class="kpi-label">Pendientes</div></div>
  </div>

  <!-- KPIs ACUMULADOS -->
  <div class="section-label">&#128200; Acumulado historico</div>
  <div class="kpi-grid-sm">
    <div class="kpi-card-sm"><div class="sm-icon">&#128197;</div><div><div class="sm-num">47</div><div class="sm-lbl">Total</div></div></div>
    <div class="kpi-card-sm valida"><div class="sm-icon">&#9989;</div><div><div class="sm-num">28</div><div class="sm-lbl">Validas</div></div></div>
    <div class="kpi-card-sm novalida"><div class="sm-icon">&#10060;</div><div><div class="sm-num">11</div><div class="sm-lbl">No validas</div></div></div>
    <div class="kpi-card-sm reagendar"><div class="sm-icon">&#128260;</div><div><div class="sm-num">5</div><div class="sm-lbl">Reagendadas</div></div></div>
    <div class="kpi-card-sm"><div class="sm-icon">&#9203;</div><div><div class="sm-num">3</div><div class="sm-lbl">Pendientes</div></div></div>
  </div>

  <!-- FILTERS -->
  <div class="filters-bar">
    <span class="f-label">Filtrar</span>
    <select class="f-select"><option>Todos los estados</option><option>Valida</option><option>No valida</option><option>Reagendar</option><option>Pendiente</option></select>
    <div class="f-divider"></div>
    <select class="f-select"><option>Todos los meses</option><option>Mayo 2026</option><option>Abril 2026</option></select>
    <div class="f-spacer"></div>
    <button class="btn-refresh">&#8635; Actualizar</button>
  </div>

  <!-- SEARCH -->
  <div class="search-bar">
    <input id="searchInput" class="search-input" type="text" placeholder="Buscar por empresa o contacto..." oninput="if(!this.value.trim())document.getElementById('sr').style.display='none'">
    <button class="btn-search" onclick="if(document.getElementById('searchInput').value.trim())document.getElementById('sr').style.display='block'">Buscar</button>
  </div>
  <div id="sr" style="display:none;" class="search-result">
    <div class="sr-header">&#10003; 1 resultado encontrado</div>
    <div style="padding:12px 16px;font-size:13px;font-weight:600;color:var(--carbon);">SERFONAC &mdash; Pablo Salgado &middot; <span style="color:var(--pending);font-weight:400;">25 mayo &middot; Pendiente</span></div>
  </div>

  <!-- SECTION HEADER -->
  <div class="section-header">
    <div class="gold-line"></div>
    Acumulado Reuniones
    <span class="sh-count">14 este mes</span>
  </div>

  <!-- CARD 1: valida -->
  <div class="meeting-card valida">
    <div class="card-top">
      <span class="card-company-title">SumUp Chile</span>
      <span class="card-datetime">Mie 13 may &middot; 11:30</span>
      <span class="card-badge badge-valida">&#10003; Valida</span>
    </div>
    <div class="card-body">
      <div class="card-col">
        <div class="c-name">Javier Gonzalez Maulen</div>
        <div class="c-role">Gerente Comercial</div>
        <div class="c-info">
          <span>&#9993; jgonzalez@sumup.com</span>
          <span>&#128222; +56 9 8812 3456</span>
        </div>
        <span class="c-industry-tag">Fintech</span>
      </div>
      <div class="card-col">
        <div class="val-label">Validacion comercial</div>
        <select class="val-status-sel"><option selected>&#10003; Reunion valida</option><option>&#10007; No valida</option><option>&#8635; Reagendar</option><option>&#9203; Pendiente</option></select>
        <textarea class="val-textarea">Enviamos propuesta el 26/05, esperamos respuesta esta semana.</textarea>
        <button class="btn-save">&#128190; Guardar</button>
      </div>
    </div>
  </div>

  <!-- CARD 2: no valida -->
  <div class="meeting-card novalida">
    <div class="card-top">
      <span class="card-company-title">Distribuidora Los Andes</span>
      <span class="card-datetime">Mar 19 may &middot; 09:00</span>
      <span class="card-badge badge-novalida">&#10007; No valida</span>
    </div>
    <div class="card-body">
      <div class="card-col">
        <div class="c-name">Carlos Mendoza Rios</div>
        <div class="c-role">Jefe de Logistica</div>
        <div class="c-info">
          <span>&#9993; cmendoza@losandes.cl</span>
          <span>&#128222; +56 9 7723 8801</span>
        </div>
        <span class="c-industry-tag">Distribucion</span>
      </div>
      <div class="card-col">
        <div class="val-label">Validacion comercial</div>
        <select class="val-status-sel"><option>&#10003; Reunion valida</option><option selected>&#10007; No valida</option><option>&#8635; Reagendar</option><option>&#9203; Pendiente</option></select>
        <textarea class="val-textarea">No tenian presupuesto para el trimestre.</textarea>
        <button class="btn-save">&#128190; Guardar</button>
      </div>
    </div>
  </div>

  <!-- CARD 3: reagendar -->
  <div class="meeting-card reagendar">
    <div class="card-top">
      <span class="card-company-title">TechSolutions SpA</span>
      <span class="card-datetime">Lun 5 may &middot; 15:00</span>
      <span class="card-badge badge-reagendar">&#8635; Reagendar</span>
    </div>
    <div class="card-body">
      <div class="card-col">
        <div class="c-name">Valentina Arce Diaz</div>
        <div class="c-role">Directora de Operaciones</div>
        <div class="c-info">
          <span>&#9993; varce@techsolutions.cl</span>
          <span>&#128222; +56 9 6643 2210</span>
        </div>
        <span class="c-industry-tag">Tecnologia</span>
      </div>
      <div class="card-col">
        <div class="val-label">Validacion comercial</div>
        <select class="val-status-sel"><option>&#10003; Reunion valida</option><option>&#10007; No valida</option><option selected>&#8635; Reagendar</option><option>&#9203; Pendiente</option></select>
        <textarea class="val-textarea">No pudo asistir, reagendamos para primera semana de junio.</textarea>
        <button class="btn-save">&#128190; Guardar</button>
      </div>
    </div>
  </div>

  <!-- CARD 4: pendiente -->
  <div class="meeting-card pendiente">
    <div class="card-top">
      <span class="card-company-title">SERFONAC</span>
      <span class="card-datetime">Dom 25 may &middot; 19:58</span>
      <span class="card-badge badge-pendiente">&#9203; Pendiente</span>
    </div>
    <div class="card-body">
      <div class="card-col">
        <div class="c-name">Pablo Salgado Gomez</div>
        <div class="c-role">Gerente General</div>
        <div class="c-info">
          <span>&#9993; psalgado@serfonac.cl</span>
          <span>&#128222; +56 9 5511 7733</span>
        </div>
        <span class="c-industry-tag">Construccion</span>
      </div>
      <div class="card-col">
        <div class="val-label">Validacion comercial</div>
        <select class="val-status-sel"><option>&#10003; Reunion valida</option><option>&#10007; No valida</option><option>&#8635; Reagendar</option><option selected>&#9203; Pendiente</option></select>
        <textarea class="val-textarea" placeholder="Escribe observaciones sobre esta reunion..."></textarea>
        <button class="btn-save">&#128190; Guardar</button>
      </div>
    </div>
  </div>

</main>
</div>
</body>
</html>"""

HTML = HTML.replace('CP_PLACEHOLDER', CP).replace('TRS_PLACEHOLDER', TRS)

with open('dashboard/mockup_portal.html', 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f"Done. {os.path.getsize('dashboard/mockup_portal.html')//1024} KB")
