# EduCert — préparation de la version pilote

## Périmètre pilote

- Blockchain : Ethereum Sepolia, contrat `EduCert_v2.sol`.
- Frontend : HTML/JavaScript + MetaMask pour les écritures.
- Lecture publique : RPC Sepolia, sans MetaMask.
- Backend institutionnel : PostgreSQL obligatoire.
- QR : génération conservée, déploiement HTTPS à traiter séparément.

## Vérification de l'audit PostgreSQL

Vérification de l'audit :

```text
http://127.0.0.1:8020/api/audit/ID_CERTIFICAT
```

Chaque émission et changement de statut doit produire un événement d'audit avec le
hash de transaction lorsqu'il est disponible.

## PostgreSQL obligatoire

La base PostgreSQL doit être créée avant le démarrage de l'API. Le fichier `.env.example`
documente la forme de `DATABASE_URL`; remplacez localement la valeur d'exemple et ne
publiez jamais le mot de passe.

L'API refuse désormais de démarrer si `DATABASE_URL` n'est pas PostgreSQL. Les tables
`certificates` et `audit_events` sont créées automatiquement au premier démarrage.
Activez les sauvegardes PostgreSQL et testez une restauration avant la production.

Sepolia reste la preuve d'ancrage externe; PostgreSQL conserve l'index institutionnel,
les statuts et l'audit applicatif.

### Couche de persistance actuelle

L'API utilise maintenant SQLAlchemy avec le même schéma pour SQLite et PostgreSQL :

- `DATABASE_URL=postgresql+psycopg://...` est obligatoire ;
- les routes existantes `/api/certificates/...` et `/api/audit/...` restent inchangées ;
- `EDUCERT_CORS_ORIGINS` doit être limité aux domaines HTTPS en production.

Installation des dépendances :

```bash
python -m pip install -r requirements.txt
```

Cette étape prépare le changement de moteur. Une migration versionnée Alembic et un
test de restauration PostgreSQL restent obligatoires avant la mise en production.

## Authentification institutionnelle

Pour le pilote, ne pas gérer les mots de passe dans EduCert. Utiliser un fournisseur
OIDC compatible (université, Keycloak ou fournisseur institutionnel) :

- le fournisseur authentifie l'utilisateur ;
- l'API vérifie le JWT (`issuer`, `audience`, signature, expiration) ;
- le `sub` ou l'adresse e-mail institutionnelle est relié à un rôle local ;
- les droits blockchain restent la règle d'autorisation finale pour émettre/révoquer.

Rôles recommandés : `national_admin`, `university_admin`, `faculty_issuer`,
`faculty_revoker`, `auditor`. Ne jamais considérer le rôle envoyé par le navigateur
comme fiable.

## Checklist avant pilote

- [ ] contrat et réseau Sepolia vérifiés dans `config.js` ;
- [ ] comptes autorisés testés avec un compte non autorisé ;
- [ ] émission et révocation visibles dans `/api/audit/...` ;
- [ ] sauvegarde et restauration SQLite testées ;
- [ ] secrets exclus du frontend et du dépôt ;
- [ ] HTTPS et domaine public validés avant impression des QR ;
- [ ] consentement et minimisation des données personnelles documentés.
