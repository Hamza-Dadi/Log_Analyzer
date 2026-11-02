from collections import Counter
import os
import io
from pathlib import Path
import requests
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

"""
Module Serving / Visualisation Interactive (Dark Theme + Drapeaux PNG) :
Affiche les graphiques statistiques directement à l'écran via une interface interactive
Matplotlib avec un thème sombre (Dark Mode) et les drapeaux des pays attaquants en PNG.
"""

ROOT_DIR = Path(__file__).resolve().parent.parent
FLAGS_DIR = ROOT_DIR / "Storage" / "flags"
FLAGS_DIR.mkdir(parents=True, exist_ok=True)

# Dictionnaire de correspondance des codes ISO vers les noms complets en français
COUNTRY_NAMES = {
    "RO": "Roumanie",
    "NL": "Pays-Bas",
    "VN": "Vietnam",
    "FI": "Finlande",
    "LT": "Lituanie",
    "US": "États-Unis",
    "FR": "France",
    "CN": "Chine",
    "DE": "Allemagne",
    "RU": "Russie",
    "GB": "Royaume-Uni",
    "IN": "Inde",
    "BR": "Brésil",
    "CA": "Canada",
    "SG": "Singapour",
    "KR": "Corée du Sud",
    "MA": "Maroc",
    "DZ": "Algérie",
    "TN": "Tunisie",
    "ES": "Espagne",
    "IT": "Italie",
    "TR": "Turquie",
    "BG": "Bulgarie",
    "PL": "Pologne",
    "UA": "Ukraine",
    "HK": "Hong Kong",
    "TW": "Taïwan",
    "JP": "Japon",
    "ID": "Indonésie",
    "TH": "Thaïlande"
}

# Palette de couleurs Dark Theme
DARK_BG = "#0d1117"        # Fond principal (Dark GitHub)
CARD_BG = "#161b22"        # Fond des sous-graphiques
BORDER_COLOR = "#30363d"   # Bordures discrètes
GRID_COLOR = "#21262d"     # Lignes de grille
TEXT_MAIN = "#f0f6fc"      # Texte principal blanc éclatant
TEXT_MUTED = "#8b949e"     # Texte secondaire gris clair
ACCENT_BLUE = "#58a6ff"    # Bleu néon
ACCENT_RED = "#f85149"     # Rouge alerte
ACCENT_GREEN = "#3fb950"   # Vert émeraude
ACCENT_AMBER = "#d29922"   # Ambre
ACCENT_PURPLE = "#bc8cff"  # Violet


def get_flag_image(country_code):
    """
    Récupère le drapeau PNG d'un pays depuis le cache local ou le télécharge (40px)
    depuis flagcdn.com. Retourne l'image numpy array ou None.
    """
    if not country_code or country_code in ("Inconnu", "Local"):
        return None

    code_lower = country_code.lower()
    flag_file = FLAGS_DIR / f"{code_lower}.png"

    # 1. Vérification dans le cache local
    if flag_file.exists():
        try:
            return mpimg.imread(str(flag_file))
        except Exception:
            pass

    # 2. Téléchargement depuis CDN fiable et sécurisé
    url = f"https://flagcdn.com/w40/{code_lower}.png"
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            with open(flag_file, "wb") as f:
                f.write(resp.content)
            return mpimg.imread(io.BytesIO(resp.content), format="png")
    except Exception:
        pass

    return None


def setup_dark_axis(ax, title=""):
    """Applique le thème sombre et le style à un repère Matplotlib."""
    ax.set_facecolor(CARD_BG)
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold", color=TEXT_MAIN, pad=10)

    # Couleurs des axes et graduations
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(BORDER_COLOR)
        spine.set_linewidth(1.2)

    ax.grid(color=GRID_COLOR, linestyle="--", linewidth=0.7, alpha=0.6)


def show_dashboard(stats):
    """
    Affiche le tableau de bord interactif en Dark Mode avec les drapeaux PNG des pays.
    """
    fig, axs = plt.subplots(2, 2, figsize=(15, 10))
    fig.patch.set_facecolor(DARK_BG)
    fig.canvas.manager.set_window_title("Log Analyzer - Dashboard Sécurité ESISA (Dark Mode)")

    # Titre général du dashboard
    fig.suptitle(
        "LOG ANALYZER - DASHBOARD DE SÉCURITÉ & STATISTIQUES (ESISA)",
        fontsize=15,
        fontweight="bold",
        color=TEXT_MAIN,
        y=0.98
    )

    # ── 1. Graphique 1 : Top des Pays Sources (avec Drapeaux PNG) ──
    ax1 = axs[0, 0]
    setup_dark_axis(ax1, title="Top 8 des Pays d'Origine des Attaques (avec Drapeaux)")

    top_countries = stats["countries"].most_common(8)
    if top_countries:
        codes = [c[0] for c in reversed(top_countries)]
        c_names = [f"{COUNTRY_NAMES.get(code, code)} ({code})" for code in codes]
        c_vals = [c[1] for c in reversed(top_countries)]
        max_val = max(c_vals) if c_vals else 1

        bars1 = ax1.barh(c_names, c_vals, color=ACCENT_BLUE, edgecolor="#1f6feb", alpha=0.9, height=0.6)
        ax1.set_xlabel("Nombre de requêtes d'attaques", color=TEXT_MUTED, fontsize=9)
        ax1.set_xlim(0, max_val * 1.35)

        for idx, (bar, code, val) in enumerate(zip(bars1, codes, c_vals)):
            # Affichage du nombre de requêtes
            ax1.text(
                val + max_val * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}",
                va="center",
                ha="left",
                color=TEXT_MAIN,
                fontsize=8.5,
                fontweight="bold"
            )

            # Insertion du drapeau PNG à côté de la valeur
            flag_img = get_flag_image(code)
            if flag_img is not None:
                imagebox = OffsetImage(flag_img, zoom=0.55)
                ab = AnnotationBbox(
                    imagebox,
                    (val + max_val * 0.18, idx),
                    frameon=False,
                    box_alignment=(0.5, 0.5)
                )
                ax1.add_artist(ab)

    # ── 2. Graphique 2 : Répartition des Types d'Événements ──
    ax2 = axs[0, 1]
    setup_dark_axis(ax2, title="Répartition des Types d'Événements de Sécurité")

    top_events = stats["events"].most_common(5)
    if top_events:
        e_names = [e[0] for e in top_events]
        e_vals = [e[1] for e in top_events]
        colors = [ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE, ACCENT_GREEN, ACCENT_PURPLE]

        wedges, texts, autotexts = ax2.pie(
            e_vals,
            labels=e_names,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors[:len(e_names)],
            wedgeprops=dict(width=0.45, edgecolor=DARK_BG, linewidth=2)
        )
        for t in texts:
            t.set_color(TEXT_MUTED)
            t.set_fontsize(8.5)
        for at in autotexts:
            at.set_color(TEXT_MAIN)
            at.set_fontsize(8.5)
            at.set_fontweight("bold")

    # ── 3. Graphique 3 : Top des Adresses IP Attaquantes (avec Pays) ──
    ax3 = axs[1, 0]
    setup_dark_axis(ax3, title="Top 8 des Adresses IP les Plus Agressives")

    top_ips = stats["ips"].most_common(8)
    if top_ips:
        ip_labels = []
        ip_codes = []
        for item in reversed(top_ips):
            ip = item[0]
            code = stats.get("ip_locations", {}).get(ip, {}).get("country", "")
            country_name = COUNTRY_NAMES.get(code, code)
            suffix = f" [{country_name}]" if code else ""
            ip_labels.append(f"{ip}{suffix}")
            ip_codes.append(code)

        ip_vals = [item[1] for item in reversed(top_ips)]
        max_ip_val = max(ip_vals) if ip_vals else 1

        bars3 = ax3.barh(ip_labels, ip_vals, color=ACCENT_RED, edgecolor="#da3633", alpha=0.85, height=0.6)
        ax3.set_xlabel("Nombre de tentatives bloquées", color=TEXT_MUTED, fontsize=9)
        ax3.set_xlim(0, max_ip_val * 1.35)

        for idx, (bar, code, val) in enumerate(zip(bars3, ip_codes, ip_vals)):
            ax3.text(
                val + max_ip_val * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}",
                va="center",
                ha="left",
                color=TEXT_MAIN,
                fontsize=8.5,
                fontweight="bold"
            )
            flag_img = get_flag_image(code)
            if flag_img is not None:
                imagebox = OffsetImage(flag_img, zoom=0.5)
                ab = AnnotationBbox(
                    imagebox,
                    (val + max_ip_val * 0.18, idx),
                    frameon=False,
                    box_alignment=(0.5, 0.5)
                )
                ax3.add_artist(ab)

    # ── 4. Graphique 4 : Distribution Horaire des Attaques ──
    ax4 = axs[1, 1]
    setup_dark_axis(ax4, title="Activité et Fréquence des Attaques par Heure (00h - 23h)")

    hours = list(range(24))
    h_vals = [stats["hourly"].get(h, 0) for h in hours]

    ax4.plot(hours, h_vals, color=ACCENT_GREEN, marker="o", linewidth=2.4, markersize=4.5)
    ax4.fill_between(hours, h_vals, color=ACCENT_GREEN, alpha=0.18)

    ax4.set_xlabel("Heure de la journée", color=TEXT_MUTED, fontsize=9)
    ax4.set_ylabel("Volume d'attaques", color=TEXT_MUTED, fontsize=9)
    ax4.set_xticks(hours[::2])
    ax4.set_xticklabels([f"{h:02d}h" for h in hours[::2]])

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    print("[+] Lancement du Dashboard Dark Mode interactif à l'écran...")
    plt.show()


if __name__ == "__main__":
    dummy = {
        "countries": Counter({"RO": 5929, "NL": 4980, "VN": 1189, "FI": 985, "LT": 659}),
        "events": Counter({"Failed Password": 10962, "Invalid User": 3166, "Accepted Login": 734, "Connection Closed": 3152}),
        "ips": Counter({"203.171.18.62": 395, "45.148.10.152": 299, "45.227.254.170": 235}),
        "hourly": Counter({h: (h * 47) % 300 + 100 for h in range(24)}),
        "ip_locations": {"203.171.18.62": {"country": "VN"}, "45.148.10.152": {"country": "NL"}}
    }
    show_dashboard(dummy)
