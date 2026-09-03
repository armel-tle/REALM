# Realm — installation et déploiement

## Ce que contient ce dossier

```
realm_app/
├── app.py                  <- le backend Flask (toute la logique)
├── requirements.txt
├── templates/
│   ├── base.html            <- sidebar + SEO + PWA
│   ├── index.html           <- tableau de bord
│   ├── produits.html
│   ├── ventes.html
│   ├── depenses.html
│   ├── clients.html         <- clients + suivi des crédits
│   ├── rapports.html
│   └── donnees.html         <- export CSV + réinitialisation
└── static/
    ├── style.css             <- thème "royal" (violet + or)
    ├── manifest.json
    ├── service-worker.js
    └── icons/
        ├── icon-192.png      <- logo couronne
        └── icon-512.png
```

## Ce qui a changé par rapport à la version précédente

- **Nouveau nom** : Realm (anagramme d'Armel)
- **Nouveau design** : thème violet royal + or, typographie Playfair Display
  pour les titres, structure en barre latérale (comme sur ta capture d'écran)
- **Emojis** intégrés dans la navigation et les titres
- **Nouvelles fonctionnalités** :
  - 💸 **Dépenses** : enregistrer les charges (transport, loyer...) pour un
    bénéfice réaliste
  - 👥 **Clients & crédits** : ajouter des clients, faire des ventes à
    crédit, suivre qui doit combien, marquer un crédit comme payé
  - 📊 **Rapports** : classement des produits les plus vendus, ventes des
    14 derniers jours, répartition des dépenses
  - 🗂️ **Données** : exporter chaque table en CSV, ou tout réinitialiser
- **SEO** : balises meta title/description/keywords sur chaque page, pour un
  meilleur référencement sur Google

## Étape 1 : remplacer le contenu de ton dépôt GitHub

Sur `github.com/armel-tle/KmerGestion` (tu peux renommer le dépôt en
`Realm` dans les paramètres GitHub si tu veux que ça suive le nouveau nom) :

1. Supprime tous les anciens fichiers du dépôt (`index.html` et tout
   fichier Flask précédent s'il y en avait)
2. Upload tous les fichiers et dossiers de ce zip à la racine du dépôt,
   en gardant la structure `templates/` et `static/`

## Étape 2 : tester en local (recommandé)

```bash
pip install -r requirements.txt
python app.py
```

Ouvre `http://127.0.0.1:5000` dans ton navigateur.

## Étape 3 : configurer Render

1. Sur Render, ouvre les paramètres de ton service
2. **Build Command** :
   ```
   pip install -r requirements.txt
   ```
3. **Start Command** :
   ```
   gunicorn app:app
   ```
4. Vérifie que l'Environment est bien "Python 3"

Si ton service est encore configuré comme "Static Site", il faut le
recréer en "Web Service" — un site statique ne peut pas exécuter de code
Python.

## Étape 4 : pousser et déployer

```bash
git add .
git commit -m "Refonte complète : Realm avec dépenses, clients, crédits, rapports"
git push
```

Render redéploiera automatiquement.

## Limite importante

La base de données (`realm.db`) est stockée sur le disque du serveur.
Sur le plan gratuit de Render, **ce disque n'est pas permanent** — les
données peuvent être effacées à chaque redéploiement.

Pour un usage réel avec de vrais commerçants, il faudra migrer vers une
base de données externe (PostgreSQL, proposé aussi par Render). On peut
faire cette migration ensemble dès que tu es prêt à passer en production.

## Prochaines étapes possibles

- Ajouter une page de connexion (un compte par commerçant)
- Ajouter les notifications (stock bas, crédits en retard) via Web Push
- Migrer vers PostgreSQL pour la mise en production
- Renommer le dépôt GitHub et le service Render en "Realm" pour que
  l'URL corresponde au nouveau nom (actuellement encore en
  `kmergestion.onrender.com`)
