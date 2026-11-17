# EduCert Maroc v4 — DApp + SQLite

Version finalisée du prototype : rôles université/faculté, émission et révocation contrôlées,
vérification publique sans MetaMask, calcul SHA-256 local et base SQLite d'audit.

## Architecture

`HTML/MetaMask -> EduCert_v2 sur Sepolia`

`HTML -> API FastAPI -> SQLite`

La blockchain conserve la preuve (hash, version, statut et événements). SQLite conserve
l'identifiant, l'université, la faculté, l'émetteur, le hash, la transaction et les dates.
Les PDF restent locaux. La lecture et la vérification peuvent utiliser le RPC Sepolia public
sans connecter MetaMask ; MetaMask est nécessaire uniquement pour les transactions.

## Démarrage

```powershell
py -m pip install -r requirements.txt
py -m uvicorn backend.app:app --host 127.0.0.1 --port 8020
```

API : `http://127.0.0.1:8020/api/health` — la base est créée dans `data/educert.sqlite3`.

Dans `config.js`, configurez `apiBase: "http://127.0.0.1:8020"`, puis servez le frontend avec :

```bash
py -m http.server 8080 --bind 0.0.0.0
```

Après confirmation blockchain, l'interface enregistre les métadonnées dans SQLite ; après révocation,
elle met à jour le statut local. Ne mettez jamais de clé privée ou de données personnelles sensibles
dans le frontend.

## Scénario E2E

1. Déployer `EduCert_v2.sol` avec le compte national sur Sepolia.
2. Copier l'adresse dans `config.js`.
3. Lancer l'API sur 8020 puis le frontend sur 8080.
4. Compte national : enregistrer l'université et son administrateur.
5. Administrateur université : enregistrer une faculté et lui attribuer Émettre/Révoquer.
6. Compte faculté : sélectionner un PDF et ancrer le certificat.
7. Vérifier le certificat avec le PDF original, sans MetaMask si nécessaire.
8. Révoquer avec un compte autorisé et vérifier le statut `REVOKED`.

## QR de certification

Après avoir lu un certificat et affiché son hash, cliquez sur **Générer le QR du certificat lu**.
Le QR encode l'URL publique de la page avec `certificate`, `version` et `hash`. Lorsqu'un
consommateur scanne le QR, la page charge automatiquement le certificat via le RPC Sepolia
et affiche `QR vérifié : certificat valide et actif`, sans demander MetaMask.

Pour un test avec un téléphone sur le même Wi-Fi, `config.js` contient :
`publicBaseUrl: "http://192.168.11.107:8080/"`.
Remplacez cette adresse par l'IP locale réelle du PC (`hostname -I`) si nécessaire.
Le téléphone doit être sur le même Wi-Fi et le serveur doit écouter sur `0.0.0.0`.
Pour éviter toute saisie, ouvrez directement EduCert avec l'IP réseau du PC :
`http://192.168.11.107:8082/`. Le QR reprend automatiquement cette adresse et ce port.
Si vous ouvrez la page avec `localhost`, le QR contiendra naturellement `localhost`.
Pour une utilisation partout, remplacez ensuite cette valeur par une URL HTTPS publique.
Après toute modification, générez un **nouveau QR** : un ancien QR contenant `localhost`
conserve naturellement son ancienne adresse.

Le QR ajoute `view=qr`. Après le scan, la blockchain est vérifiée via Sepolia mais l'écran
mobile affiche uniquement `🏆` si le certificat est valide, ou `❌` s'il est invalide/révoqué.

## Vérifications utiles

```text
http://127.0.0.1:8020/api/health
http://127.0.0.1:8020/docs
http://127.0.0.1:8080
```

La preuve complète est : `document_hash` + `tx_hash` + adresse du contrat + réseau Sepolia.

## Version pilote

Voir [`PILOTE.md`](PILOTE.md) pour la sauvegarde SQLite, l'audit, la préparation PostgreSQL
et l'authentification institutionnelle OIDC/JWT. Une sauvegarde rapide se crée avec :

```bash
python scripts/backup_sqlite.py
```

Les événements d'audit sont consultables avec :
`/api/audit/ID_CERTIFICAT`.
