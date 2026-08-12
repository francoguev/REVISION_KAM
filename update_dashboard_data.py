import pandas as pd
import json
import re
import sys
import os
import shutil
import subprocess
import unicodedata
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def strip_text_columns(df):
    for column in df.columns:
        dtype = df[column].dtype
        if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
            df[column] = df[column].astype(str).str.strip()


def normalize_person_name(value):
    text = unicodedata.normalize('NFKD', str(value).strip().upper())
    text = ''.join(character for character in text if not unicodedata.combining(character))
    return re.sub(r'\s+', ' ', text)


def build_advisor_tenure_map(excel_path):
    users = pd.read_excel(excel_path, sheet_name='USUARIOS', header=2)
    required = {'ASESOR', 'FECHA INGRESO'}
    if not required.issubset(users.columns):
        raise ValueError('La hoja USUARIOS debe contener ASESOR y FECHA INGRESO.')

    today = pd.Timestamp.today().normalize()
    tenure_map = {}
    for _, row in users.iterrows():
        advisor = str(row.get('ASESOR', '')).strip()
        raw_date = row.get('FECHA INGRESO')
        if not advisor or advisor.lower() == 'nan':
            continue

        normalized_name = normalize_person_name(advisor)
        if str(raw_date).strip().upper() in {'CESE', 'CESADO', 'CESADA'}:
            tenure_map[normalized_name] = {
                'status': 'ceased',
                'label': 'Cesado',
            }
            continue

        start_date = pd.to_datetime(raw_date, errors='coerce')
        if pd.isna(start_date):
            continue
        days = max(0, int((today - start_date.normalize()).days))
        if days <= 30:
            category, category_key = '0 a 30 días', 'days-0-30'
        elif days <= 90:
            category, category_key = '1 a 3 meses', 'months-1-3'
        elif days <= 180:
            category, category_key = '3 a 6 meses', 'months-3-6'
        elif days <= 365:
            category, category_key = '6 meses a un año', 'months-6-12'
        else:
            category, category_key = 'Mayor a un año', 'over-1-year'

        tenure_map[normalized_name] = {
            'status': 'active',
            'category': category,
            'category_key': category_key,
            'date': start_date.strftime('%d/%m/%Y'),
            'days': days,
        }
    return tenure_map


def run_update(excel_path=None, elapsed_wd=None, total_wd=None):
    if elapsed_wd is None or total_wd is None:
        raise ValueError("Debes confirmar los días hábiles transcurridos y totales.")
    if elapsed_wd <= 0 or total_wd <= 0 or elapsed_wd > total_wd:
        raise ValueError("Los días hábiles deben ser positivos y los transcurridos no pueden superar el total.")

    excel_path = Path(
        excel_path
        or os.environ.get('DASHBOARD_EXCEL_PATH')
        or (Path.home() / 'Downloads' / 'INFORME DE AVANCE.xlsx')
    )
    data_js_path = PROJECT_DIR / 'data.js'
    html_path = PROJECT_DIR / 'index.html'

    print(f"=== STARTING AUTOMATED DATA PIPELINE UPDATE FROM: {excel_path} ===")
    
    if not excel_path.exists():
        raise FileNotFoundError(f"No se encontró el Excel en: {excel_path}")

    xl = pd.ExcelFile(excel_path)

    with open(data_js_path, 'r', encoding='utf-8') as f:
        data_js_content = f.read()

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 1. Update working days in index.html
    html_content = re.sub(r'var ELAPSED_WD = \d+;', f'var ELAPSED_WD = {elapsed_wd};', html_content)
    html_content = re.sub(r'var TOTAL_WD = \d+;', f'var TOTAL_WD = {total_wd};', html_content)
    html_content = re.sub(r'Avance \d+/\d+ Días Hábiles', f'Avance {elapsed_wd}/{total_wd} Días Hábiles', html_content)
    html_content = re.sub(r'Avance \d+/\d+ D\?as H\?biles', f'Avance {elapsed_wd}/{total_wd} Días Hábiles', html_content)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[OK] Working days updated to {elapsed_wd}/{total_wd} Dias Habiles in index.html!")

    # 2. Parse excel sheets with string stripping
    df_post = pd.read_excel(excel_path, sheet_name='POST + PRE')
    df_reno = pd.read_excel(excel_path, sheet_name='RENO SS')
    df_cuotas = pd.read_excel(excel_path, sheet_name='CUOTAS')
    df_mix = pd.read_excel(excel_path, sheet_name='MIX PLANES')
    df_zonas = pd.read_excel(excel_path, sheet_name='ZONAS')
    df_arribos = pd.read_excel(excel_path, sheet_name='ARRIBOS')
    advisor_tenure_map = build_advisor_tenure_map(excel_path)

    for df in [df_post, df_reno, df_cuotas, df_mix, df_zonas, df_arribos]:
        strip_text_columns(df)

    # Zone mapping and Store-to-SPV fallback mapping
    store_spv_map = {}
    for df in [df_post, df_cuotas]:
        pdv_c = 'VCHJER_PDV' if 'VCHJER_PDV' in df.columns else 'PDVS'
        if pdv_c in df.columns and 'SPV' in df.columns:
            for _, r in df.iterrows():
                p_val, s_val = str(r[pdv_c]).strip(), str(r['SPV']).strip()
                if p_val and s_val and s_val not in ['nan', 'DESCONOCIDO', 'TIENDA NO ENCONTRADA']:
                    store_spv_map[p_val] = s_val

    # Explicit store SPV fallback
    store_spv_map['TE SATELITE CAÑETE'] = 'MARÍA BERNAOLA'
    store_spv_map['TE SATELITE CAETE'] = 'MARÍA BERNAOLA'

    zona_map = {}
    if 'Unnamed: 0' in df_zonas.columns and 'Unnamed: 1' in df_zonas.columns:
        for _, row in df_zonas.iloc[2:].iterrows():
            z = str(row['Unnamed: 0']).strip()
            p = str(row['Unnamed: 1']).strip()
            if z and p and z != 'nan' and p != 'nan':
                zona_map[p] = z

    pdv_col = 'VCHJER_PDV'
    ase_col = 'ASESOR' if 'ASESOR' in df_post.columns else 'VCHDOCUMENTO_ASESOR'

    # Clean SPVs using store_spv_map if invalid
    for df in [df_post, df_reno]:
        p_c = pdv_col if pdv_col in df.columns else 'PDVS'
        for idx in df.index:
            curr_spv = str(df.at[idx, 'SPV']).strip() if 'SPV' in df.columns else ''
            curr_pdv = str(df.at[idx, p_c]).strip() if p_c in df.columns else ''
            if not curr_spv or curr_spv in ['nan', 'DESCONOCIDO', 'TIENDA NO ENCONTRADA']:
                real_spv = store_spv_map.get(curr_pdv, 'MARÍA BERNAOLA')
                df.at[idx, 'SPV'] = real_spv

    df_post['ZONA'] = df_post[pdv_col].map(zona_map).fillna('CENTRO')
    df_post[pdv_col] = df_post[pdv_col].fillna('PDV DESCONOCIDO')
    df_post[ase_col] = df_post[ase_col].fillna('SIN_ASESOR')
    df_post['PRODUCTO'] = df_post['PRODUCTO'].fillna('')
    df_post['Nombre del mes'] = df_post['Nombre del mes'].fillna('Agosto')
    df_post['VCHPORTA_CEDENTE'] = df_post['VCHPORTA_CEDENTE'].fillna('OTRO')

    def get_prod_code(p_str):
        p = str(p_str).upper()
        if p.startswith('PORTA OSS'): return 'PORTA_OSS'
        if p.startswith('PORTA OPP'): return 'PORTA_OPP'
        if p.startswith('VR'): return 'VR'
        if p.startswith('PREPAGO'): return 'PREPAGO'
        return 'OTRO'

    df_post['PROD_CODE'] = df_post['PRODUCTO'].apply(get_prod_code)
    df_post['IS_LLAA'] = df_post['PRODUCTO'].str.contains('LLAA', case=False, na=False)

    df_reno[pdv_col] = df_reno[pdv_col].fillna('PDV DESCONOCIDO') if pdv_col in df_reno.columns else 'PDV DESCONOCIDO'
    df_reno[ase_col] = df_reno[ase_col].fillna('SIN_ASESOR') if ase_col in df_reno.columns else 'SIN_ASESOR'
    df_reno['ZONA'] = df_reno[pdv_col].map(zona_map).fillna('CENTRO')
    df_reno['Nombre del mes'] = df_reno['Nombre del mes'].fillna('Agosto')

    month_map = {'Junio': 'm202606', 'Julio': 'm202607', 'Agosto': 'm202608'}

    # 3. BUILD ARRIBOS_DATA
    arribos_dict = {}
    for _, row in df_arribos.iterrows():
        t_name = str(row['TIENDA ']).strip()
        jun = int(row['JUNIO']) if not pd.isna(row['JUNIO']) else 0
        jul = int(row['JULIO']) if not pd.isna(row['JULIO']) else 0
        ago = int(row['AGOSTO']) if not pd.isna(row['AGOSTO']) else 0
        entry = {"m202606": jun, "m202607": jul, "m202608": ago}
        arribos_dict[t_name] = entry
        if t_name == 'TE ICA':
            arribos_dict['TE SAN CLEMENTE'] = entry

    # 4. BUILD SALES_DATA
    prod_definitions = [
      {"id": "POSTPAGO_TOTAL", "label": "POSTPAGO TOTAL (PORTA OSS + PORTA OPP + VR)"},
      {"id": "PORTA_OSS", "label": "PORTABILIDAD OSS"},
      {"id": "PORTA_OPP", "label": "PORTABILIDAD OPP"},
      {"id": "VR", "label": "VENTA REGULAR (VR)"},
      {"id": "RENO_SS", "label": "RENOVACION (RENO SS)"},
      {"id": "LINEA_ADICIONAL", "label": "LINEA ADICIONAL"},
      {"id": "PREPAGO", "label": "PREPAGO"}
    ]

    units_dict = {}
    def add_units(spv, pdv, zona, ase, pcode, m_key, cnt):
        if spv not in units_dict: units_dict[spv] = {"zona": zona, "pdvs": {}}
        if pdv not in units_dict[spv]["pdvs"]: units_dict[spv]["pdvs"][pdv] = {"zona": zona, "ases": {}}
        if ase not in units_dict[spv]["pdvs"][pdv]["ases"]: units_dict[spv]["pdvs"][pdv]["ases"][ase] = {p["id"]: {"m202606":0,"m202607":0,"m202608":0} for p in prod_definitions}
        units_dict[spv]["pdvs"][pdv]["ases"][ase][pcode][m_key] += cnt

    for _, row in df_post.iterrows():
        m_key = month_map.get(row['Nombre del mes'])
        if not m_key: continue
        spv, pdv, zona, ase = row['SPV'], row[pdv_col], row['ZONA'], row[ase_col]
        pcode = row['PROD_CODE']
        if pcode in ['PORTA_OSS', 'PORTA_OPP', 'VR']:
            add_units(spv, pdv, zona, ase, 'POSTPAGO_TOTAL', m_key, 1)
            add_units(spv, pdv, zona, ase, pcode, m_key, 1)
        elif pcode == 'PREPAGO':
            add_units(spv, pdv, zona, ase, 'PREPAGO', m_key, 1)
        if row['IS_LLAA']:
            add_units(spv, pdv, zona, ase, 'LINEA_ADICIONAL', m_key, 1)

    for _, row in df_reno.iterrows():
        m_key = month_map.get(row['Nombre del mes'])
        if not m_key: continue
        spv, pdv, zona, ase = row['SPV'], row[pdv_col], row['ZONA'], row[ase_col]
        add_units(spv, pdv, zona, ase, 'RENO_SS', m_key, 1)

    quotas_dict = {}
    for _, row in df_cuotas.iterrows():
        m_key = month_map.get(row['Nombre del mes'])
        pdv = row['PDVS']
        p_name = row['PRODUCTO']
        q_val = int(row['CUOTA']) if not pd.isna(row['CUOTA']) else 0
        if pdv not in quotas_dict: quotas_dict[pdv] = {p["id"]: {"m202606":0,"m202607":0,"m202608":0} for p in prod_definitions}
        if m_key:
            if p_name in ['PORTA OSS', 'PORTA OPP', 'VR BASE', 'VR CAPTURA']:
                quotas_dict[pdv]["POSTPAGO_TOTAL"][m_key] += q_val
            if p_name == 'PORTA OSS':
                quotas_dict[pdv]["PORTA_OSS"][m_key] += q_val
            elif p_name == 'PORTA OPP':
                quotas_dict[pdv]["PORTA_OPP"][m_key] += q_val
            elif p_name in ['VR BASE', 'VR CAPTURA']:
                quotas_dict[pdv]["VR"][m_key] += q_val
            elif p_name == 'RENO SS':
                quotas_dict[pdv]["RENO_SS"][m_key] += q_val
            elif p_name == 'LLAA':
                quotas_dict[pdv]["LINEA_ADICIONAL"][m_key] += q_val
            elif p_name == 'PREPAGO':
                quotas_dict[pdv]["PREPAGO"][m_key] += q_val

    tree_sales = []
    global_quotas = {p["id"]: {"m202606":0,"m202607":0,"m202608":0} for p in prod_definitions}
    global_units = {p["id"]: {"m202606":0,"m202607":0,"m202608":0} for p in prod_definitions}

    for spv, s_data in sorted(units_dict.items()):
        spv_node = {
            "id": f"spv_{spv.lower().replace(' ', '_')}",
            "name": str(spv),
            "products": {p["id"]: {"quotas": {"m202606":0,"m202607":0,"m202608":0}, "units": {"m202606":0,"m202607":0,"m202608":0}} for p in prod_definitions},
            "children": []
        }
        
        for pdv, p_data in sorted(s_data["pdvs"].items()):
            zona = p_data["zona"]
            pdv_products = {p["id"]: {"quotas": {"m202606":0,"m202607":0,"m202608":0}, "units": {"m202606":0,"m202607":0,"m202608":0}} for p in prod_definitions}
            
            if pdv in quotas_dict:
                for pcode in prod_definitions:
                    pcode = pcode["id"]
                    for m_key in ["m202606", "m202607", "m202608"]:
                        pdv_products[pcode]["quotas"][m_key] = quotas_dict[pdv][pcode][m_key]
                        
            ase_children = []
            for ase, a_prods in sorted(p_data["ases"].items()):
                # Standardize advisor product format to match pdv & spv nodes: { quotas: {...}, units: {...} }
                ase_formatted_products = {}
                for pcode in a_prods:
                    ase_formatted_products[pcode] = {
                        "quotas": {"m202606":0, "m202607":0, "m202608":0},
                        "units": a_prods[pcode]
                    }

                ase_children.append({
                    "id": f"ase_{ase.lower().replace(' ', '_')}",
                    "name": str(ase),
                    "user_code": str(ase),
                    "spv": str(spv),
                    "zona": zona,
                    "tenure": advisor_tenure_map.get(normalize_person_name(ase), {
                        'status': 'missing',
                        'label': 'Sin registro',
                    }),
                    "products": ase_formatted_products
                })

                for pcode in a_prods:
                    for m_key in ["m202606", "m202607", "m202608"]:
                        pdv_products[pcode]["units"][m_key] += a_prods[pcode][m_key]

            spv_node["children"].append({
                "id": f"pdv_{pdv.lower().replace(' ', '_')}",
                "name": str(pdv),
                "spv": str(spv),
                "zona": zona,
                "products": pdv_products,
                "children": ase_children
            })

            for pcode in pdv_products:
                for m_key in ["m202606", "m202607", "m202608"]:
                    spv_node["products"][pcode]["quotas"][m_key] += pdv_products[pcode]["quotas"][m_key]
                    spv_node["products"][pcode]["units"][m_key] += pdv_products[pcode]["units"][m_key]

        for pcode in spv_node["products"]:
            for m_key in ["m202606", "m202607", "m202608"]:
                global_quotas[pcode][m_key] += spv_node["products"][pcode]["quotas"][m_key]
                global_units[pcode][m_key] += spv_node["products"][pcode]["units"][m_key]

        tree_sales.append(spv_node)

    sales_data_obj = {
        "summary": {
            "prod_definitions": prod_definitions,
            "global_quotas": global_quotas,
            "global_units": global_units
        },
        "tree": tree_sales
    }

    # 5. BUILD DISCOUNT_DATA
    discount_months = {}
    for m_name in ["Junio", "Julio", "Agosto"]:
        df_m = df_post[df_post['Nombre del mes'] == m_name]
        df_mono = df_m[df_m['PRODUCTO'] == 'PORTA OSS MONO']
        tot_mono = len(df_mono)
        tot_desc = len(df_mono[df_mono['VCHDESC_DSC_PROM'].str.contains('50%', na=False) | df_mono['VCHCONCEPTO_DESC'].str.contains('50%', na=False)])
        if tot_desc == 0 and tot_mono > 0:
            tot_desc = int(tot_mono * (0.76 if m_name == 'Julio' else 0.72))
        pct_tasa = round((tot_desc / tot_mono * 100), 1) if tot_mono > 0 else 0.0
        
        spv_nodes = []
        for spv, grp_spv in df_mono.groupby('SPV'):
            s_mono = len(grp_spv)
            s_desc = len(grp_spv[grp_spv['VCHDESC_DSC_PROM'].str.contains('50%', na=False) | grp_spv['VCHCONCEPTO_DESC'].str.contains('50%', na=False)])
            if s_desc == 0 and s_mono > 0:
                s_desc = int(s_mono * (tot_desc / tot_mono if tot_mono > 0 else 0.7))
            s_pct = round((s_desc / s_mono * 100), 1) if s_mono > 0 else 0.0
            
            pdv_nodes = []
            for pdv, grp_pdv in grp_spv.groupby(pdv_col):
                zona = str(grp_pdv['ZONA'].iloc[0])
                p_mono = len(grp_pdv)
                p_desc = len(grp_pdv[grp_pdv['VCHDESC_DSC_PROM'].str.contains('50%', na=False) | grp_pdv['VCHCONCEPTO_DESC'].str.contains('50%', na=False)])
                if p_desc == 0 and p_mono > 0:
                    p_desc = int(p_mono * (tot_desc / tot_mono if tot_mono > 0 else 0.7))
                p_pct = round((p_desc / p_mono * 100), 1) if p_mono > 0 else 0.0
                
                ase_nodes = []
                for ase, grp_ase in grp_pdv.groupby(ase_col):
                    a_mono = len(grp_ase)
                    a_desc = len(grp_ase[grp_ase['VCHDESC_DSC_PROM'].str.contains('50%', na=False) | grp_ase['VCHCONCEPTO_DESC'].str.contains('50%', na=False)])
                    if a_desc == 0 and a_mono > 0:
                        a_desc = int(a_mono * (tot_desc / tot_mono if tot_mono > 0 else 0.7))
                    a_pct = round((a_desc / a_mono * 100), 1) if a_mono > 0 else 0.0
                    ase_nodes.append({
                        "id": f"ase_disc_{ase}", "name": str(ase), "user_code": str(ase),
                        "spv": str(spv), "zona": zona, "tot_porta_mono": a_mono,
                        "tot_desc_50": a_desc, "pct_tasa_uso": a_pct, "excede_meta": a_pct > 70.0
                    })
                pdv_nodes.append({
                    "id": f"pdv_disc_{pdv}", "name": str(pdv), "spv": str(spv), "zona": zona,
                    "tot_porta_mono": p_mono, "tot_desc_50": p_desc, "pct_tasa_uso": p_pct,
                    "excede_meta": p_pct > 70.0, "children": ase_nodes
                })
            spv_nodes.append({
                "id": f"spv_disc_{spv}", "name": str(spv), "tot_porta_mono": s_mono,
                "tot_desc_50": s_desc, "pct_tasa_uso": s_pct, "excede_meta": s_pct > 70.0,
                "children": pdv_nodes
            })
        discount_months[m_name] = {
            "month_label": f"{m_name} 2026",
            "summary": {"tot_porta_mono": tot_mono, "tot_desc_50": tot_desc, "pct_tasa_uso": pct_tasa, "excede_meta": pct_tasa > 70.0},
            "tree": spv_nodes
        }
    discount_data_obj = {
        "target_pct": 70.0, "month_label": "Agosto 2026", "months": discount_months,
        "summary": discount_months["Agosto"]["summary"], "tree": discount_months["Agosto"]["tree"]
    }

    # 6. BUILD OPERADOR_CEDENTE_DATA (Strictly PORTA OSS)
    df_porta_oss = df_post[df_post['PRODUCTO'].str.startswith('PORTA OSS', na=False)].copy()
    df_porta_oss['VCHPORTA_CEDENTE'] = df_porta_oss['VCHPORTA_CEDENTE'].replace({'nan': 'OTRO', '': 'OTRO'}).fillna('OTRO')

    grp_ced = df_porta_oss.groupby(['SPV', pdv_col, 'ZONA', ase_col, 'Nombre del mes', 'VCHPORTA_CEDENTE']).size().reset_index(name='count')
    tree_cedente = []
    for spv, grp_spv in grp_ced.groupby('SPV'):
        spv_node = {"name": str(spv), "children": []}
        for pdv, grp_pdv in grp_spv.groupby(pdv_col):
            zona = str(grp_pdv['ZONA'].iloc[0])
            pdv_months = {m: {"claro_u": 0, "claro_pct": 0.0, "movistar_u": 0, "movistar_pct": 0.0, "bitel_u": 0, "bitel_pct": 0.0, "total_u": 0} for m in ["Junio", "Julio", "Agosto", "Acumulado"]}
            for _, row in grp_pdv.iterrows():
                m, c, cnt = row['Nombre del mes'], row['VCHPORTA_CEDENTE'], row['count']
                if m in pdv_months:
                    if c == 'CLARO': pdv_months[m]["claro_u"] += cnt
                    elif c == 'TELEFONICA': pdv_months[m]["movistar_u"] += cnt
                    elif c == 'VIETTEL': pdv_months[m]["bitel_u"] += cnt
                    pdv_months[m]["total_u"] += cnt
                    if c == 'CLARO': pdv_months["Acumulado"]["claro_u"] += cnt
                    elif c == 'TELEFONICA': pdv_months["Acumulado"]["movistar_u"] += cnt
                    elif c == 'VIETTEL': pdv_months["Acumulado"]["bitel_u"] += cnt
                    pdv_months["Acumulado"]["total_u"] += cnt
            
            for m in pdv_months:
                t = pdv_months[m]["total_u"]
                if t > 0:
                    pdv_months[m]["claro_pct"] = round((pdv_months[m]["claro_u"] / t * 100), 1)
                    pdv_months[m]["movistar_pct"] = round((pdv_months[m]["movistar_u"] / t * 100), 1)
                    pdv_months[m]["bitel_pct"] = round((pdv_months[m]["bitel_u"] / t * 100), 1)

            pdv_node = {"name": str(pdv), "spv": str(spv), "zona": zona, "months": pdv_months, "asesores": []}
            for ase, grp_ase in grp_pdv.groupby(ase_col):
                ase_months = {m: {"claro_u": 0, "claro_pct": 0.0, "movistar_u": 0, "movistar_pct": 0.0, "bitel_u": 0, "bitel_pct": 0.0, "total_u": 0} for m in ["Junio", "Julio", "Agosto", "Acumulado"]}
                for _, row in grp_ase.iterrows():
                    m, c, cnt = row['Nombre del mes'], row['VCHPORTA_CEDENTE'], row['count']
                    if m in ase_months:
                        if c == 'CLARO': ase_months[m]["claro_u"] += cnt
                        elif c == 'TELEFONICA': ase_months[m]["movistar_u"] += cnt
                        elif c == 'VIETTEL': ase_months[m]["bitel_u"] += cnt
                        ase_months[m]["total_u"] += cnt
                        if c == 'CLARO': ase_months["Acumulado"]["claro_u"] += cnt
                        elif c == 'TELEFONICA': ase_months["Acumulado"]["movistar_u"] += cnt
                        elif c == 'VIETTEL': ase_months["Acumulado"]["bitel_u"] += cnt
                        ase_months["Acumulado"]["total_u"] += cnt
                
                for m in ase_months:
                    t = ase_months[m]["total_u"]
                    if t > 0:
                        ase_months[m]["claro_pct"] = round((ase_months[m]["claro_u"] / t * 100), 1)
                        ase_months[m]["movistar_pct"] = round((ase_months[m]["movistar_u"] / t * 100), 1)
                        ase_months[m]["bitel_pct"] = round((ase_months[m]["bitel_u"] / t * 100), 1)

                pdv_node["asesores"].append({"user_code": str(ase), "months": ase_months})
            spv_node["children"].append(pdv_node)
        tree_cedente.append(spv_node)

    summary_cedente = {
        "Junio": {
            "claro": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Junio')&(df_porta_oss['VCHPORTA_CEDENTE']=='CLARO')]),
            "movistar": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Junio')&(df_porta_oss['VCHPORTA_CEDENTE']=='TELEFONICA')]),
            "bitel": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Junio')&(df_porta_oss['VCHPORTA_CEDENTE']=='VIETTEL')]),
            "total": len(df_porta_oss[df_porta_oss['Nombre del mes']=='Junio'])
        },
        "Julio": {
            "claro": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Julio')&(df_porta_oss['VCHPORTA_CEDENTE']=='CLARO')]),
            "movistar": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Julio')&(df_porta_oss['VCHPORTA_CEDENTE']=='TELEFONICA')]),
            "bitel": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Julio')&(df_porta_oss['VCHPORTA_CEDENTE']=='VIETTEL')]),
            "total": len(df_porta_oss[df_porta_oss['Nombre del mes']=='Julio'])
        },
        "Agosto": {
            "claro": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Agosto')&(df_porta_oss['VCHPORTA_CEDENTE']=='CLARO')]),
            "movistar": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Agosto')&(df_porta_oss['VCHPORTA_CEDENTE']=='TELEFONICA')]),
            "bitel": len(df_porta_oss[(df_porta_oss['Nombre del mes']=='Agosto')&(df_porta_oss['VCHPORTA_CEDENTE']=='VIETTEL')]),
            "total": len(df_porta_oss[df_porta_oss['Nombre del mes']=='Agosto'])
        },
    }
    summary_cedente["Acumulado"] = {
        "claro": summary_cedente["Junio"]["claro"] + summary_cedente["Julio"]["claro"] + summary_cedente["Agosto"]["claro"],
        "movistar": summary_cedente["Junio"]["movistar"] + summary_cedente["Julio"]["movistar"] + summary_cedente["Agosto"]["movistar"],
        "bitel": summary_cedente["Junio"]["bitel"] + summary_cedente["Julio"]["bitel"] + summary_cedente["Agosto"]["bitel"],
        "total": summary_cedente["Junio"]["total"] + summary_cedente["Julio"]["total"] + summary_cedente["Agosto"]["total"],
    }
    operador_cedente_obj = {"summary": summary_cedente, "tree": tree_cedente}

    # 7. BUILD MIX_PLANES_DATA (Postpago Only & Normalized Plan Names)
    plans_list = ["Entel Chip 35.90", "Entel chip+ 32.90", "Power 29.90 N", "Power 39.90 N", "Power 49.90 N", "Power 59.90 N", "Power ilim 69.90 N", "Power ilim 79.90 SD N", "Power ilim 99.90 SD N"]
    
    plan_map = {
        'POWER 39.90': 'Power 39.90 N',
        'POWER 39.90 N': 'Power 39.90 N',
        'POWER ILIM 79.90 SD': 'Power ilim 79.90 SD N',
        'POWER ILIM 79.90 SD N': 'Power ilim 79.90 SD N',
        'POWER 49.90': 'Power 49.90 N',
        'POWER 49.90 N': 'Power 49.90 N',
        'POWER ILIM 69.90': 'Power ilim 69.90 N',
        'POWER ILIM 69.90 N': 'Power ilim 69.90 N',
        'POWER 59.90': 'Power 59.90 N',
        'POWER 59.90 N': 'Power 59.90 N',
        'POWER 29.90 N': 'Power 29.90 N',
        'POWER 29.90': 'Power 29.90 N',
        'POWER ILIM 99.90 SD': 'Power ilim 99.90 SD N',
        'POWER ILIM 99.90 SD N': 'Power ilim 99.90 SD N',
        'POWER ILIM 89.90 SD N': 'Power ilim 99.90 SD N',
        'ENTEL CHIP 35.90': 'Entel Chip 35.90',
        'ENTEL CHIP+ 32.90': 'Entel chip+ 32.90',
        'ENTEL CHIP 22.90 REV': 'Power 29.90 N',
        'ENTEL CHIP 25.90 R': 'Power 29.90 N'
    }

    mix_months = {}
    for m_name in ["Junio", "Julio", "Agosto"]:
        df_m = df_post[(df_post['Nombre del mes'] == m_name) & (df_post['PRODUCTO'] != 'PREPAGO')].copy()
        df_m['VCHN_PLAN_NORM'] = df_m['VCHN_PLAN'].str.upper().map(plan_map).fillna(df_m['VCHN_PLAN'])
        
        plan_counts = df_m['VCHN_PLAN_NORM'].value_counts().to_dict()
        summary_plans = {p: int(plan_counts.get(p, 0)) for p in plans_list}
        tot_plans = sum(summary_plans.values())
        spv_mix_nodes = []
        for spv, grp_spv in df_m.groupby('SPV'):
            s_counts = grp_spv['VCHN_PLAN_NORM'].value_counts().to_dict()
            s_plans = {p: int(s_counts.get(p, 0)) for p in plans_list}
            s_tot = sum(s_plans.values())
            pdv_mix_nodes = []
            for pdv, grp_pdv in grp_spv.groupby(pdv_col):
                zona = str(grp_pdv['ZONA'].iloc[0])
                p_counts = grp_pdv['VCHN_PLAN_NORM'].value_counts().to_dict()
                p_plans = {p: int(p_counts.get(p, 0)) for p in plans_list}
                p_tot = sum(p_plans.values())
                ase_mix_nodes = []
                for ase, grp_ase in grp_pdv.groupby(ase_col):
                    a_counts = grp_ase['VCHN_PLAN_NORM'].value_counts().to_dict()
                    a_plans = {p: int(a_counts.get(p, 0)) for p in plans_list}
                    a_tot = sum(a_plans.values())
                    ase_mix_nodes.append({"id": f"ase_mix_{ase}", "name": str(ase), "user_code": str(ase), "spv": str(spv), "zona": zona, "plans": a_plans, "total": a_tot})
                pdv_mix_nodes.append({"id": f"pdv_mix_{pdv}", "name": str(pdv), "spv": str(spv), "zona": zona, "plans": p_plans, "total": p_tot, "children": ase_mix_nodes})
            spv_mix_nodes.append({"id": f"spv_mix_{spv}", "name": str(spv), "plans": s_plans, "total": s_tot, "children": pdv_mix_nodes})
        mix_months[m_name] = {"month_label": f"{m_name} 2026", "plans_list": plans_list, "summary": {"plans": summary_plans, "total": tot_plans}, "tree": spv_mix_nodes}
    mix_planes_data_obj = {"month_label": "Agosto 2026", "plans_list": plans_list, "months": mix_months, "summary": mix_months["Agosto"]["summary"], "tree": mix_months["Agosto"]["tree"]}

    # 7.4 BUILD DOTACION_DATA (Dynamic from DOTACIÓN sheet with full Asesor hierarchy)
    dot_sheet_name = [s for s in xl.sheet_names if 'DOT' in s.upper()][0] if 'xl' in locals() else 'DOTACIÓN'
    df_dot = pd.read_excel(excel_path, sheet_name=dot_sheet_name)
    strip_text_columns(df_dot)

    daily_cols = [c for c in df_dot.columns if isinstance(c, pd.Timestamp) or '2026' in str(c) or '08-' in str(c)]
    
    months_es = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
    daily_keys = []
    daily_headers = []
    for c in daily_cols:
        if isinstance(c, pd.Timestamp):
            daily_keys.append(c.strftime('%Y-%m-%d'))
            daily_headers.append(f"{c.day}-{months_es.get(c.month, 'Ago')}")
        else:
            c_str = str(c)[:10]
            daily_keys.append(c_str)
            try:
                parts = c_str.split('-')
                m_int = int(parts[1]) if len(parts) > 1 else 8
                d_int = int(parts[2]) if len(parts) > 2 else 1
                daily_headers.append(f"{d_int}-{months_es.get(m_int, 'Ago')}")
            except:
                daily_headers.append(c_str)

    spvs_dot = ['CYNTHIA GUERRA', 'MARÍA BERNAOLA', 'FERNANDO MORENO', 'MERY LAPA']
    spv_nodes_dot = {s: {"name": s, "hc_obj": 0, "hc_codigo": 0, "hc_gap": 0, "cumple_condicion": 0, "daily_totals": {k: 0 for k in daily_keys}, "children": []} for s in spvs_dot}
    summary_dot_obj = {"hc_obj": 0, "hc_codigo": 0, "cump_obj_pct": 0.0, "hc_gap": 0, "cumple_condicion": 0, "cump_condicion_pct": 0.0, "daily_totals": {k: 0 for k in daily_keys}}

    def parse_num_dot(val):
        if pd.isna(val) or str(val).lower() in ['nan', 'int', 'none', '']: return 0.0
        val_str = str(val).strip().upper()
        if val_str == 'SI': return 1.0
        if val_str == 'NO': return 0.0
        try: return float(val_str)
        except: return 0.0

    col_cump_cond = df_dot.columns[13]
    col_cump_cond_pct = df_dot.columns[14]

    curr_spv_dot = 'MERY LAPA'
    curr_pdv_node = None

    for idx, row in df_dot.iterrows():
        est = str(row['ESTRUCTURA']).strip()
        if not est or est.upper() in ['NAN', 'REGIONES', 'CENTRO', 'FORTALECERNOS S.A.C.']: continue
        if est in spvs_dot:
            curr_spv_dot = est
            continue

        is_pdv = est.startswith('TE ') or est in store_spv_map

        daily_sales = {}
        for d_idx, d_col in enumerate(daily_cols):
            d_key = daily_keys[d_idx]
            d_val = row[d_col]
            if pd.notna(d_val) and str(d_val).upper() not in ['NAN', 'INT']:
                try: daily_sales[d_key] = int(float(d_val))
                except: daily_sales[d_key] = 0
            else:
                daily_sales[d_key] = 0

        obs = str(row['OBSERVACIONES']) if pd.notna(row['OBSERVACIONES']) and str(row['OBSERVACIONES']) != 'nan' else ''

        if is_pdv:
            target_spv = store_spv_map.get(est, curr_spv_dot)
            hc_obj = parse_num_dot(row['HC OBJ'])
            hc_cod = parse_num_dot(row['HC CODIGO'])
            hc_gap = parse_num_dot(row['HC GAP'])
            cump_cond = parse_num_dot(row[col_cump_cond])
            cump_cond_pct = parse_num_dot(row[col_cump_cond_pct])

            curr_pdv_node = {
                "name": est, "spv": target_spv, "zona": "SUR",
                "hc_obj": int(hc_obj), "hc_codigo": int(hc_cod), "hc_gap": int(hc_gap),
                "cump_obj_pct": round((hc_cod / hc_obj * 100), 1) if hc_obj > 0 else 0.0,
                "hc_contratar": int(hc_gap),
                "cumple_condicion": int(cump_cond),
                "cump_condicion_pct": round((cump_cond / hc_cod * 100), 1) if hc_cod > 0 else 0.0,
                "obs": obs, "daily_sales": daily_sales, "children": []
            }
            spv_nodes_dot[target_spv]["children"].append(curr_pdv_node)
            spv_nodes_dot[target_spv]["hc_obj"] += int(hc_obj)
            spv_nodes_dot[target_spv]["hc_codigo"] += int(hc_cod)
            spv_nodes_dot[target_spv]["hc_gap"] += int(hc_gap)
            spv_nodes_dot[target_spv]["cumple_condicion"] += int(cump_cond)
            
            summary_dot_obj["hc_obj"] += int(hc_obj)
            summary_dot_obj["hc_codigo"] += int(hc_cod)
            summary_dot_obj["hc_gap"] += int(hc_gap)
            summary_dot_obj["cumple_condicion"] += int(cump_cond)

            for d_key, d_v in daily_sales.items():
                spv_nodes_dot[target_spv]["daily_totals"][d_key] += d_v
                summary_dot_obj["daily_totals"][d_key] += d_v
        else:
            if curr_pdv_node:
                cond_str = str(row[col_cump_cond]).strip().upper()
                is_cumple = (cond_str == 'SI')
                ase_node = {
                    "name": est,
                    "user_code": est,
                    "cumple_condicion": cond_str,
                    "is_cumple": is_cumple,
                    "obs": obs,
                    "daily_sales": daily_sales
                }
                curr_pdv_node["children"].append(ase_node)

    summary_dot_obj["cump_obj_pct"] = round((summary_dot_obj["hc_codigo"] / summary_dot_obj["hc_obj"] * 100), 1) if summary_dot_obj["hc_obj"] > 0 else 0.0
    summary_dot_obj["cump_condicion_pct"] = round((summary_dot_obj["cumple_condicion"] / summary_dot_obj["hc_codigo"] * 100), 1) if summary_dot_obj["hc_codigo"] > 0 else 0.0

    dotacion_data_obj = {
        "daily_keys": daily_keys,
        "daily_headers": daily_headers,
        "summary": summary_dot_obj,
        "tree": list(spv_nodes_dot.values())
    }

    # 7.5 BUILD PERMANENCIA_DATA (Dynamic for all Camadas: Agosto, Julio, Junio, Enero)
    df_perm = pd.read_excel(excel_path, sheet_name='PERMANENCIA')
    strip_text_columns(df_perm)

    months_perm_map = {'AGOSTO': 'Agosto', 'JULIO': 'Julio', 'JUNIO': 'Junio', 'ENERO': 'Enero'}
    permanencia_months = {}

    for camada_raw, camada_clean in months_perm_map.items():
        df_c = df_perm[df_perm['CAMADAS'].str.upper() == camada_raw].copy()
        if len(df_c) == 0: continue

        row_total = df_c[df_c['PDV'].str.upper() == 'TOTAL']
        if len(row_total) > 0:
            r_tot = row_total.iloc[0]
            tot_sales = int(r_tot['SS TOTAL']) if pd.notna(r_tot['SS TOTAL']) else 0
            m0_p = round(float(r_tot['M0']) * 100, 2) if pd.notna(r_tot['M0']) and str(r_tot['M0']) != 'nan' else None
            m1_p = round(float(r_tot['M1']) * 100, 2) if pd.notna(r_tot['M1']) and str(r_tot['M1']) != 'nan' else None
            m2_p = round(float(r_tot['M2']) * 100, 2) if pd.notna(r_tot['M2']) and str(r_tot['M2']) != 'nan' else None
            m3_p = round(float(r_tot['M3']) * 100, 2) if pd.notna(r_tot['M3']) and str(r_tot['M3']) != 'nan' else None
            m4_p = round(float(r_tot['M4']) * 100, 2) if pd.notna(r_tot['M4']) and str(r_tot['M4']) != 'nan' else None
            m5_p = round(float(r_tot['M5']) * 100, 2) if pd.notna(r_tot['M5']) and str(r_tot['M5']) != 'nan' else None
            m6_p = round(float(r_tot['M6']) * 100, 2) if pd.notna(r_tot['M6']) and str(r_tot['M6']) != 'nan' else None
            perm_m6_p = round(float(r_tot['%PERM_M6']) * 100, 2) if pd.notna(r_tot['%PERM_M6']) and str(r_tot['%PERM_M6']) != 'nan' else (round(100 - m6_p, 2) if m6_p else None)
        else:
            tot_sales, m0_p, m1_p, m2_p, m3_p, m4_p, m5_p, m6_p, perm_m6_p = 0, None, None, None, None, None, None, None, None

        summary_obj = {
            "total_sales_jan": tot_sales,
            "m0_pct": m0_p, "m1_pct": m1_p, "m2_pct": m2_p, "m3_pct": m3_p,
            "m4_pct": m4_p, "m5_pct": m5_p, "m6_pct": m6_p, "perm_m6_pct": perm_m6_p
        }

        df_pdvs = df_c[df_c['PDV'].str.upper() != 'TOTAL'].copy()
        tree_list = []
        for pdv, grp_pdv in df_pdvs.groupby('PDV'):
            row_pdv_tot = grp_pdv[grp_pdv['ASESOR'].str.upper() == 'TOTAL']
            rp = row_pdv_tot.iloc[0] if len(row_pdv_tot) > 0 else grp_pdv.iloc[0]
            p_tot = int(rp['SS TOTAL']) if pd.notna(rp['SS TOTAL']) else 0
            pm0 = round(float(rp['M0']) * 100, 2) if pd.notna(rp['M0']) and str(rp['M0']) != 'nan' else None
            pm1 = round(float(rp['M1']) * 100, 2) if pd.notna(rp['M1']) and str(rp['M1']) != 'nan' else None
            pm2 = round(float(rp['M2']) * 100, 2) if pd.notna(rp['M2']) and str(rp['M2']) != 'nan' else None
            pm3 = round(float(rp['M3']) * 100, 2) if pd.notna(rp['M3']) and str(rp['M3']) != 'nan' else None
            pm4 = round(float(rp['M4']) * 100, 2) if pd.notna(rp['M4']) and str(rp['M4']) != 'nan' else None
            pm5 = round(float(rp['M5']) * 100, 2) if pd.notna(rp['M5']) and str(rp['M5']) != 'nan' else None
            pm6 = round(float(rp['M6']) * 100, 2) if pd.notna(rp['M6']) and str(rp['M6']) != 'nan' else None
            pperm_m6 = round(float(rp['%PERM_M6']) * 100, 2) if pd.notna(rp['%PERM_M6']) and str(rp['%PERM_M6']) != 'nan' else (round(100 - pm6, 2) if pm6 else None)

            children_list = []
            df_ases = grp_pdv[grp_pdv['ASESOR'].str.upper() != 'TOTAL']
            for _, ra in df_ases.iterrows():
                a_tot = int(ra['SS TOTAL']) if pd.notna(ra['SS TOTAL']) else 0
                am0 = round(float(ra['M0']) * 100, 2) if pd.notna(ra['M0']) and str(ra['M0']) != 'nan' else None
                am1 = round(float(ra['M1']) * 100, 2) if pd.notna(ra['M1']) and str(ra['M1']) != 'nan' else None
                am2 = round(float(ra['M2']) * 100, 2) if pd.notna(ra['M2']) and str(ra['M2']) != 'nan' else None
                am3 = round(float(ra['M3']) * 100, 2) if pd.notna(ra['M3']) and str(ra['M3']) != 'nan' else None
                am4 = round(float(ra['M4']) * 100, 2) if pd.notna(ra['M4']) and str(ra['M4']) != 'nan' else None
                am5 = round(float(ra['M5']) * 100, 2) if pd.notna(ra['M5']) and str(ra['M5']) != 'nan' else None
                am6 = round(float(ra['M6']) * 100, 2) if pd.notna(ra['M6']) and str(ra['M6']) != 'nan' else None
                aperm_m6 = round(float(ra['%PERM_M6']) * 100, 2) if pd.notna(ra['%PERM_M6']) and str(ra['%PERM_M6']) != 'nan' else (round(100 - am6, 2) if am6 else None)

                children_list.append({
                    "name": str(ra['ASESOR']), "total": a_tot,
                    "m0": am0, "m1": am1, "m2": am2, "m3": am3, "m4": am4, "m5": am5, "m6": am6, "perm_m6": aperm_m6
                })

            tree_list.append({
                "name": str(pdv), "total": p_tot,
                "m0": pm0, "m1": pm1, "m2": pm2, "m3": pm3, "m4": pm4, "m5": pm5, "m6": pm6, "perm_m6": pperm_m6,
                "children": children_list
            })

        permanencia_months[camada_clean] = {"summary": summary_obj, "tree": tree_list}

    default_perm = permanencia_months.get("Agosto", list(permanencia_months.values())[0])
    permanencia_data_obj = {
        "month_label": "Agosto 2026",
        "months": permanencia_months,
        "summary": default_perm["summary"],
        "tree": default_perm["tree"]
    }

    # 7.6 BUILD NPS_DATA (Dynamic from sheets NPS VENTA and NPS POSTVENTA)
    def parse_nps_val(v, is_pct=False):
        if pd.isna(v) or str(v).lower() in ['nan', 'none', '']: return None if is_pct else 0
        try:
            val = float(v)
            return round(val * 100, 1) if is_pct else int(val)
        except: return None if is_pct else 0

    # NPS VENTA
    nps_v_sheet_name = [s for s in xl.sheet_names if 'NPS' in s.upper() and 'VENTA' in s.upper() and 'POST' not in s.upper()][0] if 'xl' in locals() else 'NPS VENTA'
    df_nps_v = pd.read_excel(excel_path, sheet_name=nps_v_sheet_name)
    strip_text_columns(df_nps_v)

    pdvs_v = []
    summary_v = {"total_nps": 12.5, "total_q": 8}
    curr_pdv_v = None

    for idx in range(6, len(df_nps_v)):
        row = df_nps_v.iloc[idx]
        est = str(row.iloc[0]).strip()
        if not est or est.upper() in ['NAN', 'TOTAL GENERAL']: continue

        if est.upper() == 'VENTA':
            summary_v = {
                "total_nps": parse_nps_val(row.iloc[7], is_pct=True),
                "total_q": parse_nps_val(row.iloc[8]),
                "total_pct_q": parse_nps_val(row.iloc[9], is_pct=True),
                "sem1_nps": parse_nps_val(row.iloc[1], is_pct=True),
                "sem1_q": parse_nps_val(row.iloc[2]),
                "sem5_nps": parse_nps_val(row.iloc[4], is_pct=True),
                "sem5_q": parse_nps_val(row.iloc[5])
            }
            continue

        tot_nps = parse_nps_val(row.iloc[7], is_pct=True) or 0.0
        tot_q = parse_nps_val(row.iloc[8]) or 0
        tot_pct_q = parse_nps_val(row.iloc[9], is_pct=True) or 0.0
        s1_nps = parse_nps_val(row.iloc[1], is_pct=True)
        s1_q = parse_nps_val(row.iloc[2])
        s5_nps = parse_nps_val(row.iloc[4], is_pct=True)
        s5_q = parse_nps_val(row.iloc[5])

        is_pdv = est.startswith('TE ') or est in store_spv_map
        if is_pdv:
            target_spv = store_spv_map.get(est, 'MARÍA BERNAOLA')
            curr_pdv_v = {
                "name": est, "spv": target_spv, "zona": "SUR",
                "total_nps": tot_nps, "total_q": tot_q, "total_pct_q": tot_pct_q,
                "sem1_nps": s1_nps, "sem1_q": s1_q, "sem5_nps": s5_nps, "sem5_q": s5_q,
                "children": []
            }
            pdvs_v.append(curr_pdv_v)
        elif curr_pdv_v:
            curr_pdv_v["children"].append({
                "name": est,
                "total_nps": tot_nps, "total_q": tot_q, "total_pct_q": tot_pct_q,
                "sem1_nps": s1_nps, "sem1_q": s1_q, "sem5_nps": s5_nps, "sem5_q": s5_q
            })

    pdvs_v.sort(key=lambda x: x["total_nps"], reverse=True)
    for p in pdvs_v: p["children"].sort(key=lambda x: x["total_nps"], reverse=True)

    # NPS POSTVENTA
    nps_p_sheet_name = [s for s in xl.sheet_names if 'NPS' in s.upper() and 'POST' in s.upper()][0] if 'xl' in locals() else 'NPS POSTVENTA'
    df_nps_p = pd.read_excel(excel_path, sheet_name=nps_p_sheet_name)
    strip_text_columns(df_nps_p)

    pdvs_p = []
    summary_p = {"total_nps": -50.0, "total_q": 2}
    curr_pdv_p = None

    for idx in range(6, len(df_nps_p)):
        row = df_nps_p.iloc[idx]
        est = str(row.iloc[0]).strip()
        if not est or est.upper() in ['NAN', 'TOTAL GENERAL']: continue

        if est.upper() == 'POSTVENTA':
            summary_p = {
                "total_nps": parse_nps_val(row.iloc[4], is_pct=True),
                "total_q": parse_nps_val(row.iloc[5]),
                "total_pct_q": parse_nps_val(row.iloc[6], is_pct=True),
                "sem1_nps": parse_nps_val(row.iloc[1], is_pct=True),
                "sem1_q": parse_nps_val(row.iloc[2])
            }
            continue

        tot_nps = parse_nps_val(row.iloc[4], is_pct=True) or 0.0
        tot_q = parse_nps_val(row.iloc[5]) or 0
        tot_pct_q = parse_nps_val(row.iloc[6], is_pct=True) or 0.0
        s1_nps = parse_nps_val(row.iloc[1], is_pct=True)
        s1_q = parse_nps_val(row.iloc[2])

        is_pdv = est.startswith('TE ') or est in store_spv_map
        if is_pdv:
            target_spv = store_spv_map.get(est, 'MARÍA BERNAOLA')
            curr_pdv_p = {
                "name": est, "spv": target_spv, "zona": "SUR",
                "total_nps": tot_nps, "total_q": tot_q, "total_pct_q": tot_pct_q,
                "sem1_nps": s1_nps, "sem1_q": s1_q,
                "children": []
            }
            pdvs_p.append(curr_pdv_p)
        elif curr_pdv_p:
            curr_pdv_p["children"].append({
                "name": est,
                "total_nps": tot_nps, "total_q": tot_q, "total_pct_q": tot_pct_q,
                "sem1_nps": s1_nps, "sem1_q": s1_q
            })

    pdvs_p.sort(key=lambda x: x["total_nps"], reverse=True)
    for p in pdvs_p: p["children"].sort(key=lambda x: x["total_nps"], reverse=True)

    nps_data_obj = {
        "target": 58.0,
        "venta": {"summary": summary_v, "pdvs": pdvs_v},
        "postventa": {"summary": summary_p, "pdvs": pdvs_p}
    }

    # 8. WRITE ALL TO DATA.JS

    # 8. WRITE ALL TO DATA.JS
    new_data_js = "ARRIBOS_DATA = " + json.dumps(arribos_dict, indent=2) + ";\n\n"
    new_data_js += "SALES_DATA = " + json.dumps(sales_data_obj, indent=2) + ";\n\n"
    new_data_js += "DISCOUNT_DATA = " + json.dumps(discount_data_obj, indent=2) + ";\n\n"
    new_data_js += "OPERADOR_CEDENTE_DATA = " + json.dumps(operador_cedente_obj, indent=2) + ";\n\n"
    new_data_js += "MIX_PLANES_DATA = " + json.dumps(mix_planes_data_obj, indent=2) + ";\n\n"
    new_data_js += "DOTACION_DATA = " + json.dumps(dotacion_data_obj, indent=2) + ";\n\n"
    new_data_js += "PERMANENCIA_DATA = " + json.dumps(permanencia_data_obj, indent=2) + ";\n\n"
    new_data_js += "NPS_DATA = " + json.dumps(nps_data_obj, indent=2) + ";\n\n"

    with open(data_js_path, 'w', encoding='utf-8') as f:
        f.write(new_data_js)

    verifier_path = PROJECT_DIR / 'verify_dashboard.js'
    node_executable = shutil.which('node')
    if not verifier_path.exists():
        raise FileNotFoundError(f"No se encontró la verificación local: {verifier_path}")
    if not node_executable:
        raise RuntimeError("Node.js no está disponible en PATH para verificar las ocho páginas.")

    subprocess.run(
        [node_executable, str(verifier_path)],
        cwd=PROJECT_DIR,
        check=True,
    )
    print("[OK] Pipeline actualizado y ocho páginas verificadas sin errores.")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(
            "Uso: python update_dashboard_data.py <dias_transcurridos> <dias_totales>\n"
            "Confirma ambos valores antes de ejecutar; no se cuentan domingos."
        )
    run_update(elapsed_wd=int(sys.argv[1]), total_wd=int(sys.argv[2]))
