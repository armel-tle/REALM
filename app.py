import sqlite3
import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response

app = Flask(__name__)
app.secret_key = "change-cette-cle-en-production"
DB_PATH = "realm.db"
NOM_APP = "Realm"


# ---------- Base de données ----------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            quantite INTEGER NOT NULL DEFAULT 0,
            seuil_alerte INTEGER NOT NULL DEFAULT 5,
            prix_achat REAL NOT NULL DEFAULT 0,
            prix_vente REAL NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            telephone TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ventes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produit_id INTEGER NOT NULL,
            quantite_vendue INTEGER NOT NULL,
            date_vente TEXT NOT NULL,
            client_id INTEGER,
            est_credit INTEGER NOT NULL DEFAULT 0,
            paye INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (produit_id) REFERENCES produits (id),
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            libelle TEXT NOT NULL,
            montant REAL NOT NULL,
            date_depense TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def maintenant():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------- Tableau de bord ----------

@app.route("/")
def index():
    conn = get_db()
    produits = conn.execute("SELECT * FROM produits ORDER BY nom").fetchall()

    stock_bas = [p for p in produits if p["quantite"] <= p["seuil_alerte"]]

    plus_rentable = None
    if produits:
        candidat = max(produits, key=lambda p: (p["prix_vente"] - p["prix_achat"]))
        if (candidat["prix_vente"] - candidat["prix_achat"]) > 0:
            plus_rentable = candidat

    ventes = conn.execute("""
        SELECT v.quantite_vendue, p.prix_achat, p.prix_vente, p.nom
        FROM ventes v JOIN produits p ON v.produit_id = p.id
    """).fetchall()
    chiffre_affaires = sum(v["quantite_vendue"] * v["prix_vente"] for v in ventes)
    marge_ventes = sum(v["quantite_vendue"] * (v["prix_vente"] - v["prix_achat"]) for v in ventes)

    total_depenses = conn.execute("SELECT COALESCE(SUM(montant), 0) AS total FROM depenses").fetchone()["total"]
    benefice_estime = marge_ventes - total_depenses

    valeur_stock = sum(p["quantite"] * p["prix_achat"] for p in produits)

    credits_clients = conn.execute("""
        SELECT COALESCE(SUM(v.quantite_vendue * p.prix_vente), 0) AS total
        FROM ventes v JOIN produits p ON v.produit_id = p.id
        WHERE v.est_credit = 1 AND v.paye = 0
    """).fetchone()["total"]

    ventes_par_produit = {}
    for v in ventes:
        ventes_par_produit[v["nom"]] = ventes_par_produit.get(v["nom"], 0) + v["quantite_vendue"]
    produit_plus_vendu = max(ventes_par_produit, key=ventes_par_produit.get) if ventes_par_produit else None

    conn.close()
    return render_template(
        "index.html",
        stock_bas=stock_bas,
        plus_rentable=plus_rentable,
        chiffre_affaires=chiffre_affaires,
        benefice_estime=benefice_estime,
        valeur_stock=valeur_stock,
        credits_clients=credits_clients,
        produit_plus_vendu=produit_plus_vendu,
        nb_produits=len(produits),
    )


# ---------- Produits & stock ----------

@app.route("/produits")
def produits():
    conn = get_db()
    liste = conn.execute("SELECT * FROM produits ORDER BY nom").fetchall()
    conn.close()
    return render_template("produits.html", produits=liste)


@app.route("/produits/ajouter", methods=["POST"])
def ajouter_produit():
    nom = request.form.get("nom", "").strip()
    try:
        quantite = int(request.form.get("quantite", "0"))
        seuil_alerte = int(request.form.get("seuil_alerte", "5"))
        prix_achat = float(request.form.get("prix_achat", "0"))
        prix_vente = float(request.form.get("prix_vente", "0"))
    except ValueError:
        flash("Les quantités et prix doivent être des nombres.", "erreur")
        return redirect(url_for("produits"))

    if not nom:
        flash("Le nom du produit est obligatoire.", "erreur")
        return redirect(url_for("produits"))

    conn = get_db()
    conn.execute(
        "INSERT INTO produits (nom, quantite, seuil_alerte, prix_achat, prix_vente) VALUES (?, ?, ?, ?, ?)",
        (nom, quantite, seuil_alerte, prix_achat, prix_vente),
    )
    conn.commit()
    conn.close()
    flash(f"Produit « {nom} » ajouté au stock.", "succes")
    return redirect(url_for("produits"))


@app.route("/produits/<int:produit_id>/supprimer", methods=["POST"])
def supprimer_produit(produit_id):
    conn = get_db()
    conn.execute("DELETE FROM produits WHERE id = ?", (produit_id,))
    conn.commit()
    conn.close()
    flash("Produit supprimé.", "succes")
    return redirect(url_for("produits"))


# ---------- Ventes ----------

@app.route("/ventes")
def ventes():
    conn = get_db()
    produits = conn.execute("SELECT * FROM produits ORDER BY nom").fetchall()
    clients = conn.execute("SELECT * FROM clients ORDER BY nom").fetchall()
    historique = conn.execute("""
        SELECT v.id, v.quantite_vendue, v.date_vente, v.est_credit, v.paye,
               p.nom AS produit_nom,
               c.nom AS client_nom,
               (v.quantite_vendue * p.prix_vente) AS total_vente,
               (v.quantite_vendue * (p.prix_vente - p.prix_achat)) AS marge
        FROM ventes v
        JOIN produits p ON v.produit_id = p.id
        LEFT JOIN clients c ON v.client_id = c.id
        ORDER BY v.id DESC
        LIMIT 25
    """).fetchall()
    conn.close()
    return render_template("ventes.html", produits=produits, clients=clients, historique=historique)


@app.route("/ventes/enregistrer", methods=["POST"])
def enregistrer_vente():
    try:
        produit_id = int(request.form.get("produit_id"))
        quantite_vendue = int(request.form.get("quantite_vendue", "0"))
    except (ValueError, TypeError):
        flash("Vente invalide.", "erreur")
        return redirect(url_for("ventes"))

    client_id = request.form.get("client_id") or None
    est_credit = 1 if request.form.get("est_credit") == "on" else 0
    paye = 0 if est_credit else 1

    if quantite_vendue <= 0:
        flash("La quantité vendue doit être supérieure à 0.", "erreur")
        return redirect(url_for("ventes"))

    conn = get_db()
    produit = conn.execute("SELECT * FROM produits WHERE id = ?", (produit_id,)).fetchone()

    if produit is None:
        flash("Produit introuvable.", "erreur")
        conn.close()
        return redirect(url_for("ventes"))

    if quantite_vendue > produit["quantite"]:
        flash(f"Stock insuffisant : il reste {produit['quantite']} unité(s) de « {produit['nom']} ».", "erreur")
        conn.close()
        return redirect(url_for("ventes"))

    conn.execute(
        "INSERT INTO ventes (produit_id, quantite_vendue, date_vente, client_id, est_credit, paye) VALUES (?, ?, ?, ?, ?, ?)",
        (produit_id, quantite_vendue, maintenant(), client_id, est_credit, paye),
    )
    conn.execute("UPDATE produits SET quantite = quantite - ? WHERE id = ?", (quantite_vendue, produit_id))
    conn.commit()
    conn.close()
    flash(f"Vente enregistrée : {quantite_vendue} x « {produit['nom']} ».", "succes")
    return redirect(url_for("ventes"))


# ---------- Dépenses ----------

@app.route("/depenses")
def depenses():
    conn = get_db()
    liste = conn.execute("SELECT * FROM depenses ORDER BY id DESC").fetchall()
    total = conn.execute("SELECT COALESCE(SUM(montant), 0) AS total FROM depenses").fetchone()["total"]
    conn.close()
    return render_template("depenses.html", depenses=liste, total=total)


@app.route("/depenses/ajouter", methods=["POST"])
def ajouter_depense():
    libelle = request.form.get("libelle", "").strip()
    try:
        montant = float(request.form.get("montant", "0"))
    except ValueError:
        flash("Le montant doit être un nombre.", "erreur")
        return redirect(url_for("depenses"))

    if not libelle or montant <= 0:
        flash("Indique un libellé et un montant valide.", "erreur")
        return redirect(url_for("depenses"))

    conn = get_db()
    conn.execute(
        "INSERT INTO depenses (libelle, montant, date_depense) VALUES (?, ?, ?)",
        (libelle, montant, maintenant()),
    )
    conn.commit()
    conn.close()
    flash("Dépense enregistrée.", "succes")
    return redirect(url_for("depenses"))


@app.route("/depenses/<int:depense_id>/supprimer", methods=["POST"])
def supprimer_depense(depense_id):
    conn = get_db()
    conn.execute("DELETE FROM depenses WHERE id = ?", (depense_id,))
    conn.commit()
    conn.close()
    flash("Dépense supprimée.", "succes")
    return redirect(url_for("depenses"))


# ---------- Clients & crédits ----------

@app.route("/clients")
def clients():
    conn = get_db()
    liste = conn.execute("SELECT * FROM clients ORDER BY nom").fetchall()

    credits_par_client = []
    for c in liste:
        du = conn.execute("""
            SELECT v.id, v.date_vente, v.quantite_vendue, p.nom,
                   (v.quantite_vendue * p.prix_vente) AS total
            FROM ventes v JOIN produits p ON v.produit_id = p.id
            WHERE v.client_id = ? AND v.est_credit = 1 AND v.paye = 0
        """, (c["id"],)).fetchall()
        total_du = sum(d["total"] for d in du)
        if total_du > 0:
            credits_par_client.append({"client": c, "total_du": total_du, "details": du})

    conn.close()
    return render_template("clients.html", clients=liste, credits=credits_par_client)


@app.route("/clients/ajouter", methods=["POST"])
def ajouter_client():
    nom = request.form.get("nom", "").strip()
    telephone = request.form.get("telephone", "").strip()

    if not nom:
        flash("Le nom du client est obligatoire.", "erreur")
        return redirect(url_for("clients"))

    conn = get_db()
    conn.execute("INSERT INTO clients (nom, telephone) VALUES (?, ?)", (nom, telephone))
    conn.commit()
    conn.close()
    flash(f"Client « {nom} » ajouté.", "succes")
    return redirect(url_for("clients"))


@app.route("/ventes/<int:vente_id>/marquer_paye", methods=["POST"])
def marquer_paye(vente_id):
    conn = get_db()
    conn.execute("UPDATE ventes SET paye = 1 WHERE id = ?", (vente_id,))
    conn.commit()
    conn.close()
    flash("Crédit marqué comme payé.", "succes")
    return redirect(url_for("clients"))


# ---------- Rapports ----------

@app.route("/rapports")
def rapports():
    conn = get_db()

    top_produits = conn.execute("""
        SELECT p.nom, SUM(v.quantite_vendue) AS total_vendu,
               SUM(v.quantite_vendue * (p.prix_vente - p.prix_achat)) AS marge_totale
        FROM ventes v JOIN produits p ON v.produit_id = p.id
        GROUP BY p.id
        ORDER BY total_vendu DESC
        LIMIT 10
    """).fetchall()

    ventes_par_jour = conn.execute("""
        SELECT SUBSTR(v.date_vente, 1, 10) AS jour,
               SUM(v.quantite_vendue * p.prix_vente) AS total_jour
        FROM ventes v JOIN produits p ON v.produit_id = p.id
        GROUP BY jour
        ORDER BY jour DESC
        LIMIT 14
    """).fetchall()

    depenses_par_type = conn.execute("""
        SELECT libelle, SUM(montant) AS total
        FROM depenses
        GROUP BY libelle
        ORDER BY total DESC
        LIMIT 10
    """).fetchall()

    conn.close()
    return render_template(
        "rapports.html",
        top_produits=top_produits,
        ventes_par_jour=ventes_par_jour,
        depenses_par_type=depenses_par_type,
    )


# ---------- Données (export / réinitialisation) ----------

@app.route("/donnees")
def donnees():
    conn = get_db()
    nb_produits = conn.execute("SELECT COUNT(*) AS n FROM produits").fetchone()["n"]
    nb_ventes = conn.execute("SELECT COUNT(*) AS n FROM ventes").fetchone()["n"]
    nb_clients = conn.execute("SELECT COUNT(*) AS n FROM clients").fetchone()["n"]
    nb_depenses = conn.execute("SELECT COUNT(*) AS n FROM depenses").fetchone()["n"]
    conn.close()
    return render_template(
        "donnees.html",
        nb_produits=nb_produits,
        nb_ventes=nb_ventes,
        nb_clients=nb_clients,
        nb_depenses=nb_depenses,
    )


@app.route("/donnees/export/<table>")
def exporter_csv(table):
    tables_autorisees = {
        "produits": "SELECT nom, quantite, seuil_alerte, prix_achat, prix_vente FROM produits",
        "ventes": """
            SELECT v.date_vente, p.nom AS produit, v.quantite_vendue,
                   (v.quantite_vendue * p.prix_vente) AS total,
                   c.nom AS client, v.est_credit, v.paye
            FROM ventes v JOIN produits p ON v.produit_id = p.id
            LEFT JOIN clients c ON v.client_id = c.id
        """,
        "depenses": "SELECT libelle, montant, date_depense FROM depenses",
        "clients": "SELECT nom, telephone FROM clients",
    }

    if table not in tables_autorisees:
        flash("Export invalide.", "erreur")
        return redirect(url_for("donnees"))

    conn = get_db()
    lignes = conn.execute(tables_autorisees[table]).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    if lignes:
        writer.writerow(lignes[0].keys())
        for ligne in lignes:
            writer.writerow(list(ligne))

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table}_realm.csv"},
    )


@app.route("/donnees/reinitialiser", methods=["POST"])
def reinitialiser_donnees():
    conn = get_db()
    conn.execute("DELETE FROM ventes")
    conn.execute("DELETE FROM depenses")
    conn.execute("DELETE FROM clients")
    conn.execute("DELETE FROM produits")
    conn.commit()
    conn.close()
    flash("Toutes les données ont été réinitialisées.", "succes")
    return redirect(url_for("donnees"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
else:
    init_db()
