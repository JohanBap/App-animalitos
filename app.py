import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from itertools import combinations
from collections import Counter
from datetime import date, timedelta
import re

st.set_page_config(page_title="Pronosticador Animalitos", page_icon="🎯", layout="centered")
st.title("🎯 Pronosticador por Parejas (Modo Chat)")

ARCHIVO_CSV = "resultados.csv"

LOTERIAS_URL = {
    "Lotto Activo": "https://loteriadehoy.com",
    "La Granjita": "https://loteriadehoy.com",
    "Guácharo Activo": "https://loteriadehoy.com",
    "Guacharito": "https://loteriadehoy.com"
}

def cargar_datos():
    try:
        return pd.read_csv(ARCHIVO_CSV)
    except FileNotFoundError:
        return pd.DataFrame(columns=["loteria", "fecha", "hora", "animal"])

def actualizar_desde_web(df_actual):
    headers = {"User-Agent": "Mozilla/5.0"}
    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    nuevos = []

    for nombre_lot, url in LOTERIAS_URL.items():
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            tabla = soup.find("table")
            if not tabla:
                continue
            for fila in tabla.find_all("tr")[1:]:
                celdas = [c.get_text(" ", strip=True) for c in fila.find_all(["td", "th"])]
                if len(celdas) < 8:
                    continue
                hora = celdas.upper()
                if not re.match(r"^\d{1,2}:\d{2}\s*[AP]M$", hora):
                    continue
                for dia_idx in range(7):
                    fecha_celda = str(lunes_actual + timedelta(days=dia_idx))
                    texto_anim = celdas[dia_idx + 1]
                    if texto_anim and texto_anim != "-" and not texto_anim.lower().startswith("pend"):
                        anim_limpio = " ".join(texto_anim.split()).title()
                        nuevos.append({
                            "loteria": nombre_lot,
                            "fecha": fecha_celda,
                            "hora": hora,
                            "animal": anim_limpio
                        })
        except Exception:
            pass

    if nuevos:
        df_nuevo = pd.DataFrame(nuevos)
        df_combinado = pd.concat([df_actual, df_nuevo], ignore_index=True)
        df_combinado.drop_duplicates(subset=["loteria", "fecha", "hora"], keep="last", inplace=True)
        df_combinado.to_csv(ARCHIVO_CSV, index=False, encoding="utf-8")
        return df_combinado, len(nuevos)
    return df_actual, 0

df = cargar_datos()

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración")

if st.sidebar.button("🔄 Actualizar Resultados de Hoy", use_container_width=True):
    with st.spinner("Descargando resultados en vivo..."):
        df, cant = actualizar_desde_web(df)
        if cant > 0:
            st.sidebar.success("¡Pizarra actualizada!")
            st.rerun()
        else:
            st.sidebar.warning("No hay sorteos nuevos aún.")

st.sidebar.markdown("---")
loteria = st.sidebar.selectbox(
    "Lotería Activa (100% Independiente):",
    ["Lotto Activo", "La Granjita", "Guácharo Activo", "Guacharito"]
)

fecha_hoy = str(st.sidebar.date_input("Fecha de análisis:", value=date.today()))

datos_lot = df[df["loteria"] == loteria].copy().reset_index(drop=True)

# --- MOTOR DE PAREJAS ---
por_dia = datos_lot.groupby("fecha")["animal"].apply(list)
parejas_counter = Counter()

for lista_dia in por_dia:
    unicos = sorted(set(lista_dia))
    for par in combinations(unicos, 2):
        parejas_counter[par] += 1

def obtener_mejores_socios(animales_base, excluir_salidos=True, top_n=3):
    puntajes = Counter()
    todos = datos_lot["animal"].unique()
    for candidato in todos:
        if excluir_salidos and candidato in animales_base:
            continue
        score = 0
        for base in animales_base:
            par = tuple(sorted([candidato, base]))
            score += parejas_counter[par]
        if score > 0:
            puntajes[candidato] = score
    return puntajes.most_common(top_n)

# --- INTERFAZ TIPO CHAT ---
salidos_hoy = datos_lot[datos_lot["fecha"] == fecha_hoy]["animal"].tolist()

with st.chat_message("assistant"):
    st.markdown(f"**Analizando {loteria} ({fecha_hoy})** — Base histórica: `{len(datos_lot)}` sorteos.")
    if not salidos_hoy:
        st.write("Aún no hay resultados registrados hoy. Toca **Actualizar Resultados de Hoy** en el menú izquierdo o ingrésalo abajo.")
    else:
        st.write(f"**Pizarra de hoy ({len(salidos_hoy)} sorteos):** " + " ➡️ ".join(salidos_hoy))

        primer_animal = [salidos_hoy]
        socios_tripleta = obtener_mejores_socios(primer_animal, excluir_salidos=True, top_n=3)
        if len(socios_tripleta) == 3:
            t1, t2, t3 = socios_tripleta, socios_tripleta, socios_tripleta
            st.success(f"🎲 **1 Tripleta del Día (Anclada en {salidos_hoy}):**\n\n### **{t1} — {t2} — {t3}**")

        if len(salidos_hoy) >= 4:
            top_2 = obtener_mejores_socios(salidos_hoy, excluir_salidos=True, top_n=2)
            if len(top_2) >= 2:
                st.info(
                    f"🔥 **2 Animalitos para el resto del día (Cruce de los {len(salidos_hoy)} sorteos):**\n\n"
                    f"1. **{top_2}** *(Índice de coincidencia: {top_2} pts)*\n"
                    f"2. **{top_2}** *(Índice de coincidencia: {top_2} pts)*"
                )
        else:
            faltan = 4 - len(salidos_hoy)
            st.warning(f"⏳ Faltan **{faltan} sorteo(s)** de la mañana para llegar a las 11:00 AM y liberar los **2 animalitos** de la tarde.")

# --- INGRESO MANUAL OPCIONAL ---
st.markdown("---")
col1, col2, col3 = st.columns([1.2, 2, 1.3])
with col1:
    hora_sel = st.selectbox("Hora:", [
        "08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM",
        "12:00 PM", "01:00 PM", "02:00 PM", "03:00 PM",
        "04:00 PM", "05:00 PM", "06:00 PM", "07:00 PM"
    ], index=min(len(salidos_hoy), 11))
with col2:
    anim_txt = st.text_input("Animalito que salió:", placeholder="Ej: 13 Mono")
with col3:
    st.write("")
    st.write("")
    if st.button("Enviar Resultado 📤", use_container_width=True) and anim_txt.strip():
        nuevo = pd.DataFrame([{
            "loteria": loteria,
            "fecha": fecha_hoy,
            "hora": hora_sel,
            "animal": anim_txt.strip()
        }])
        df = pd.concat([df, nuevo], ignore_index=True)
        df.drop_duplicates(subset=["loteria", "fecha", "hora"], keep="last", inplace=True)
        df.to_csv(ARCHIVO_CSV, index=False, encoding="utf-8")
        st.rerun()
