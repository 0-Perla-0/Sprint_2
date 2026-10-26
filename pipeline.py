"""Sprint 2 - Las Pintas (PIN) 2023 y 2024. Pipeline reproducible.
Uso: python pipeline.py RUTA_BD_2023.xlsx RUTA_BD_2024.xlsx
Genera en ./out: horario.csv, diario.csv, mensual.csv, cobertura.csv"""
import sys, numpy as np, pandas as pd

ESTACION = "PIN"
CATS = ["Buena", "Aceptable", "Mala", "Muy mala", "Extremadamente mala"]
# Puntos de corte NOM-172-SEMARNAT-2023 (limites superiores de cada categoria)
CORTES = {
    "PM10":  [45, 50, 132, 213],          # ug/m3, NowCast 12 h (24 h para el resumen diario)
    "PM2.5": [15, 25, 79, 130],           # ug/m3
    "O3":    [0.058, 0.090, 0.135, 0.175] # ppm, promedio de 1 h
}
MIN_HORAS_DIA = 18                        # 75 % de 24 h

def cargar(rutas):
    fr = []
    for r in rutas:
        d = pd.read_excel(r, sheet_name="Data")
        d.columns = [c.strip().upper() for c in d.columns]
        d = d[d["STATION"].astype(str).str.strip() == ESTACION]
        fr.append(d)
    d = pd.concat(fr).sort_values("DATE").reset_index(drop=True)
    for c in d.columns:
        if c not in ("STATION", "DATE"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d

def nowcast(valores, es_pm10):
    """valores: ultimas 12 horas en orden cronologico (None/NaN = faltante)."""
    v = [None if pd.isna(x) else x for x in valores]
    if sum(x is not None for x in v[-3:]) < 2:
        return np.nan
    datos = [(x, i) for i, x in enumerate(v[::-1]) if x is not None]
    mx = max(x for x, _ in datos); mn = min(x for x, _ in datos)
    w = max(round(1 - (mx - mn) / mx, 2), 0.5) if mx > 0 else 1.0
    num = sum(x * w ** i for x, i in datos); den = sum(w ** i for _, i in datos)
    prom = round(num / den, 0)
    return int(round(prom * (0.714 if es_pm10 else 0.694), 0))

def cat(x, pol):
    if pd.isna(x): return np.nan
    for k, lim in enumerate(CORTES[pol]):
        if x <= lim: return k
    return 4

def peor(*ks):
    ks = [k for k in ks if not pd.isna(k)]
    return max(ks) if ks else np.nan

def horario(d):
    h = d[["DATE", "O3", "PM10", "PM2.5", "ET", "RH", "WS", "WD", "PP", "IT"]].copy()
    h["NC_PM10"] = [nowcast(h["PM10"].iloc[max(0, i - 11):i + 1], True) if i >= 0 else np.nan for i in range(len(h))]
    h["NC_PM2.5"] = [nowcast(h["PM2.5"].iloc[max(0, i - 11):i + 1], False) for i in range(len(h))]
    h["k_PM10"] = h["NC_PM10"].map(lambda x: cat(x, "PM10"))
    h["k_PM2.5"] = h["NC_PM2.5"].map(lambda x: cat(x, "PM2.5"))
    h["k_O3"] = h["O3"].map(lambda x: cat(x, "O3"))
    h["k_global"] = [peor(a, b, c) for a, b, c in zip(h.k_PM10, h["k_PM2.5"], h.k_O3)]
    h["fecha"] = h["DATE"].dt.normalize(); h["hora"] = h["DATE"].dt.hour
    h["anio"] = h["DATE"].dt.year; h["mes"] = h["DATE"].dt.month
    return h

def diario(h):
    filas = []
    for f, g in h.groupby("fecha"):
        r = {"fecha": f, "anio": f.year, "mes": f.month}
        for p, c in (("PM10", "PM10"), ("PM2.5", "PM2.5"), ("O3", "O3")):
            n = g[c].notna().sum(); r["n_" + p] = n
            ok = n >= MIN_HORAS_DIA
            # Redondeo NOM-172 (5.2.4): PM a enteros, O3 a 3 decimales
            r["ind_" + p] = (round(g[c].mean(), 0) if p != "O3" else round(g[c].max(), 3)) if ok else np.nan
            r["k_" + p] = cat(r["ind_" + p], p)
        r["k_global"] = peor(r["k_PM10"], r["k_PM2.5"], r["k_O3"])
        r["dominante"] = "/".join(p for p in ("PM10", "PM2.5", "O3")
                                  if not pd.isna(r["k_" + p]) and r["k_" + p] == r["k_global"]) if not pd.isna(r["k_global"]) else "ND"
        r["max_NC_PM10"] = g["NC_PM10"].max(); r["max_NC_PM2.5"] = g["NC_PM2.5"].max()
        r["horas_extrema"] = int((g["k_global"] == 4).sum()); r["horas_muy_mala_o_peor"] = int((g["k_global"] >= 3).sum())
        filas.append(r)
    return pd.DataFrame(filas)

if __name__ == "__main__":
    d = cargar(sys.argv[1:3]); h = horario(d); dd = diario(h)
    import os; os.makedirs("out", exist_ok=True)
    h.to_csv("out/horario.csv", index=False); dd.to_csv("out/diario.csv", index=False)
