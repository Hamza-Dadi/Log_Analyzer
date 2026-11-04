import io
import sys
from pathlib import Path
from collections import Counter
import requests
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# Permet l'import de la configuration si exécuté de façon isolée
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.logger import get_logger

logger = get_logger("Serving.visualizer")

"""
Module Serving / Visualisation Interactive (Dark Theme + Drapeaux PNG) :
Affiche les 3 graphiques demandés par le professeur directement à l'écran :
1. Nombre de tentatives échouées par pays (avec drapeaux PNG).
2. Nombre de tentatives réussies par utilisateur.
3. Tentatives échouées avec utilisateur invalide (Invalid user).
4. Synthèse et indicateurs clés de sécurité (KPIs).
"""

FLAGS_DIR = ROOT_DIR / "Storage" / "flags"
FLAGS_DIR.mkdir(parents=True, exist_ok=True)

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
    "TH": "Thaïlande",
    "CL": "Chili"
}

# Palette de couleurs Thème Sombre (Dark Mode)
DARK_BG = "#0d1117"        # Fond principal (Dark GitHub)
CARD_BG = "#161b22"        # Fond des panneaux graphiques
BORDER_COLOR = "#30363d"   # Bordures discrètes
GRID_COLOR = "#21262d"     # Lignes de repères
TEXT_MAIN = "#f0f6fc"      # Texte principal blanc
TEXT_MUTED = "#8b949e"     # Texte secondaire gris clair
ACCENT_BLUE = "#58a6ff"    # Bleu néon
ACCENT_RED = "#f85149"     # Rouge alerte
ACCENT_GREEN = "#3fb950"   # Vert émeraude
ACCENT_AMBER = "#d29922"   # Ambre
ACCENT_PURPLE = "#bc8cff"  # Violet


def get_flag_image(country_code):
    """
    Récupère le drapeau PNG d'un pays depuis le cache local ou le télécharge (40px).
    Retourne l'image numpy array ou None en cas d'échec.
    """
    if not country_code or country_code in ("Inconnu", "Local"):
        return None

    code_lower = country_code.lower()
    flag_file = FLAGS_DIR / f"{code_lower}.png"

    # 1. Vérification dans le cache local
    if flag_file.exists():
        try:
            return mpimg.imread(str(flag_file))
        except Exception as e:
            logger.warning(f"Erreur de lecture du drapeau local {flag_file} : {e}")

    # 2. Téléchargement depuis CDN sécurisé flagcdn.com
    url = f"https://flagcdn.com/w40/{code_lower}.png"
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            with open(flag_file, "wb") as f:
                f.write(resp.content)
            logger.debug(f"Drapeau telecharge et mis en cache : {code_lower}.png")
            return mpimg.imread(io.BytesIO(resp.content), format="png")
        else:
            logger.warning(f"Drapeau introuvable pour {country_code} (HTTP {resp.status_code})")
    except Exception as e:
        logger.warning(f"Impossible de recuperer le drapeau pour {country_code} : {e}")

    return None


def setup_dark_axis(ax, title=""):
    """Applique le thème sombre et le style soigné à un repère Matplotlib."""
    ax.set_facecolor(CARD_BG)
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold", color=TEXT_MAIN, pad=10)

    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(BORDER_COLOR)
        spine.set_linewidth(1.2)

    ax.grid(color=GRID_COLOR, linestyle="--", linewidth=0.7, alpha=0.6)


def show_dashboard(stats):
    """
    Affiche le tableau de bord interactif en Dark Mode avec les 3 métriques exactes
    demandées par le professeur + une carte récapitulative des KPIs.
    """
    logger.info("Generation du dashboard interactif Matplotlib...")

    fig, axs = plt.subplots(2, 2, figsize=(16, 9.5))
    fig.patch.set_facecolor(DARK_BG)
    try:
        fig.canvas.manager.set_window_title("Log Analyzer - Dashboard Securite (Dark Mode)")
    except Exception:
        pass

    # Titre général du dashboard
    fig.suptitle(
        "LOG ANALYZER - DASHBOARD DE SECURITE & STATISTIQUES",
        fontsize=15,
        fontweight="bold",
        color=TEXT_MAIN,
        y=0.98
    )

    # Extraction des données requises
    failed_by_country = stats.get("failed_by_country", [])
    successful_by_user = stats.get("successful_by_user", [])
    failed_invalid_users = stats.get("failed_invalid_users", [])

    # Compatibilité de secours si ancien format passé
    if not failed_by_country and "countries" in stats:
        failed_by_country = stats["countries"].most_common(8)
    if not failed_invalid_users and "top_10_targeted_users" in stats:
        failed_invalid_users = stats["top_10_targeted_users"][:8]

    # ── 1. Graphique 1 : Nombre de tentatives échouées par pays (avec drapeaux) ──
    ax1 = axs[0, 0]
    setup_dark_axis(ax1, title="1. Nombre de Tentatives Echouees par Pays (avec Drapeaux)")

    if failed_by_country:
        codes = [item[0] for item in reversed(failed_by_country)]
        names = [f"{COUNTRY_NAMES.get(c, c)} ({c})" for c in codes]
        vals = [item[1] for item in reversed(failed_by_country)]
        max_val = max(vals) if vals else 1

        bars1 = ax1.barh(names, vals, color=ACCENT_RED, edgecolor="#da3633", alpha=0.9, height=0.6)
        ax1.set_xlabel("Nombre d'attaques echouees", color=TEXT_MUTED, fontsize=9)
        ax1.set_xlim(0, max_val * 1.35)

        for idx, (bar, code, val) in enumerate(zip(bars1, codes, vals)):
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

    # ── 2. Graphique 2 : Nombre de tentatives réussies par utilisateur ──
    ax2 = axs[0, 1]
    setup_dark_axis(ax2, title="2. Nombre de Tentatives Reussies par Utilisateur")

    if successful_by_user:
        users = [item[0] for item in successful_by_user]
        u_vals = [item[1] for item in successful_by_user]

        bars2 = ax2.bar(users, u_vals, color=ACCENT_GREEN, edgecolor="#238636", alpha=0.9, width=0.45)
        ax2.set_ylabel("Connexions / Sessions legitimes", color=TEXT_MUTED, fontsize=9)
        ax2.set_yscale("log")  # Échelle logarithmique car root (sessions) et adminesisa (ssh) diffèrent en volume
        ax2.set_ylim(0.5, max(u_vals) * 5)

        for bar, val in zip(bars2, u_vals):
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                val * 1.25,
                f"{val:,}",
                ha="center",
                va="bottom",
                color=TEXT_MAIN,
                fontsize=9.5,
                fontweight="bold"
            )
        ax2.text(
            0.5, 0.90,
            "(Echelle logarithmique : adminesisa = SSH, root = Sessions systeme)",
            transform=ax2.transAxes,
            ha="center",
            color=TEXT_MUTED,
            fontsize=8,
            style="italic"
        )

    # ── 3. Graphique 3 : Tentatives échouées avec utilisateur invalide ──
    ax3 = axs[1, 0]
    setup_dark_axis(ax3, title="3. Tentatives Echouees avec Utilisateur Invalide (Top Comptes)")

    if failed_invalid_users:
        inv_users = [item[0] for item in reversed(failed_invalid_users)]
        inv_vals = [item[1] for item in reversed(failed_invalid_users)]
        max_inv = max(inv_vals) if inv_vals else 1

        bars3 = ax3.barh(inv_users, inv_vals, color=ACCENT_AMBER, edgecolor="#9e6a03", alpha=0.9, height=0.6)
        ax3.set_xlabel("Nombre de tentatives de brute-force", color=TEXT_MUTED, fontsize=9)
        ax3.set_xlim(0, max_inv * 1.25)

        for bar, val in zip(bars3, inv_vals):
            ax3.text(
                val + max_inv * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}",
                va="center",
                ha="left",
                color=TEXT_MAIN,
                fontsize=8.5,
                fontweight="bold"
            )

    # ── 4. Panneau 4 : Synthèse de Sécurité & KPIs Globaux ──
    ax4 = axs[1, 1]
    setup_dark_axis(ax4, title="Synthese Globale & Indicateurs de Securite (KPIs)")
    ax4.grid(False)

    # Données KPI
    tot_failed = sum(v for _, v in failed_by_country) if failed_by_country else 0
    tot_invalid = sum(v for _, v in failed_invalid_users) if failed_invalid_users else 0
    tot_success = sum(v for _, v in successful_by_user) if successful_by_user else 0
    top_attacker_country = failed_by_country[0][0] if failed_by_country else "N/A"
    top_attacker_name = COUNTRY_NAMES.get(top_attacker_country, top_attacker_country)
    top_invalid_name = failed_invalid_users[0][0] if failed_invalid_users else "N/A"

    kpi_text = (
        f"  INDICATEURS CLES DE SURVEILLANCE\n\n"
        f"  Total Tentatives Echouees  : {tot_failed:,} (Top pays)\n"
        f"  Faux Utilisateurs Cibles   : {tot_invalid:,} tentatives\n"
        f"  Connexions Legitimes       : {tot_success:,} sessions\n\n"
        f"  Pays Attaquant N 1         : {top_attacker_name} ({top_attacker_country})\n"
        f"  Compte Invalide N 1        : '{top_invalid_name}' ({failed_invalid_users[0][1] if failed_invalid_users else 0} fois)\n\n"
        f"  Statut du Systeme          : SURVEILLANCE ACTIVE\n"
        f"  Journalisation             : app.log (RotatingFileHandler)"
    )

    ax4.text(
        0.08, 0.5,
        kpi_text,
        transform=ax4.transAxes,
        va="center",
        ha="left",
        fontsize=10,
        fontfamily="monospace",
        color=TEXT_MAIN,
        bbox=dict(boxstyle="round,pad=1.2", facecolor="#21262d", edgecolor=BORDER_COLOR, linewidth=1.5)
    )
    ax4.set_xticks([])
    ax4.set_yticks([])

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    logger.info("Affichage de la fenetre interactive du dashboard.")
    print("[+] Lancement du Dashboard Dark Mode avec les 3 metriques a l'ecran...")
    plt.show()


if __name__ == "__main__":
    dummy_stats = {
        "failed_by_country": [("RO", 2561), ("NL", 2149), ("VN", 368), ("FI", 337), ("PL", 336), ("LT", 286), ("CL", 153), ("GB", 129)],
        "successful_by_user": [("root", 2138), ("adminesisa", 3)],
        "failed_invalid_users": [("admin", 407), ("esisa", 193), ("ubuntu", 144), ("user", 109), ("test", 82), ("support", 75), ("dev", 70), ("solana", 68)]
    }
    print("Test unitaire visualizer : syntaxe valide.")
