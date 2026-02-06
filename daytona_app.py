import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import os
import time
import re
import statistics
import unicodedata

# -------------------------
# CONFIGURACIÓN PÁGINA
# -------------------------
st.set_page_config(page_title="Daytona Financial Intelligence", layout="wide", page_icon="🚗")

st.markdown(
    """
    <style>
    @media print {
        .stApp header {display: none;}
    }
    .block-container {
        padding-top: 1rem;
    }
    button {display: none;}
    .stSidebar {display: block;}
    footer {display: none;}
    .footer-text {
        font-size: 12px;
        color: #888;
        text-align: center;
        margin-top: 50px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Daytona Financial Intelligence")
st.markdown("---")

# -------------------------
# FUNCIONES UTILITARIAS
# -------------------------
def normalizar_para_url(texto):
    if not isinstance(texto, str):
        return ""
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = re.sub(r"-+", "-", texto)
    return texto

def obtener_semaforo_por_dias(valor_celda):
    try:
        texto = str(valor_celda)
        numeros = re.findall(r"\d+", texto)
        if not numeros:
            return "", 0
        dias = int(numeros[0])
        if dias <= 30:
            return "🟢", dias
        elif dias <= 89:
            return "🟡", dias
        else:
            return "🔴", dias
    except:
        return "", 0

def analizar_vehiculo(marca, modelo, anio, ver_navegador):
    if not marca or not modelo or not anio:
        return 0, 0, "Datos incompletos", "", 0, 0

    marca_url = normalizar_para_url(marca)
    modelo_url = normalizar_para_url(modelo)

    try:
        anio_str = str(int(float(anio)))
    except:
        return 0, 0, "Error Año", "", 0, 0

    url = f"https://autos.mercadolibre.com.mx/{marca_url}/{modelo_url}/{anio_str}_NoIndex_True?VIEW=list"
    ruta_memoria = os.path.join(os.getcwd(), "mi_sesion_ml")
    precios_brutos = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=ruta_memoria,
                headless=not ver_navegador,
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = browser.pages[0]
            page.goto(url, timeout=30000)
            time.sleep(3.5)

            elementos = page.locator(".andes-money-amount__fraction").all_inner_texts()
            for t in elementos:
                limpio = t.replace(",", "").replace(".", "")
                try:
                    val = int(limpio)
                    if 50000 <= val <= 10000000:
                        precios_brutos.append(val)
                except:
                    pass

            browser.close()
    except Exception as e:
        return 0, 0, f"Error: {str(e)[:10]}", url, 0, 0

    if not precios_brutos:
        return 0, 0, "0 Resultados", url, 0, 0

    mediana_inicial = statistics.median(precios_brutos)
    precios_limpios = [
        p for p in precios_brutos
        if mediana_inicial * 0.6 <= p <= mediana_inicial * 1.6
    ]

    if not precios_limpios:
        precios_limpios = precios_brutos

    cantidad = len(precios_limpios)
    mediana_final = int(statistics.median(precios_limpios))
    precio_daytona = int(mediana_final * 0.95)
    min_mercado = min(precios_limpios)
    max_mercado = max(precios_limpios)

    return precio_daytona, cantidad, "Exitoso", url, min_mercado, max_mercado

# ----------------------------------------------------
# CARGA AUTOPRECIOS DESDE EXCEL
# ----------------------------------------------------
ruta_autoprecios = os.path.join(os.getcwd(), "autoprecios_lobato_catalogo.xls")

df_autoprecios = None
if os.path.exists(ruta_autoprecios):
    try:
        df_autoprecios = pd.read_excel(
            ruta_autoprecios,
            sheet_name="AUTOPRECIOS"
        )
        df_autoprecios.columns = df_autoprecios.columns.str.strip()
        df_autoprecios.columns = df_autoprecios.columns.str.upper()
    except Exception as e:
        st.sidebar.error(f"Error cargando AUTOPRECIOS ({ruta_autoprecios}): {str(e)[:80]}")
else:
    st.sidebar.warning(f"No se encontró el archivo en: {ruta_autoprecios}")

# -------------------------
# SIDEBAR
# -------------------------
with st.sidebar:
    try:
        st.image("https://www.grupodaytona.com/favicon.ico", width=50)
    except:
        st.write("Grupo Daytona")

    st.markdown("### Panel de Control")

    modo = st.radio(
        "Selecciona modo:",
        ["Analizar inventario", "Cotizar compra"],
        index=0
    )

st.sidebar.markdown("---")
st.sidebar.caption("2026 Grupo Daytona. Confidencial y exclusivo. Todos los derechos reservados.")

# =====================================================
# MODO 1: ANALIZAR INVENTARIO (EXCEL)
# =====================================================
if modo == "Analizar inventario":
    archivo = st.file_uploader("Carga Inventario Maestro Excel", type="xlsx")

    if archivo:
        df = pd.read_excel(archivo)
        df.columns = df.columns.str.strip()

        csubmarca = next((c for c in df.columns if "submarca" in c.lower()), None)
        cmodelolbl = next((c for c in df.columns if "modelo" in c.lower()), None)
        colnombreauto = csubmarca if csubmarca else cmodelolbl

        caniolbl = next(
            (c for c in df.columns if any(x in c.lower() for x in ["año", "year", "anho"])),
            None,
        )
        colanionum = cmodelolbl if (csubmarca and cmodelolbl) else caniolbl

        colversion = next(
            (c for c in df.columns if "versión" in c.lower() or "version" in c.lower()),
            None,
        )
        colprecio = next(
            (c for c in df.columns if "precio" in c.lower() or "venta" in c.lower()),
            None,
        )
        colcosto = next(
            (c for c in df.columns if any(x in c.lower() for x in ["costo", "compra", "inversion", "libro"])),
            None,
        )
        colsucursal = next(
            (c for c in df.columns if any(x in c.lower() for x in ["sucursal", "ubicacion", "agencia"])),
            None,
        )
        colid = next(
            (c for c in df.columns if any(x in c.lower() for x in ["id", "sku", "articulo"])),
            None,
        )
        coldias = next(
            (c for c in df.columns if any(x in c.lower() for x in ["dias", "days", "antiguedad", "stock", "inventario"])),
            None,
        )

        if not colversion:
            st.error("Falta columna Versión.")
        else:
            dffiltrado = df.copy()
            nombre_reporte = "General"

            if colsucursal:
                lista_sucursales = ["Todas"] + sorted(list(df[colsucursal].astype(str).unique()))
                seleccion = st.sidebar.selectbox("Filtrar Sucursal", lista_sucursales)
                if seleccion != "Todas":
                    dffiltrado = df[df[colsucursal] == seleccion]
                    nombre_reporte = seleccion
                    st.info(f"Reporte para {seleccion}")
                else:
                    st.info("Reporte Consolidado")
            else:
                st.info("Reporte Consolidado")

            modoprueba = st.sidebar.checkbox("Modo Prueba 3 autos", value=True)
            vernavegador = st.sidebar.checkbox("Ver navegador", value=True)
            st.sidebar.markdown("---")

            if st.button("INICIAR ESCANEO FINAL"):
                data = dffiltrado.head(3).copy() if modoprueba else dffiltrado.copy()
                barra = st.progress(0)
                res = []

                for idx, (_, row) in enumerate(data.iterrows()):
                    progreso = (idx + 1) / len(data)
                    if progreso > 1.0:
                        progreso = 1.0
                    barra.progress(progreso)

                    marca = row.get("Marca", "")
                    modelo = row.get(colnombreauto, "")
                    version = row.get(colversion, "")

                    raw_anio = row.get(colanionum, None)
                    anio_limpio = ""
                    anio_valido = False
                    try:
                        if pd.notna(raw_anio):
                            anio_limpio = str(int(float(raw_anio)))
                            if len(anio_limpio) == 4 and anio_limpio.isdigit():
                                anio_valido = True
                    except:
                        pass

                    if colprecio and isinstance(row[colprecio], (int, float)):
                        precio_act = row[colprecio]
                    else:
                        precio_act = 0

                    if colcosto and isinstance(row[colcosto], (int, float)):
                        costo_libro = row[colcosto]
                    else:
                        costo_libro = 0

                    val_id = row[colid] if colid else ""
                    val_sucursal = row[colsucursal] if colsucursal else ""

                    semaforo, dias_stock = ("", 0)
                    if coldias:
                        semaforo, dias_stock = obtener_semaforo_por_dias(row[coldias])

                    if not anio_valido:
                        res.append({
                            "ID": val_id,
                            "Sucursal": val_sucursal,
                            "S": semaforo,
                            "Diagnóstico": "❌ ERROR AÑO",
                            "Stock": dias_stock,
                            "Auto": f"{marca} {modelo}",
                            "Versión": version,
                            "Año": anio_limpio,
                            "Comp.": 0,
                            "Costo Real": costo_libro,
                            "Compra Sugerida": 0,
                            "Actual Venta": precio_act,
                            "Sugerido Venta": 0,
                            "Mínimo (Piso)": 0,
                            "Utilidad": 0,
                            "Link": "",
                            "Fecha": time.strftime('%Y-%m-%d')
                        })
                        continue

                    sugerido, num, estado, url_link, min_mercado, max_mercado = analizar_vehiculo(
                        marca,
                        modelo,
                        anio_limpio,
                        vernavegador
                    )

                    utilidad_esperada = 0
                    if sugerido and costo_libro:
                        utilidad_esperada = sugerido - costo_libro

                    if sugerido > 0:
                        compra_sugerida = int(sugerido * 0.88)
                    else:
                        compra_sugerida = 0

                    diagnostico = "OK"
                    if dias_stock > 90:
                        diagnostico = "🧊 CONGELADO"
                    elif costo_libro > 0 and sugerido > 0 and sugerido < costo_libro:
                        diagnostico = "⚠️ PÉRDIDA"
                    elif sugerido > precio_act and dias_stock < 30:
                        diagnostico = "💰 OPORTUNIDAD"

                    res.append({
                        "ID": val_id,
                        "Sucursal": val_sucursal,
                        "S": semaforo,
                        "Diagnóstico": diagnostico,
                        "Stock": dias_stock,
                        "Auto": f"{marca} {modelo}",
                        "Versión": version,
                        "Año": anio_limpio,
                        "Comp.": num,
                        "Costo Real": costo_libro,
                        "Compra Sugerida": compra_sugerida,
                        "Actual Venta": precio_act,
                        "Sugerido Venta": sugerido,
                        "Mínimo (Piso)": min_mercado,
                        "Utilidad": utilidad_esperada,
                        "Link": url_link,
                        "Fecha": time.strftime('%Y-%m-%d')
                    })
                    time.sleep(1.5)

                st.success("✅ Análisis Finalizado")
                df_r = pd.DataFrame(res)

                if not modoprueba:
                    archivo_historial = "historial_master_daytona.csv"
                    try:
                        cols_guardar = [c for c in df_r.columns if c not in ['Link', 'S', 'Diagnóstico']]
                        if os.path.exists(archivo_historial):
                            df_r[cols_guardar].to_csv(archivo_historial, mode='a', header=False, index=False)
                        else:
                            df_r[cols_guardar].to_csv(archivo_historial, index=False)
                    except:
                        pass

                st.header(f"Resumen Ejecutivo: {nombre_reporte}")
                total_inventario = df_r['Costo Real'].sum()
                total_utilidad = df_r['Utilidad'].sum()

                col1, col2, col3 = st.columns(3)
                col1.metric("Valor Inventario", f"${total_inventario:,.0f}")
                col2.metric("Utilidad Potencial", f"${total_utilidad:,.0f}")

                format_dict = {
                    "Costo Real": "${:,.0f}",
                    "Compra Sugerida": "${:,.0f}",
                    "Actual Venta": "${:,.0f}",
                    "Sugerido Venta": "${:,.0f}",
                    "Mínimo (Piso)": "${:,.0f}",
                    "Utilidad": "${:,.0f}"
                }

                def estilos_financieros(val):
                    if not isinstance(val, (int, float)):
                        return ''
                    if val < 0:
                        return 'color: red; font-weight: bold'
                    if val > 0:
                        return 'color: green; font-weight: bold'
                    return ''

                cols_visual = [c for c in df_r.columns if c not in ['Fecha']]

                st.dataframe(
                    df_r[cols_visual].style.format(format_dict).applymap(estilos_financieros, subset=['Utilidad']),
                    column_config={
                        "Link": st.column_config.LinkColumn("URL"),
                        "S": st.column_config.Column("S", width="small"),
                        "Comp.": st.column_config.NumberColumn(help="Autos similares en mercado"),
                        "Compra Sugerida": st.column_config.NumberColumn(help="Precio máx compra (12% margen)"),
                        "Costo Real": st.column_config.NumberColumn(help="Costo original de libro")
                    },
                    hide_index=True,
                    use_container_width=True
                )

                st.markdown(
                    "<div class='footer-text'>2026 Grupo Daytona · Información confidencial · Generado por Daytona Intelligence</div>",
                    unsafe_allow_html=True
                )
                st.markdown("---")

                nombre_csv = f"Daytona_Reporte_{nombre_reporte}_{time.strftime('%Y%m%d')}.csv"
                csv = df_r.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar Reporte CSV", csv, nombre_csv, "text/csv")

# =====================================================
# MODO 2: COTIZAR COMPRA (USANDO AUTOPRECIOS)
# =====================================================
if modo == "Cotizar compra":
    st.header("Cotizar Compra Seminuevos (por catálogo Autoprecios)")

    if df_autoprecios is None:
        st.error("No se pudo cargar AUTOPRECIOS. Verifica el archivo autoprecios_lobato_catalogo.xls y recarga la app.")
    else:
        columnas_necesarias = [
            "MARCA", "SUBMARCA", "VERSIÓN", "AÑO/MODELO",
            "ID", "PRECIO VENTA", "PRECIO COMPRA",
            "PRECIO_DE_LISTA_NUEVO", "PRECIO INTERMEDIO",
            "PRECIO AGENCIA CERTIFICADOS"
        ]
        for col in columnas_necesarias:
            if col not in df_autoprecios.columns:
                st.error(f"Falta la columna '{col}' en AUTOPRECIOS.")
                st.stop()

        # 1) Marca
        marcas = sorted(df_autoprecios["MARCA"].dropna().astype(str).unique())
        marca_sel = st.selectbox("Marca", ["(elige una)"] + marcas)

        df_marca = df_autoprecios.copy()
        if marca_sel != "(elige una)":
            df_marca = df_marca[df_marca["MARCA"] == marca_sel]

        # 2) Submarca / Modelo
        submarcas = sorted(df_marca["SUBMARCA"].dropna().astype(str).unique())
        submarca_sel = st.selectbox("Submarca / Modelo", ["(elige una)"] + submarcas)

        df_submarca = df_marca.copy()
        if submarca_sel != "(elige una)":
            df_submarca = df_submarca[df_submarca["SUBMARCA"] == submarca_sel]

        # 3) Año / Modelo (filtra por Marca + Submarca)
        anios_raw = df_submarca["AÑO/MODELO"].dropna().unique()
        anios = []
        for a in anios_raw:
            try:
                val = str(int(float(a)))
                if len(val) == 4:
                    anios.append(val)
            except:
                pass
        anios = sorted(list(set(anios)))
        anio_sel = st.selectbox("Año / Modelo", ["(elige uno)"] + anios)

        df_anio = df_submarca.copy()
        if anio_sel != "(elige uno)":
            def normalizar_anio(x):
                try:
                    if pd.notna(x):
                        return str(int(float(x)))
                except:
                    return ""
                return ""

            df_anio = df_anio.copy()
            df_anio["ANIO_STR"] = df_anio["AÑO/MODELO"].apply(normalizar_anio)
            df_anio = df_anio[df_anio["ANIO_STR"] == anio_sel]

        # 4) Versión (solo las de ese año)
        versiones = sorted(df_anio["VERSIÓN"].dropna().astype(str).unique()) if not df_anio.empty else []
        version_sel = st.selectbox("Versión", ["(elige una)"] + versiones)

        ver_navegador = st.checkbox("Ver navegador (MercadoLibre)", value=True)

        if st.button("COTIZAR ESTA CONFIGURACIÓN"):
            if (
                marca_sel == "(elige una)"
                or submarca_sel == "(elige una)"
                or anio_sel == "(elige uno)"
                or version_sel == "(elige una)"
            ):
                st.warning("Completa Marca, Submarca, Año y Versión para cotizar.")
            else:
                # 1) Fila exacta de AUTOPRECIOS
                df_match = df_autoprecios.copy()

                def normalizar_anio(x):
                    try:
                        if pd.notna(x):
                            return str(int(float(x)))
                    except:
                        return ""
                    return ""

                df_match["ANIO_STR"] = df_match["AÑO/MODELO"].apply(normalizar_anio)

                df_match = df_match[
                    (df_match["MARCA"] == marca_sel) &
                    (df_match["SUBMARCA"] == submarca_sel) &
                    (df_match["VERSIÓN"] == version_sel) &
                    (df_match["ANIO_STR"] == anio_sel)
                ]

                if df_match.empty:
                    st.error("No encontré en AUTOPRECIOS una fila que coincida exactamente con Marca/Submarca/Año/Versión seleccionados.")
                    st.stop()

                fila = df_match.iloc[0]

                id_auto = fila.get("ID", "")
                precio_venta_cat = fila.get("PRECIO VENTA", 0)
                precio_compra_cat = fila.get("PRECIO COMPRA", 0)
                precio_lista_nuevo = fila.get("PRECIO_DE_LISTA_NUEVO", 0)
                precio_intermedio = fila.get("PRECIO INTERMEDIO", 0)
                precio_ag_cert = fila.get("PRECIO AGENCIA CERTIFICADOS", 0)

                # 2) Robot ML
                sugerido, num, estado, url, min_mercado, max_mercado = analizar_vehiculo(
                    marca_sel,
                    submarca_sel,
                    anio_sel,
                    ver_navegador
                )

                if sugerido == 0 and num == 0:
                    st.error(f"No se pudieron obtener precios del mercado. Estado: {estado}")
                    if url:
                        st.write("Link usado para la búsqueda:", url)
                else:
                    compra_sugerida = int(sugerido * 0.88) if sugerido > 0 else 0
                    utilidad_vs_compra_cat = sugerido - precio_compra_cat if (sugerido and precio_compra_cat) else 0

                    st.subheader("Configuración seleccionada")
                    st.write(f"**ID Autoprecios**: {id_auto}")
                    st.write(f"**Marca**: {marca_sel}")
                    st.write(f"**Submarca / Modelo**: {submarca_sel}")
                    st.write(f"**Año / Modelo**: {anio_sel}")
                    st.write(f"**Versión**: {version_sel}")

                    st.write("---")
                    st.subheader("Valores de catálogo AUTOPRECIOS")
                    st.write(f"**Precio lista nuevo**: {precio_lista_nuevo:,.0f} MXN")
                    st.write(f"**Precio catálogo venta**: {precio_venta_cat:,.0f} MXN")
                    st.write(f"**Precio catálogo compra**: {precio_compra_cat:,.0f} MXN")
                    st.write(f"**Precio intermedio**: {precio_intermedio:,.0f} MXN")
                    st.write(f"**Precio agencia certificados**: {precio_ag_cert:,.0f} MXN")

                    st.write("---")
                    st.subheader("Resultados MercadoLibre (Robot Daytona)")
                    st.write(f"**Autos comparables encontrados**: {num}")
                    st.write(f"**Rango de mercado**: {min_mercado:,.0f} - {max_mercado:,.0f} MXN")
                    if url:
                        st.write("Link usado para la búsqueda:", url)

                    st.write("---")
                    st.subheader("Precios sugeridos Daytona")

                    col_a, col_b = st.columns(2)
                    col_a.metric(
                        "Precio sugerido Daytona (venta)",
                        f"{sugerido:,.0f} MXN"
                    )
                    col_b.metric(
                        "Compra sugerida (≈12% margen)",
                        f"{compra_sugerida:,.0f} MXN"
                    )

                    st.write("---")
                    st.subheader("Análisis rápido")
                    st.write(
                        f"**Utilidad vs PRECIO COMPRA de Autoprecios** "
                        f"si vendes al sugerido Daytona: {utilidad_vs_compra_cat:,.0f} MXN"
                    )
