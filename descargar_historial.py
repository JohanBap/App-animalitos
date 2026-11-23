import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date, timedelta
import time
import re

# Configuración de las 4 loterías (totalmente independientes)
LOTERIAS = {
    "Lotto Activo": "https://loteriadehoy.com/animalito/lottoactivo/resultados/",
    "La Granjita": "https://loteriadehoy.com/animalito/lagranjita/resultados/",
    "Guácharo Activo": "https://loteriadehoy.com/animalito/guacharoactivo/resultados/",
    "Guacharito": "https://loteriadehoy.com/animalito/elguacharitomillonario/resultados/"
}

DIAS_A_DESCARGAR = 365
ARCHIVO_CSV = "resultados.csv"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

registros = []
hoy = date.today()

print(f"🚀 Iniciando descarga automática de los últimos {DIAS_A_DESCARGAR} días...")

for nombre_loteria, url_base in LOTERIAS.items():
    print(f"\n📥 Descargando {nombre_loteria}...")
    contador_lot = 0
    
    for i in range(DIAS_A_DESCARGAR, -1, -1):
        fecha_obj = hoy - timedelta(days=i)
        fecha_str = fecha_obj.strftime("%Y-%m-%d")
        
        # La URL de hoy no lleva fecha; los días anteriores llevan la fecha al final
        url = url_base if i == 0 else f"{url_base}{fecha_str}/"
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                continue
                
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Buscar bloques de resultados (número + animal y hora)
            tarjetas = soup.find_all(["div", "li"], class_=re.compile("resultado|sorteo|animal|col-", re.I))
            
            vistos_dia = set()
            for tarjeta in tarjetas:
                texto = " ".join(tarjeta.get_text(" ", strip=True).split())
                # Buscar patrón: Número (0, 00, 1-99) + Nombre + Hora (08:00 AM)
                match_hora = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)", texto, re.I)
                match_anim = re.match(r"^(00|\d{1,2})\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?=\s+(?:Lotto|La Granjita|Guacharo|El Guacharito|\d{1,2}:))", texto, re.I)
                
                if match_hora and match_anim:
                    hora = match_hora.group(1).upper()
                    numero = match_anim.group(1)
                    nombre_anim = match_anim.group(2).strip().title()
                    animal_completo = f"{numero} {nombre_anim}"
                    
                    clave = (fecha_str, hora)
                    if clave not in vistos_dia:
                        vistos_dia.add(clave)
                        registros.append({
                            "loteria": nombre_loteria,
                            "fecha": fecha_str,
                            "hora": hora,
                            "animal": animal_completo
                        })
                        contador_lot += 1
                        
            time.sleep(0.25)  # Pausa corta para no saturar tu conexión
        except Exception as e:
            pass
            
    print(f"✅ {nombre_loteria}: {contador_lot} sorteos guardados.")

if registros:
    df = pd.DataFrame(registros)
    df.drop_duplicates(subset=["loteria", "fecha", "hora"], keep="last", inplace=True)
    df.to_csv(ARCHIVO_CSV, index=False, encoding="utf-8")
    print(f"\n🎉 ¡LISTO! Se guardaron {len(df)} sorteos totales en '{ARCHIVO_CSV}'.")
else:
    print("\n⚠️ No se pudieron extraer registros. Revisa tu conexión a internet.")
