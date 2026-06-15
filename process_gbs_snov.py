#!/usr/bin/env python3
"""
Depuracion y clasificacion ICP - GBS Logistics x Base Snov
55.968 contactos -> clasificados por fit, macroindustria, macrocargo
"""

import sys, re, warnings
from pathlib import Path
import pandas as pd
import numpy as np
warnings.filterwarnings('ignore')

BASE = Path(__file__).resolve().parent
RAW  = BASE / "data" / "raw"     / "GBS" / "snov_all-prospects.xlsx"
OUT  = BASE / "data" / "outputs" / "GBS"
OUT.mkdir(parents=True, exist_ok=True)

print(f"Leyendo: {RAW}")

# ─── 1. Cargar por indice de columna (evita problemas de encoding) ───────────
df_raw = pd.read_excel(RAW, dtype=str, header=0)
print(f"Cargado: {len(df_raw):,} filas x {len(df_raw.columns)} columnas")

# Asignar nombres limpios por posicion
COL_NAMES = [
    'email', 'email_status', 'nombre', 'apellido', 'nombre_completo',
    'linkedin_social', 'linkedin',
    'cargo',
    'pais_persona', 'ubicacion_persona',
    'sector_persona',
    'fecha_agrega',
    'empresa', 'empresa_url', 'empresa_social',
    'empresa_size',
    'pais_empresa', 'ubicacion_empresa',
    'estado_provincia', 'ciudad',
    'sector_empresa',
    'hq_telefono', 'telefono',
    'cp_empresa', 'cp_size', 'cp_web', 'cp_movil', 'cp_linkedin_emp', 'cp_linkedin_per',
    'cp_size2', 'cp_web2',
]
df_raw.columns = COL_NAMES[:len(df_raw.columns)]
df = df_raw.copy()

# ─── 2. Limpiar valores nulos ────────────────────────────────────────────────
def clean(v):
    if pd.isna(v): return ''
    s = str(v).strip()
    return '' if s.lower() in ('nan', 'none', 'n/a', '-') else s

for c in df.columns:
    df[c] = df[c].apply(clean)

# ─── 3. Campos derivados ─────────────────────────────────────────────────────

# Nombre completo
df['nombre_completo'] = df.apply(
    lambda r: r['nombre_completo'] if r['nombre_completo']
              else f"{r['nombre']} {r['apellido']}".strip(), axis=1)

# LinkedIn: preferir campo directo
df['linkedin_final'] = df.apply(
    lambda r: r['linkedin'] or r['linkedin_social'] or r['cp_linkedin_per'] or r['cp_linkedin_emp'], axis=1)

# Email valido
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
PERSONAL_DOMAINS = {'gmail','hotmail','yahoo','outlook','icloud','live','msn','aol','protonmail'}

def email_valido(e):
    return bool(EMAIL_RE.match(e))

def email_corporativo(e):
    if not email_valido(e): return False
    dom = e.split('@')[-1].split('.')[0].lower()
    return dom not in PERSONAL_DOMAINS

df['tiene_email']        = df['email'].apply(email_valido)
df['email_corporativo']  = df['email'].apply(email_corporativo)
df['email_verificado']   = df['email_status'].str.lower().isin(['valid','verified'])

# Telefono: consolidar (prioridad: cp_movil > hq_telefono > telefono)
def clean_phone(p):
    if not p: return ''
    digitos = re.sub(r'\D', '', p)
    return p.strip() if len(digitos) >= 7 else ''

df['telefono_final'] = df.apply(
    lambda r: clean_phone(r['cp_movil']) or clean_phone(r['hq_telefono']) or clean_phone(r['telefono']),
    axis=1)
df['tiene_telefono'] = df['telefono_final'].apply(bool)
df['es_movil']       = df['cp_movil'].apply(lambda v: bool(clean_phone(v)))

# Pais normalizado
PAIS_MAP = {
    'chile':'Chile','cl':'Chile',
    'peru':'Peru','peru':'Peru',
    'colombia':'Colombia',
    'argentina':'Argentina',
    'mexico':'Mexico','mx':'Mexico',
    'brasil':'Brasil','brazil':'Brasil',
    'espana':'Espana','spain':'Espana',
    'united states':'USA','usa':'USA',
    'canada':'Canada',
}
def normalizar_pais(r):
    p = (r['pais_persona'] or r['pais_empresa']).lower().strip()
    for key, val in PAIS_MAP.items():
        if key in p:
            return val
    return (r['pais_persona'] or r['pais_empresa'] or 'Desconocido').title()

df['pais'] = df.apply(normalizar_pais, axis=1)

# Sector combinado (empresa tiene mejor dato para industria)
df['sector'] = df.apply(
    lambda r: r['sector_empresa'] or r['sector_persona'], axis=1)

# Tamanio empresa
def normalizar_size(s):
    if not s: return 'Desconocido'
    nums = re.findall(r'\d+', s)
    if not nums: return s
    n = int(nums[0])
    if n <= 10:   return '1-10'
    if n <= 50:   return '11-50'
    if n <= 200:  return '51-200'
    if n <= 500:  return '201-500'
    if n <= 1000: return '501-1000'
    return '1000+'

df['empresa_size_norm'] = df['empresa_size'].apply(normalizar_size)

# ─── 4. Deduplicar antes de scoring ─────────────────────────────────────────
n_inicial = len(df)
df['email_key'] = df['email'].str.lower().str.strip()
# Mantener el de mejor email_status entre duplicados de email
df['_sort_email'] = df['email_status'].apply(lambda s: 0 if s.lower() == 'valid' else 1)
df = df.sort_values('_sort_email')
df_dedup = df[df['email_key'] != ''].drop_duplicates(subset='email_key', keep='first')
df_noemail = df[df['email_key'] == ''].drop_duplicates(
    subset=['empresa', 'nombre_completo'], keep='first')
df = pd.concat([df_dedup, df_noemail], ignore_index=True)
df = df.drop(columns=['email_key', '_sort_email'])
n_dedup = len(df)
print(f"Duplicados eliminados: {n_inicial - n_dedup:,} | Quedan: {n_dedup:,}")

# ─── 5. Clasificacion de industria ───────────────────────────────────────────

# Keywords por macroindustria (operan sobre texto en ingles y espanol)
INDUSTRIA_KW = {
    'Mineria y Repuestos Mineros': [
        'mining','miner','metal','mineral','mineral','copper','cobre','lithium','litio',
        'gold','silver','coal','quarry','extractiv','drilling','chancador','molienda',
        'h-e parts','blumaq','boundary','aftermarket','repuesto minero','spare mine',
        'mining parts','ferrous','nonferrous','metals'
    ],
    'Maquinaria y Equipamiento Industrial': [
        'machinery','machine','equipment','industrial','automation','automatizacion',
        'valve','pump','bomba','motor','herramienta','manufactur','metalmec',
        'instrument','compressor','turbine','hydraulic','bearing','rodamiento',
        'ksb','rockwell','yokogawa','siemens','abb','engineering','ingenieria',
        'fabricacion','manufactura','industrial equipment','mechanical',
        'electrical equipment','power equipment','heavy equipment','tool'
    ],
    'Repuestos Automotrices': [
        'automotive','automotri','auto parts','repuesto auto','vehicle','car parts',
        'truck','autopart','carroceria','fleet','flota','spare parts auto',
        'auto accessories','motor vehicle','automobil'
    ],
    'Equipamiento Medico y Salud': [
        'health','medical','medic','hospital','clinic','pharma','laboratory',
        'laboratorio','dental','salud','healthcare','biomedical','dispositivo medico',
        'vitalmed','biomed','dipromed','arquimed','simmedical','farmaceutic',
        'diagnostic','life science','biotechnology','biotech'
    ],
    'Tecnologia y Electronica': [
        'technology','tech','electronic','software','telecom','hardware',
        'semiconductor','digital','computer','network','cloud','saas',
        'informatica','codificacion','imaging','printing','datacom',
        'information technology','it services','it ','ecommerce','e-commerce',
        'retail tech','pc factory','intcomex','td synnex','sp digital'
    ],
    'Retail y Distribucion': [
        'retail','distributor','distribution','wholesale','mayorista',
        'consumer goods','fmcg','fashion','apparel','ropa','vestuario',
        'tienda','store','comercio','supermarket','supermercado'
    ],
    'Alimentos y Vino': [
        'food','aliment','wine','vino','vina','vineyard','winery','beverage',
        'bebida','gourmet','fruto seco','dried food','agroindustria','agricola',
        'agro','frutícola','bodega','destileria','packaging food','tetra'
    ],
    'Quimica y Plasticos': [
        'chemical','quimic','plastic','polimer','polymer','rubber','goma',
        'resin','adhesive','paint','pintura','coating','lubricant'
    ],
    'Construccion e Infraestructura': [
        'construction','building','concrete','cement','obra','arquitect',
        'real estate','inmobil','infraestructure','contractor','steel','acero',
        'civil engineering'
    ],
    'Energia': [
        'energy','energia','power generation','solar','wind','eolica','oil','gas',
        'petroleum','petroleo','renewable','utilities'
    ],
}

EXCLUSION_KW = [
    'madera','wood','forestry','timber','avena','oat',
    'seafood','fish','salmon','fresh fruit','fruta fresca','banana',
    'frozen','congelado','cobre commodity','carbon coal commodity'
]

def classify_industria(sector, empresa, cargo=''):
    text = f"{sector} {empresa} {cargo}".lower()
    is_excl = any(k in text for k in EXCLUSION_KW)
    if is_excl:
        return 'Excluir - Commodity', 'Commodity excluido', False

    scores = {}
    for macro, kws in INDUSTRIA_KW.items():
        scores[macro] = sum(1 for k in kws if k in text)

    best = max(scores, key=scores.get) if scores else None
    if not best or scores[best] == 0:
        return 'Otras Industrias', 'Sin clasificar', False

    is_prio = best in ['Mineria y Repuestos Mineros','Maquinaria y Equipamiento Industrial',
                       'Repuestos Automotrices','Equipamiento Medico y Salud',
                       'Tecnologia y Electronica','Alimentos y Vino']
    micro = get_micro_industria(best, text)
    return best, micro, is_prio

def get_micro_industria(macro, text):
    m = {
        'Mineria y Repuestos Mineros': [
            ('repuesto minero','Repuestos y partes mineras'),
            ('parts','Repuestos y partes mineras'),
            ('service','Servicios a la mineria'),
            ('equipment','Equipos mineros'),
        ],
        'Maquinaria y Equipamiento Industrial': [
            ('pump','Bombas y valvulas'),
            ('valve','Bombas y valvulas'),
            ('automation','Automatizacion y control'),
            ('motor','Motores y accionamientos'),
            ('manufactur','Metalmecanica y manufactura'),
            ('metalmec','Metalmecanica y manufactura'),
        ],
        'Equipamiento Medico y Salud': [
            ('laborat','Laboratorios y diagnostico'),
            ('dental','Equipamiento dental'),
            ('pharma','Farmaceutica'),
        ],
        'Tecnologia y Electronica': [
            ('telecom','Telecomunicaciones'),
            ('software','Software y cloud'),
            ('hardware','Hardware y electronica'),
            ('print','Impresion y codificacion'),
        ],
        'Alimentos y Vino': [
            ('wine','Vino y vinas'),
            ('vino','Vino y vinas'),
            ('vina','Vino y vinas'),
        ],
    }
    for keyword, micro in m.get(macro, []):
        if keyword in text:
            return micro
    return macro

# ─── 6. Clasificacion de cargo ───────────────────────────────────────────────

CARGO_MACROS_KW = {
    'COMEX / Importaciones / Exportaciones': {
        'prio': 1,
        'kw': [
            'comex','import','export','customs','aduana','comercio exterior',
            'international trade','foreign trade','cross border','trade analyst',
            'coordinador import','encargado de importaciones','jefe comex',
            'jefa comex','analista comex','import manager','export manager',
            'import coordinator','international operations'
        ]
    },
    'Logistica / Supply Chain': {
        'prio': 1,
        'kw': [
            'supply chain','logistics','logistica','logistic','cadena de suministro',
            'distribution manager','distribución','inventory','inventario',
            'demand planning','fulfillment','warehouse manager','almacen'
        ]
    },
    'Abastecimiento / Compras': {
        'prio': 2,
        'kw': [
            'procurement','abastecimiento','compras','buyer','purchasing',
            'sourcing','adquisiciones','category manager','strategic sourcing',
            'compradora','comprador','supply manager','materiales'
        ]
    },
    'Operaciones': {
        'prio': 2,
        'kw': [
            'operations manager','gerente de operaciones','jefe de operaciones',
            'plant manager','plant director','production manager','fabricacion',
            'maintenance manager','facilities','director of operations',
            'chief operating','coo'
        ]
    },
    'Gerencia / Dueno / CEO': {
        'prio': 2,
        'kw': [
            'owner','ceo','founder','co-founder','general manager','gerente general',
            'director general','presidente','managing director','dueno','socio',
            'country manager','managing partner','chief executive','propietario',
            'socio director','director ejecutivo','president','vice president',
            'vp ','svp','evp'
        ]
    },
}

CARGO_DESCARTE_KW = [
    'marketing','diseno','design','graphic','creative','brand','content',
    'social media','community manager','copywriter','seo','publicidad',
    'human resources','recursos humanos','rrhh',' hr ','talent','people ops',
    'reclutamiento','headhunter',
    'developer','software engineer','programador','devops','data scientist',
    'machine learning','artificial intelligence','cybersecurity','it support',
    'systems admin','network engineer',
    'accountant','contador','accounting','payroll','nomina','tesorero',
    'tax','impuestos','auditor','legal','abogado','compliance',
]

CARGO_BAJA_KW = [
    'sales','vendedor','account executive','ejecutivo comercial',
    'business development','customer success','atención al cliente',
    'customer service','project manager','project coordinator',
    'analyst','analista','assistant','asistente','coordinador',
    'supervisor','tecnico','technician',
]

def classify_cargo(cargo_str):
    c = cargo_str.lower().strip()
    if not c:
        return 'Sin Cargo Definido', 3

    # Descarte primero
    if any(k in c for k in CARGO_DESCARTE_KW):
        return 'Descarte - Cargo Irrelevante', 5

    # Buscar mejor macro cargo
    best = None
    best_prio = 99
    best_count = 0
    for macro, info in CARGO_MACROS_KW.items():
        hits = sum(1 for k in info['kw'] if k in c)
        if hits > best_count or (hits > 0 and info['prio'] < best_prio):
            best_count = hits
            best = macro
            best_prio = info['prio']

    if best and best_count > 0:
        return best, best_prio

    if any(k in c for k in CARGO_BAJA_KW):
        return 'Baja Prioridad', 4

    return 'Otros', 3

def get_micro_cargo(macro, cargo):
    c = cargo.lower()
    if macro == 'Gerencia / Dueno / CEO':
        if any(k in c for k in ['owner','dueno','propietario','socio','founder']): return 'Dueno / Fundador / Socio'
        if any(k in c for k in ['ceo','general manager','gerente general']): return 'CEO / Gerente General'
        if any(k in c for k in ['vp','vice president','director']): return 'Director / VP'
        return 'Directivo General'
    if macro == 'COMEX / Importaciones / Exportaciones':
        if 'import' in c: return 'Importaciones'
        if 'export' in c: return 'Exportaciones'
        return 'Comercio Exterior / COMEX'
    if macro == 'Logistica / Supply Chain':
        if 'supply chain' in c or 'cadena' in c: return 'Supply Chain Manager'
        if 'warehouse' in c or 'almacen' in c: return 'Almacenes / Bodega'
        return 'Logistica'
    if macro == 'Abastecimiento / Compras':
        if 'procurement' in c: return 'Procurement Manager'
        return 'Compras / Abastecimiento'
    return macro

# ─── 7. Senales de comercio exterior ─────────────────────────────────────────

COMEX_SIGNALS = [
    'import','export','comex','aduana','customs','freight','forwarder',
    'comercio exterior','international trade','foreign trade',
    'importadora','exportadora','internacional','shipping','flete',
    'embarque','carga internacional','supply chain','logistic',
    'maritime','aereo','marítimo','aéreo'
]

def detect_comex(empresa, sector, cargo):
    text = f"{empresa} {sector} {cargo}".lower()
    hits = [k for k in COMEX_SIGNALS if k in text]
    return ('Si', ', '.join(hits[:3])) if hits else ('No', '')

# ─── 8. Scoring ICP ──────────────────────────────────────────────────────────

def score_row(r):
    cargo_str  = r['cargo']
    sector_str = r['sector']
    empresa    = r['empresa']
    pais       = r['pais']
    size       = r['empresa_size_norm']

    macro_cargo, cargo_prio = classify_cargo(cargo_str)
    macro_ind, micro_ind, ind_prio = classify_industria(sector_str, empresa, cargo_str)
    comex_sig, comex_det  = detect_comex(empresa, sector_str, cargo_str)

    score = 0
    motivos = []
    descarte_motivos = []

    # Cargo (25 pts)
    cargo_pts = {1: 25, 2: 18, 3: 8, 4: 3, 5: 0}
    score += cargo_pts.get(cargo_prio, 0)
    if cargo_prio <= 2:
        motivos.append(f"Cargo P{cargo_prio}: {cargo_str[:35]}")
    elif cargo_prio == 5:
        descarte_motivos.append(f"Cargo descartado: {cargo_str[:30]}")

    # Industria (25 pts)
    ind_pts = {
        'Mineria y Repuestos Mineros': 25,
        'Maquinaria y Equipamiento Industrial': 25,
        'Repuestos Automotrices': 22,
        'Equipamiento Medico y Salud': 22,
        'Alimentos y Vino': 20,
        'Tecnologia y Electronica': 18,
        'Retail y Distribucion': 15,
        'Quimica y Plasticos': 13,
        'Energia': 12,
        'Construccion e Infraestructura': 10,
        'Otras Industrias': 5,
        'Excluir - Commodity': 0,
    }
    ip = ind_pts.get(macro_ind, 5)
    score += ip
    if ip >= 20:
        motivos.append(f"Industria prioritaria: {macro_ind}")
    elif ip >= 12:
        motivos.append(f"Industria relevante: {macro_ind}")
    if macro_ind == 'Excluir - Commodity':
        descarte_motivos.append('Industria commodity excluida')

    # COMEX signals (20 pts)
    if comex_sig == 'Si':
        score += 20
        motivos.append(f"Senal COMEX: {comex_det}")
    else:
        descarte_motivos.append('Sin senal de comercio exterior')

    # Pais (10 pts)
    pais_pts = {'Chile': 10, 'Peru': 7, 'Colombia': 7, 'Argentina': 4,
                'Mexico': 4, 'Brasil': 4, 'Espana': 3, 'USA': 2}
    pp = pais_pts.get(pais, 1)
    score += pp
    if pp >= 7:
        motivos.append(f"Pais objetivo: {pais}")

    # Tamano empresa (10 pts)
    size_pts = {'1-10': 2, '11-50': 7, '51-200': 10, '201-500': 8,
                '501-1000': 5, '1000+': 3, 'Desconocido': 3}
    sp = size_pts.get(size, 3)
    score += sp
    if sp >= 7:
        motivos.append(f"Tamano adecuado: {size}")

    # Senales dolor logistico (10 pts)
    DOLOR_KW = ['freight','forwarder','flete','embarque','aduana','customs',
                'coordinacion','visibilidad','documentacion','almacenaje']
    text = f"{empresa} {sector_str} {cargo_str}".lower()
    dolor_pts = min(sum(1 for k in DOLOR_KW if k in text) * 3, 10)
    score += dolor_pts

    # Penalizacion commodity
    if macro_ind == 'Excluir - Commodity':
        score = min(score, 20)

    score = min(max(score, 0), 100)

    if score >= 75:   fit = 'Alto'
    elif score >= 55: fit = 'Medio'
    elif score >= 35: fit = 'Bajo'
    else:             fit = 'Descartar'

    if fit == 'Alto' and cargo_prio == 1:
        tir = 'TIR-1 Prioridad Maxima'
    elif fit == 'Alto':
        tir = 'TIR-2 Alta'
    elif fit == 'Medio':
        tir = 'TIR-3 Media'
    elif fit == 'Bajo':
        tir = 'TIR-4 Baja'
    else:
        tir = 'TIR-5 Descartar'

    # Segmento y recomendacion
    seg_ind = {
        'Mineria y Repuestos Mineros': 'MIN',
        'Maquinaria y Equipamiento Industrial': 'MAQ',
        'Repuestos Automotrices': 'AUTO',
        'Equipamiento Medico y Salud': 'SALUD',
        'Tecnologia y Electronica': 'TECH',
        'Retail y Distribucion': 'RETAIL',
        'Alimentos y Vino': 'ALIM',
    }.get(macro_ind, 'OTROS')

    seg_cargo = {
        'COMEX / Importaciones / Exportaciones': 'COMEX',
        'Logistica / Supply Chain': 'LOG',
        'Abastecimiento / Compras': 'COMP',
        'Operaciones': 'OPS',
        'Gerencia / Dueno / CEO': 'GG',
    }.get(macro_cargo, 'OTROS')

    return {
        'icp_score':                 score,
        'fit_level':                 fit,
        'macro_industria':           macro_ind,
        'micro_industria':           micro_ind,
        'macro_cargo':               macro_cargo,
        'micro_cargo':               get_micro_cargo(macro_cargo, cargo_str),
        'prioridad_tir':             tir,
        'motivo_fit':                ' | '.join(motivos[:4]) or '-',
        'motivo_descarte':           ' | '.join(descarte_motivos[:3]) or '-',
        'senal_import_export':       comex_sig,
        'senal_industria_prioritaria': 'Si' if ip >= 20 else ('Media' if ip >= 12 else 'No'),
        'senal_cargo_prioritario':   'Si' if cargo_prio <= 2 else 'No',
        'recomendacion_campana':     f"Campaña {seg_ind} x {seg_cargo}" if fit != 'Descartar' else 'No enviar',
        'segmento_mensaje':          f"Seg-{seg_ind}-{seg_cargo}",
        'archivo_destino':           f"gbs_{seg_ind.lower()}_{seg_cargo.lower()}.xlsx",
    }

# ─── 9. Aplicar scoring ──────────────────────────────────────────────────────
print("Clasificando contactos (puede tomar 1-2 minutos)...")
scores_df = df.apply(score_row, axis=1, result_type='expand')
df_out = pd.concat([df, scores_df], axis=1)
df_out = df_out.sort_values(['icp_score'], ascending=False).reset_index(drop=True)

# ─── 10. Columnas de salida ───────────────────────────────────────────────────
COLS_BASE = [
    'nombre_completo', 'nombre', 'apellido', 'cargo',
    'email', 'email_status', 'tiene_email', 'email_corporativo', 'email_verificado',
    'telefono_final', 'es_movil',
    'empresa', 'empresa_url', 'empresa_size_norm', 'pais', 'ciudad',
    'sector', 'linkedin_final',
    'icp_score', 'fit_level', 'macro_industria', 'micro_industria',
    'macro_cargo', 'micro_cargo', 'prioridad_tir',
    'motivo_fit', 'motivo_descarte',
    'senal_import_export', 'senal_industria_prioritaria', 'senal_cargo_prioritario',
    'recomendacion_campana', 'segmento_mensaje', 'archivo_destino',
    'tiene_telefono',
]
cols = [c for c in COLS_BASE if c in df_out.columns]
df_final = df_out[cols].copy()

# ─── 11. Guardar archivos ─────────────────────────────────────────────────────
def save(df_s, name):
    if len(df_s) == 0:
        print(f"  SKIP (vacio): {name}")
        return
    p_csv  = OUT / f"{name}.csv"
    p_xlsx = OUT / f"{name}.xlsx"
    df_s.to_csv(p_csv, index=False, encoding='utf-8-sig')
    with pd.ExcelWriter(p_xlsx, engine='openpyxl') as w:
        df_s.to_excel(w, index=False, sheet_name='Contactos', freeze_panes=(1, 0))
        ws = w.sheets['Contactos']
        for col in ws.columns:
            ml = max((len(str(cell.value or '')) for cell in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(ml + 2, 45)
        ws.auto_filter.ref = ws.dimensions
    print(f"  {name}: {len(df_s):,} filas")

print("\nGenerando archivos de salida...")

# Base completa
save(df_final, "gbs_base_depurada_completa")

# Por fit level
for fit in ['Alto', 'Medio', 'Bajo', 'Descartar']:
    save(df_final[df_final['fit_level'] == fit], f"gbs_fit_{fit.lower()}")
save(df_final[df_final['fit_level'].isin(['Alto', 'Medio'])], "gbs_fit_alto_medio")

# === ARCHIVOS PARA SUBIR A SNOV / CAMPANAS ===
# Segmentados por disponibilidad de contacto
# Para Snov: siempre necesita email
df_con_email    = df_final[df_final['tiene_email']]
df_con_tel      = df_final[df_final['tiene_telefono']]
df_email_y_tel  = df_final[df_final['tiene_email']  & df_final['tiene_telefono']]
df_solo_email   = df_final[df_final['tiene_email']  & ~df_final['tiene_telefono']]
df_solo_tel     = df_final[~df_final['tiene_email'] & df_final['tiene_telefono']]

save(df_con_email,   "gbs_SNOV_para_subir_con_email")
save(df_email_y_tel, "gbs_email_Y_telefono")
save(df_solo_email,  "gbs_solo_email_sin_telefono")
save(df_solo_tel,    "gbs_solo_telefono_sin_email")

# Para campana: solo los buenos con email (Fit Alto + Medio con email)
df_campana = df_final[df_final['tiene_email'] & df_final['fit_level'].isin(['Alto','Medio'])]
save(df_campana, "gbs_CAMPANA_fit_alto_medio_con_email")

# Por macroindustria (solo Alto + Medio con email)
df_am = df_final[df_final['fit_level'].isin(['Alto','Medio'])]
ind_files = {
    'Mineria y Repuestos Mineros':          'gbs_mineria_repuestos',
    'Maquinaria y Equipamiento Industrial': 'gbs_maquinaria_industrial',
    'Repuestos Automotrices':               'gbs_repuestos_automotrices',
    'Equipamiento Medico y Salud':          'gbs_equipamiento_medico',
    'Tecnologia y Electronica':             'gbs_tecnologia_electronica',
    'Retail y Distribucion':               'gbs_retail_distribucion',
    'Alimentos y Vino':                     'gbs_alimentos_vino',
}
for macro, fname in ind_files.items():
    save(df_am[df_am['macro_industria'] == macro], fname)

# Por macrocargo (toda la base con fit relevante)
df_rel = df_final[df_final['fit_level'].isin(['Alto','Medio','Bajo'])]
cargo_files = {
    'COMEX / Importaciones / Exportaciones': 'gbs_comex_import_export',
    'Logistica / Supply Chain':              'gbs_supply_chain_logistica',
    'Abastecimiento / Compras':              'gbs_abastecimiento_compras',
    'Operaciones':                           'gbs_operaciones',
    'Gerencia / Dueno / CEO':               'gbs_duenos_gerencia_general',
}
for macro, fname in cargo_files.items():
    save(df_rel[df_rel['macro_cargo'] == macro], fname)

# ─── 12. Reporte resumen ──────────────────────────────────────────────────────
fit_counts = df_final['fit_level'].value_counts()
ind_counts = df_final[df_final['fit_level'].isin(['Alto','Medio'])]['macro_industria'].value_counts()
cargo_counts = df_final[df_final['fit_level'].isin(['Alto','Medio'])]['macro_cargo'].value_counts()
pais_counts = df_final['pais'].value_counts().head(10)
top_emp = (df_final[df_final['fit_level'].isin(['Alto','Medio'])]
           .groupby('empresa')
           .agg(score_medio=('icp_score','mean'), n=('icp_score','count'))
           .sort_values('score_medio', ascending=False)
           .head(20))

report = f"""# Reporte de Depuracion y Clasificacion ICP
## GBS Logistics x Base Snov
**Generado:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

---

## Resumen de Volumen

| Metrica | Cantidad |
|---------|----------|
| Contactos iniciales | {n_inicial:,} |
| Duplicados eliminados | {n_inicial - n_dedup:,} |
| Contactos finales procesados | {len(df_final):,} |
| Con email valido | {df_final['tiene_email'].sum():,} ({df_final['tiene_email'].mean()*100:.1f}%) |
| Con telefono | {df_final['tiene_telefono'].sum():,} ({df_final['tiene_telefono'].mean()*100:.1f}%) |
| Con email Y telefono | {(df_final['tiene_email'] & df_final['tiene_telefono']).sum():,} |
| Solo email (sin telefono) | {(df_final['tiene_email'] & ~df_final['tiene_telefono']).sum():,} |
| Solo telefono (sin email) | {(~df_final['tiene_email'] & df_final['tiene_telefono']).sum():,} |

## Clasificacion por Fit ICP

| Fit Level | Cantidad | % |
|-----------|----------|---|
"""
for fit in ['Alto','Medio','Bajo','Descartar']:
    n = fit_counts.get(fit, 0)
    report += f"| {fit} | {n:,} | {n/len(df_final)*100:.1f}% |\n"

report += f"""
## Top 20 Empresas mas Prometedoras (Fit Alto + Medio)

| Empresa | Score Promedio | N contactos |
|---------|---------------|-------------|
"""
for emp, row_e in top_emp.iterrows():
    report += f"| {emp[:40]} | {row_e['score_medio']:.0f} | {row_e['n']} |\n"

report += f"""
## Distribucion por Macroindustria (Fit Alto + Medio)

| Industria | Cantidad |
|-----------|----------|
"""
for ind, n in ind_counts.items():
    report += f"| {ind} | {n:,} |\n"

report += f"""
## Distribucion por Macrocargo (Fit Alto + Medio)

| Cargo | Cantidad |
|-------|----------|
"""
for cargo, n in cargo_counts.items():
    report += f"| {cargo} | {n:,} |\n"

report += f"""
## Distribucion por Pais

| Pais | Cantidad |
|------|----------|
"""
for pais, n in pais_counts.items():
    report += f"| {pais} | {n:,} |\n"

report += """
## Recomendacion de Campanas

### Campana 1 - Prioritaria: COMEX x Mineria + Maquinaria
- **Archivo**: `gbs_comex_import_export.xlsx` filtrado por industria MIN/MAQ
- **Mensaje**: urgencia operacional, retrasos de repuestos criticos
- **Cargo target**: Encargado COMEX, Jefe Importaciones, Supply Chain

### Campana 2 - Gerencia en Pymes con senal COMEX
- **Archivo**: `gbs_duenos_gerencia_general.xlsx`
- **Mensaje**: "socio logistico externo sin necesidad de equipo interno"
- **Cargo target**: Dueno, Gerente General, CEO en 11-200 empleados

### Campana 3 - Maquinaria + Equipamiento Medico x Compras
- **Archivo**: `gbs_maquinaria_industrial.xlsx` + `gbs_equipamiento_medico.xlsx`
- **Mensaje**: llegada segura de insumos criticos, sin paradas
- **Cargo target**: Procurement, Abastecimiento, Compras

## Archivos para Subir a Snov
- `gbs_SNOV_para_subir_con_email.xlsx` - TODOS con email valido (para subir directo a Snov)
- `gbs_CAMPANA_fit_alto_medio_con_email.xlsx` - Solo los mejores con email (recomendado para primera campana)
- `gbs_email_Y_telefono.xlsx` - Tienen ambos (para secuencias multi-canal)
- `gbs_solo_telefono_sin_email.xlsx` - Solo telefono (para llamada/WhatsApp)

## Observaciones de Calidad

- Campos personalizados (telefono movil, LinkedIn extra) estan vacios en la mayoria
- HQ Telefono es el campo de telefono principal disponible
- Sector viene del rubro LinkedIn de la empresa (buena calidad para clasificacion)
- Muchos contactos de Chile con industrias diversas
- Recomendado: verificar emails antes de lanzar campana (estado 'valid' ya filtrado)

## Columnas que Conviene Enriquecer
- Telefono movil (campo personalizado vacio en casi todos)
- LinkedIn personal mas completo
- Tamano de empresa (muchos desconocidos)
- Ciudad/Region especifica para Chile
"""

(OUT / "resumen_depuracion_gbs.md").write_text(report, encoding='utf-8')
print(f"\nReporte guardado: resumen_depuracion_gbs.md")

print("\n" + "="*60)
print("PROCESO COMPLETADO")
print(f"Archivos en: {OUT}")
print(f"Total contactos finales: {len(df_final):,}")
for fit in ['Alto','Medio','Bajo','Descartar']:
    n = fit_counts.get(fit, 0)
    print(f"  {fit}: {n:,}")
print(f"Con email: {df_final['tiene_email'].sum():,}")
print(f"Con telefono: {df_final['tiene_telefono'].sum():,}")
print("="*60)
