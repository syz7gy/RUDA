#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLD biológico de la estrategia ruderal (proyecto RUDA) - versión 0.2
=====================================================================

Fuente única de verdad: los dos archivos CSV de la carpeta ``datos``.

  datos/nodos.csv     variables del diagrama (una fila por variable)
  datos/aristas.csv   relaciones causales con signo, respaldo, alcance,
                      estado y verificación (la "matriz de respaldo por flecha")

Qué hace este script
  1. Lee y valida los CSV (ids, signos, estados, mecanismos).
  2. Construye el grafo con networkx y detecta los lazos de retroalimentación,
     clasificándolos como refuerzo (R) o balance (B) por el producto de signos.
  3. Dibuja el diagrama del núcleo, el diagrama completo y una página por mecanismo.
  4. Exporta tablas (lazos, matriz por mecanismo) y un resumen de verificación.

Uso
  pip install networkx matplotlib
  python cld_ruderal.py                    # usa ./datos y escribe en ./salida
  python cld_ruderal.py --datos otra_carpeta --salida resultados

Para cambiar el diagrama NO se edita este código: se editan los CSV
(agregar una fila a aristas.csv agrega una flecha; las coordenadas x, y de
nodos.csv mueven las cajas; la columna "via" de aristas.csv fuerza una ruta).

Convenciones
  signo      +  (misma dirección)   -  (dirección opuesta)   +/-  (depende de condiciones)
  retardo    si / no   (marca la flecha con doble raya)
  dibujar    si / no   (no dibuja la flecha, pero la conserva en la matriz y en el análisis)
  via        puntos intermedios "x;y|x;y" para rutas manuales
  desv       desplazamiento lateral para separar flechas recíprocas
"""
import argparse
import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Patch  # noqa: E402
import networkx as nx  # noqa: E402

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------
ESTADOS = [
    "Documentado",
    "Documentado bajo condiciones",
    "Hipótesis de modelado",
    "Pendiente de asesoría",
]
VERIFICACIONES = ["Verificada", "Parcial", "Por verificar", "No aplica"]
SIGNOS = {"+": 1, "-": -1, "+/-": 0}

MECANISMOS = {
    "M1": "Aprovechar una ventana favorable",
    "M2": "Completar el ciclo reproductivo a tiempo",
    "M3": "Producir y dispersar propágulos",
    "M4": "Mantener posibilidades de regeneración",
    "M5": "Colonizar espacios y afrontar la competencia",
}
COLOR_MECANISMO = {
    "M1": "#185FA5",
    "M2": "#BA7517",
    "M3": "#0F6E56",
    "M4": "#534AB7",
    "M5": "#A32D2D",
}
GRUPOS = {  # relleno, borde, etiqueta de leyenda
    "entorno": ("#F1EFE8", "#5F5E5A", "Entorno y perturbación"),
    "ruderal": ("#E1F5EE", "#0F6E56", "Población ruderal"),
    "competidoras": ("#FAECE7", "#993C1D", "Competidoras"),
    "rasgo": ("#EEEDFE", "#534AB7", "Rasgo o parámetro"),
}
ORDEN_DEBIL = {e: i for i, e in enumerate(ESTADOS)}

W_NODO, H_NODO = 2.8, 1.0  # tamaño de las cajas en unidades de datos
ESCALA = 0.85  # pulgadas por unidad de datos
COLOR_ARISTA = "#2C2C2A"
COLOR_APAGADO = "#B4B2A9"
COLOR_ALERTA = "#A32D2D"


# --------------------------------------------------------------------------
# Lectura y validación
# --------------------------------------------------------------------------
def leer_csv(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def cargar(datos):
    nodos = {}
    for r in leer_csv(datos / "nodos.csv"):
        if r["id"] in nodos:
            sys.exit(f"[error] id de nodo duplicado: {r['id']}")
        r["x"], r["y"] = float(r["x"]), float(r["y"])
        r["etiqueta"] = r["etiqueta"].replace("\\n", "\n")
        nodos[r["id"]] = r
    aristas = leer_csv(datos / "aristas.csv")
    return nodos, aristas


def validar(nodos, aristas):
    errores, avisos = [], []
    ids = set()
    pares = set()
    for e in aristas:
        if e["id"] in ids:
            errores.append(f"id de arista duplicado: {e['id']}")
        ids.add(e["id"])
        for campo in ("origen", "destino"):
            if e[campo] not in nodos:
                errores.append(f"{e['id']}: {campo} '{e[campo]}' no existe en nodos.csv")
        if e["signo"] not in SIGNOS:
            errores.append(f"{e['id']}: signo '{e['signo']}' inválido (usa +, - o +/-)")
        if e["estado"] not in ESTADOS:
            errores.append(f"{e['id']}: estado '{e['estado']}' inválido")
        if e["verificacion"] not in VERIFICACIONES:
            errores.append(f"{e['id']}: verificación '{e['verificacion']}' inválida")
        for m in filter(None, e["mecanismos"].split(";")):
            if m not in MECANISMOS:
                errores.append(f"{e['id']}: mecanismo '{m}' desconocido")
        par = (e["origen"], e["destino"])
        if par in pares:
            errores.append(f"{e['id']}: relación repetida {par[0]} -> {par[1]}")
        pares.add(par)
        if e["estado"].startswith("Documentado") and e["verificacion"] == "Por verificar":
            avisos.append(f"{e['id']}: marcada como '{e['estado']}' pero la fuente está por verificar")
    usados = {e["origen"] for e in aristas} | {e["destino"] for e in aristas}
    for n in nodos:
        if n not in usados:
            avisos.append(f"nodo sin relaciones: {n}")
    return errores, avisos


# --------------------------------------------------------------------------
# Grafo y análisis de lazos
# --------------------------------------------------------------------------
def construir_grafo(aristas, solo_nucleo=False):
    g = nx.DiGraph()
    for e in aristas:
        if solo_nucleo and e["capa"] != "nucleo":
            continue
        g.add_edge(e["origen"], e["destino"], **e)
    return g


def analizar_lazos(g, nodos, max_long=10):
    lazos = []
    for ciclo in nx.simple_cycles(g, length_bound=max_long):
        i = ciclo.index(min(ciclo))
        ciclo = ciclo[i:] + ciclo[:i]
        pares = list(zip(ciclo, ciclo[1:] + ciclo[:1]))
        arcos = [g[u][v] for u, v in pares]
        signos = [SIGNOS[a["signo"]] for a in arcos]
        if 0 in signos:
            tipo = "Condicional"
        else:
            prod = 1
            for s in signos:
                prod *= s
            tipo = "Refuerzo" if prod > 0 else "Balance"
        peor = max(arcos, key=lambda a: ORDEN_DEBIL[a["estado"]])["estado"]
        mecs = sorted({m for a in arcos for m in a["mecanismos"].split(";") if m})
        lazos.append(
            {
                "tipo": tipo,
                "longitud": len(ciclo),
                "variables": " -> ".join(ciclo + [ciclo[0]]),
                "etiquetas": " -> ".join([nodos[n]["etiqueta"].replace("\n", " ") for n in ciclo]),
                "aristas": ";".join(a["id"] for a in arcos),
                "mecanismos": ";".join(mecs),
                "con_retardo": "si" if any(a["retardo"] == "si" for a in arcos) else "no",
                "estado_mas_debil": peor,
                "depende_de_hipotesis": "si" if ORDEN_DEBIL[peor] >= 2 else "no",
                "en_nucleo": "si" if all(a["capa"] == "nucleo" for a in arcos) else "no",
            }
        )
    lazos.sort(key=lambda d: (d["longitud"], d["variables"]))
    cont = {"Refuerzo": 0, "Balance": 0, "Condicional": 0}
    pref = {"Refuerzo": "R", "Balance": "B", "Condicional": "C"}
    for d in lazos:
        cont[d["tipo"]] += 1
        d["id"] = f"{pref[d['tipo']]}{cont[d['tipo']]}"
    return lazos


# --------------------------------------------------------------------------
# Geometría de las flechas
# --------------------------------------------------------------------------
def borde(n, hacia):
    cx, cy = n["x"], n["y"]
    dx, dy = hacia[0] - cx, hacia[1] - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    sx = (W_NODO / 2) / abs(dx) if dx else float("inf")
    sy = (H_NODO / 2) / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return (cx + dx * s, cy + dy * s)


def punto_ortogonal(n, p):
    """Punto de la caja desde donde sale/entra una ruta manual hacia p (en línea recta, sin diagonales)."""
    if abs(p[1] - n["y"]) > H_NODO / 2 and abs(p[0] - n["x"]) < W_NODO / 2 - 0.2:
        return (p[0], n["y"] + math.copysign(H_NODO / 2, p[1] - n["y"]))
    if abs(p[0] - n["x"]) > W_NODO / 2 and abs(p[1] - n["y"]) < H_NODO / 2 - 0.1:
        return (n["x"] + math.copysign(W_NODO / 2, p[0] - n["x"]), p[1])
    return borde(n, p)


def dentro(p, n, margen=0.12):
    return abs(p[0] - n["x"]) < W_NODO / 2 + margen and abs(p[1] - n["y"]) < H_NODO / 2 + margen


def bezier(p0, c, p2, n=40):
    return [
        (
            (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t**2 * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t**2 * p2[1],
        )
        for t in [i / n for i in range(n + 1)]
    ]


def parsear_via(texto):
    if not texto:
        return []
    return [tuple(float(v) for v in par.split(";")) for par in texto.split("|")]


def trayecto(e, nodos):
    o, d = nodos[e["origen"]], nodos[e["destino"]]
    via = parsear_via(e.get("via", ""))
    if via:
        return [punto_ortogonal(o, via[0])] + via + [punto_ortogonal(d, via[-1])]
    c0, c1 = (o["x"], o["y"]), (d["x"], d["y"])
    desv = float(e.get("desv") or 0)
    L = math.hypot(c1[0] - c0[0], c1[1] - c0[1]) or 1.0
    nx_, ny_ = -(c1[1] - c0[1]) / L, (c1[0] - c0[0]) / L
    if desv:
        c0 = (c0[0] + nx_ * desv, c0[1] + ny_ * desv)
        c1 = (c1[0] + nx_ * desv, c1[1] + ny_ * desv)
    reciproca = e.get("_reciproca", False)
    candidatas = [0, 0.18, -0.18, 0.32, -0.32, 0.5, -0.5, 0.7, -0.7]
    if reciproca and not desv:
        candidatas = [0.25, 0.4, -0.25, 0.6]
    otros = [n for k, n in nodos.items() if k not in (e["origen"], e["destino"])]
    mejor, mejor_choques = None, None
    for rad in candidatas:
        mid = ((c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2)
        ctrl = (mid[0] + nx_ * rad * L, mid[1] + ny_ * rad * L)
        p0, p2 = borde(o, ctrl), borde(d, ctrl)
        pts = bezier(p0, ctrl, p2) if rad else [p0, p2]
        choques = sum(1 for p in pts for n in otros if dentro(p, n))
        if mejor is None or choques < mejor_choques:
            mejor, mejor_choques = pts, choques
        if choques == 0:
            break
    return mejor


def longitud(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def punto_en(pts, frac):
    objetivo = longitud(pts) * frac
    acum = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if acum + seg >= objetivo and seg > 0:
            t = (objetivo - acum) / seg
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            nx_, ny_ = -(b[1] - a[1]) / seg, (b[0] - a[0]) / seg
            return (x, y), (nx_, ny_), ((b[0] - a[0]) / seg, (b[1] - a[1]) / seg)
        acum += seg
    return pts[-1], (0, 1), (1, 0)


def recortar(pts, cola):
    """Devuelve (puntos de la línea, punto donde empieza la cabeza)."""
    restante = cola
    nuevos = list(pts)
    while len(nuevos) > 1 and restante > 0:
        a, b = nuevos[-2], nuevos[-1]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg > restante:
            t = (seg - restante) / seg
            nuevos[-1] = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            restante = 0
        else:
            nuevos.pop()
            restante -= seg
    return nuevos


# --------------------------------------------------------------------------
# Dibujo
# --------------------------------------------------------------------------
def estilo_estado(estado):
    if estado == "Hipótesis de modelado":
        return (0, (5, 3)), 1.7
    if estado == "Pendiente de asesoría":
        return (0, (1, 2.5)), 1.9
    return "-", 1.9


def dibujar_nodo(ax, n, apagado=False):
    rel, bor, _ = GRUPOS[n["grupo"]]
    estado = n["tipo"] == "Estado"
    exogena = n["tipo"] == "Exógena"
    caja = FancyBboxPatch(
        (n["x"] - W_NODO / 2, n["y"] - H_NODO / 2),
        W_NODO,
        H_NODO,
        boxstyle="round,pad=0,rounding_size=0.14",
        fc=rel,
        ec=bor,
        lw=2.6 if estado else 1.2,
        ls=(0, (4, 2)) if exogena else "-",
        alpha=0.3 if apagado else 1.0,
        zorder=3,
    )
    ax.add_patch(caja)
    ax.text(
        n["x"],
        n["y"],
        n["etiqueta"],
        ha="center",
        va="center",
        fontsize=9,
        color="#2C2C2A",
        alpha=0.35 if apagado else 1.0,
        zorder=4,
        linespacing=1.25,
    )


def dibujar_arista(ax, e, pts, color, apagado=False, grueso=False):
    ls, lw = estilo_estado(e["estado"])
    if grueso:
        lw += 0.9
    alpha = 0.4 if apagado else 1.0
    linea = recortar(pts, 0.3)
    if len(linea) > 1:
        ax.plot(
            [p[0] for p in linea],
            [p[1] for p in linea],
            color=color,
            lw=lw,
            ls=ls,
            alpha=alpha,
            solid_capstyle="butt",
            zorder=2,
        )
    ax.annotate(
        "",
        xy=pts[-1],
        xytext=linea[-1],
        arrowprops=dict(
            arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=15, alpha=alpha
        ),
        zorder=2,
    )
    # signo
    frac = 0.5 if longitud(pts) < 2.2 else 0.66
    (x, y), (nx_, ny_), _ = punto_en(pts, frac)
    desplaza = 0.0 if longitud(pts) < 1.3 else 0.3
    signo = {"+": "+", "-": "−", "+/-": "±"}[e["signo"]]
    col_signo = COLOR_ALERTA if e["verificacion"] == "Por verificar" else "#2C2C2A"
    if apagado:
        col_signo = COLOR_APAGADO
    ax.text(
        x + nx_ * desplaza,
        y + ny_ * desplaza,
        signo,
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=col_signo,
        zorder=5,
        bbox=dict(boxstyle="circle,pad=0.12", fc="white", ec="none", alpha=0.92),
    )
    # retardo
    if e["retardo"] == "si":
        (x, y), (nx_, ny_), (tx, ty) = punto_en(pts, 0.38)
        for d in (-0.07, 0.07):
            ax.plot(
                [x + tx * d - nx_ * 0.2, x + tx * d + nx_ * 0.2],
                [y + ty * d - ny_ * 0.2, y + ty * d + ny_ * 0.2],
                color=color,
                lw=2.0,
                zorder=5,
                alpha=alpha,
            )
        ax.text(x - nx_ * 0.5, y - ny_ * 0.5, "retardo", ha="center", va="center", fontsize=8.5, color="#5F5E5A", zorder=5)


def leyenda(fig, extra):
    altura = fig.get_figheight()
    f1, f2 = 0.95 / altura, 0.30 / altura
    h = [Patch(fc=v[0], ec=v[1], label=v[2]) for v in GRUPOS.values()]
    h.append(Patch(fc="white", ec="#2C2C2A", lw=2.6, label="Borde grueso: stock (estado)"))
    h.append(Patch(fc="white", ec="#2C2C2A", ls=(0, (4, 2)), label="Borde discontinuo: exógena"))
    fig.legend(handles=h, loc="lower center", ncol=6, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, f1))
    l = [
        Line2D([0], [0], color=COLOR_ARISTA, lw=1.9, label="Documentado (puede depender de condiciones)"),
        Line2D([0], [0], color=COLOR_ARISTA, lw=1.7, ls=(0, (5, 3)), label="Hipótesis de modelado"),
        Line2D([0], [0], color=COLOR_ARISTA, lw=1.9, ls=(0, (1, 2.5)), label="Pendiente de asesoría"),
        Line2D([0], [0], marker="$-$", color="none", markerfacecolor=COLOR_ALERTA, markeredgecolor=COLOR_ALERTA, markersize=9, label="Signo en rojo: fuente por verificar"),
    ]
    fig.legend(handles=l, loc="lower center", ncol=4, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, f2))


def figura(nodos, aristas, ids_nodos, titulo, pie, resaltar=None, lineas_lazos=None):
    sel = {k: nodos[k] for k in ids_nodos}
    vistas = [e for e in aristas if e["dibujar"] == "si" and e["origen"] in sel and e["destino"] in sel]
    pares = {(e["origen"], e["destino"]) for e in vistas}
    rutas = {}
    for e in vistas:
        inversa_manual = any(
            o["origen"] == e["destino"] and o["destino"] == e["origen"] and (o.get("via") or o.get("desv"))
            for o in vistas
        )
        e["_reciproca"] = (e["destino"], e["origen"]) in pares and not inversa_manual
        rutas[e["id"]] = trayecto(e, nodos)
    xs = [n["x"] - W_NODO / 2 for n in sel.values()] + [n["x"] + W_NODO / 2 for n in sel.values()]
    ys = [n["y"] - H_NODO / 2 for n in sel.values()] + [n["y"] + H_NODO / 2 for n in sel.values()]
    for r in rutas.values():
        xs += [p[0] for p in r]
        ys += [p[1] for p in r]
    xmin, xmax, ymin, ymax = min(xs) - 0.7, max(xs) + 0.7, min(ys) - 0.5, max(ys) + 0.9
    ancho, alto = (xmax - xmin) * ESCALA, (ymax - ymin) * ESCALA
    extra = 2.3 + (0.21 * (len(lineas_lazos) + 1) if lineas_lazos else 0.0)
    fig = plt.figure(figsize=(ancho, alto + extra))
    ax = fig.add_axes([0.01, extra / (alto + extra), 0.98, alto / (alto + extra) - 0.04])
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")
    for e in vistas:
        if resaltar:
            activa = resaltar in e["mecanismos"].split(";")
            color = COLOR_MECANISMO[resaltar] if activa else COLOR_APAGADO
            dibujar_arista(ax, e, rutas[e["id"]], color, apagado=not activa, grueso=activa)
        else:
            dibujar_arista(ax, e, rutas[e["id"]], COLOR_ARISTA)
    if resaltar:
        activos = {e["origen"] for e in vistas if resaltar in e["mecanismos"].split(";")} | {
            e["destino"] for e in vistas if resaltar in e["mecanismos"].split(";")
        }
        for k, n in sel.items():
            dibujar_nodo(ax, n, apagado=k not in activos)
    else:
        for n in sel.values():
            dibujar_nodo(ax, n)
    fig.text(0.5, 1 - 0.35 / (alto + extra), titulo, ha="center", va="top", fontsize=17, fontweight="bold", color="#2C2C2A")
    leyenda(fig, extra)
    if lineas_lazos:
        fig.text(
            0.012,
            (2.05 + 0.21 * len(lineas_lazos)) / (alto + extra),
            "Lazos de retroalimentación (R = refuerzo, B = balance)\n" + "\n".join(lineas_lazos),
            ha="left",
            va="top",
            fontsize=9,
            color="#2C2C2A",
            linespacing=1.35,
        )
    fig.text(0.012, 0.004, pie, ha="left", va="bottom", fontsize=8.5, color="#5F5E5A", wrap=True)
    return fig


# --------------------------------------------------------------------------
# Salidas
# --------------------------------------------------------------------------
def escribir_csv(ruta, filas, columnas):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def lineas_de_lazos(lazos, nodos, solo_nucleo):
    corto = {k: n["etiqueta"].replace("\n", " ") for k, n in nodos.items()}
    out = []
    for l in lazos:
        if solo_nucleo and l["en_nucleo"] != "si":
            continue
        cadena = " → ".join(corto[v] for v in l["variables"].split(" -> "))
        notas = []
        if l["con_retardo"] == "si":
            notas.append("con retardo")
        if l["depende_de_hipotesis"] == "si":
            notas.append("depende de hipótesis")
        out.append(f"{l['id']:>3}  {cadena}" + (f"   ({'; '.join(notas)})" if notas else ""))
    return out


def matriz_por_mecanismo(aristas, nodos):
    filas = []
    for m in MECANISMOS:
        for e in aristas:
            if m in e["mecanismos"].split(";"):
                filas.append(
                    {
                        "mecanismo": f"{m} {MECANISMOS[m]}",
                        "id": e["id"],
                        "relacion": f"{nodos[e['origen']]['etiqueta'].replace(chr(10), ' ')} -> {nodos[e['destino']]['etiqueta'].replace(chr(10), ' ')}",
                        "signo": e["signo"],
                        "retardo": e["retardo"],
                        "respaldo": e["respaldo"],
                        "alcance": e["alcance"],
                        "estado": e["estado"],
                        "verificacion": e["verificacion"],
                        "nota": e["nota"],
                    }
                )
    return filas


def resumen(nodos, aristas, lazos, avisos):
    lineas = ["RESUMEN DEL CLD (generado por cld_ruderal.py)", "=" * 46, ""]
    lineas.append(f"Variables: {len(nodos)}  |  Relaciones: {len(aristas)}  "
                  f"(dibujadas: {sum(1 for e in aristas if e['dibujar'] == 'si')})")
    lineas.append("")
    lineas.append("Relaciones por estado:")
    for est in ESTADOS:
        lineas.append(f"  {est}: {sum(1 for e in aristas if e['estado'] == est)}")
    lineas.append("Relaciones por verificación de la fuente:")
    for v in VERIFICACIONES:
        lineas.append(f"  {v}: {sum(1 for e in aristas if e['verificacion'] == v)}")
    lineas.append("")
    lineas.append(f"Lazos detectados: {len(lazos)} "
                  f"(R={sum(1 for l in lazos if l['tipo'] == 'Refuerzo')}, "
                  f"B={sum(1 for l in lazos if l['tipo'] == 'Balance')}, "
                  f"condicionales={sum(1 for l in lazos if l['tipo'] == 'Condicional')})")
    lineas.append("")
    lineas.append("Lazos del núcleo:")
    for l in lazos:
        if l["en_nucleo"] == "si":
            marca = "  [depende de hipótesis]" if l["depende_de_hipotesis"] == "si" else ""
            ret = "  [con retardo]" if l["con_retardo"] == "si" else ""
            lineas.append(f"  {l['id']:>3} {l['tipo']:<9} {l['variables']}{ret}{marca}")
    lineas.append("")
    lineas.append("Avisos de validación:")
    lineas += [f"  - {a}" for a in avisos] or ["  (ninguno)"]
    lineas.append("")
    lineas.append("Ausencias deliberadas (documentadas en el modelo):")
    lineas.append("  - No hay flecha de 'Biomasa destruida' hacia 'Banco de semillas': la muerte de los adultos")
    lineas.append("    no elimina las semillas ya producidas (mecanismo 4). La perturbación del suelo actúa sobre el")
    lineas.append("    banco solo mediante la profundidad de entierro (Eager et al. 2013, especialistas).")
    lineas.append("  - Fuera del alcance de v0.2: germinación activada por fuego, rebrote vegetativo,")
    lineas.append("    dispersión espacial explícita, plasticidad y evolución de rasgos.")
    return "\n".join(lineas)


def main():
    aqui = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="CLD biológico de la estrategia ruderal (RUDA)")
    ap.add_argument("--datos", default=str(aqui / "datos"))
    ap.add_argument("--salida", default=str(aqui / "salida"))
    ap.add_argument("--max-long", type=int, default=10, help="longitud máxima de lazo a buscar")
    ap.add_argument("--dpi", type=int, default=110)
    args = ap.parse_args()
    datos, salida = Path(args.datos), Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    nodos, aristas = cargar(datos)
    errores, avisos = validar(nodos, aristas)
    if errores:
        print("ERRORES DE VALIDACIÓN:")
        for e in errores:
            print("  -", e)
        sys.exit(1)

    g = construir_grafo(aristas)
    lazos = analizar_lazos(g, nodos, args.max_long)
    cols = ["id", "tipo", "longitud", "variables", "etiquetas", "aristas", "mecanismos",
            "con_retardo", "estado_mas_debil", "depende_de_hipotesis", "en_nucleo"]
    escribir_csv(salida / "lazos.csv", lazos, cols)
    escribir_csv(
        salida / "matriz_por_mecanismo.csv",
        matriz_por_mecanismo(aristas, nodos),
        ["mecanismo", "id", "relacion", "signo", "retardo", "respaldo", "alcance", "estado", "verificacion", "nota"],
    )
    (salida / "resumen.txt").write_text(resumen(nodos, aristas, lazos, avisos), encoding="utf-8")

    no_dibujadas = ", ".join(e["id"] for e in aristas if e["dibujar"] == "no")
    pie_comun = (
        "Línea = relación causal; el signo indica si las variables cambian en el mismo sentido (+) o en sentido opuesto (−). "
        "Doble raya = retardo. "
        + (f"Relaciones no dibujadas (se conservan en aristas.csv): {no_dibujadas}. " if no_dibujadas else "")
        + "Versión de trabajo: las relaciones son candidatas hasta contrastarlas con la asesoría."
    )

    ids_nucleo = [k for k, n in nodos.items() if n["capa"] == "nucleo"]
    ar_nucleo = [e for e in aristas if e["capa"] == "nucleo"]
    fig = figura(nodos, ar_nucleo, ids_nucleo, "CLD biológico v0.2 - núcleo (estrategia ruderal)", pie_comun,
                 lineas_lazos=lineas_de_lazos(lazos, nodos, True))
    for ext in ("png", "svg"):
        fig.savefig(salida / f"cld_nucleo.{ext}", dpi=args.dpi, facecolor="white")
    plt.close(fig)

    fig = figura(nodos, aristas, list(nodos), "CLD biológico v0.2 - completo (cinco mecanismos)", pie_comun,
                 lineas_lazos=lineas_de_lazos(lazos, nodos, False))
    for ext in ("png", "svg"):
        fig.savefig(salida / f"cld_completo.{ext}", dpi=args.dpi, facecolor="white")
    plt.close(fig)

    with PdfPages(salida / "cld_por_mecanismo.pdf") as pdf:
        for m, nombre in MECANISMOS.items():
            ids = [e["id"] for e in aristas if m in e["mecanismos"].split(";") and e["dibujar"] == "si"]
            pie = f"{m}: relaciones resaltadas = {', '.join(ids)}. " + pie_comun
            fig = figura(nodos, aristas, list(nodos), f"{m} - {nombre}", pie, resaltar=m)
            pdf.savefig(fig, facecolor="white")
            plt.close(fig)

    print(f"Listo. Archivos en: {salida}")
    print(f"  variables={len(nodos)} relaciones={len(aristas)} lazos={len(lazos)}")
    if avisos:
        print("Avisos:")
        for a in avisos:
            print("  -", a)


if __name__ == "__main__":
    main()
