# Documentation Technique - FastDistrib

**Version:** 1.0  
**Date:** 2024  
**Auteur:** Équipe de développement FastDistrib

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture et Technologies](#2-architecture-et-technologies)
3. [Modèles de Données](#3-modèles-de-données)
4. [Fonctionnalités Principales](#4-fonctionnalités-principales)
5. [Sécurité et Authentification](#5-sécurité-et-authentification)
6. [Flux de Travail](#6-flux-de-travail)
7. [Configuration et Déploiement](#7-configuration-et-déploiement)

---

## 1. Vue d'ensemble

### 1.1 Présentation

**FastDistrib** est une application web Django conçue pour la distribution sécurisée et automatisée de fichiers PDF personnalisés à des destinataires multiples. L'application permet de gérer des campagnes d'envoi de documents sensibles avec un système de liens de téléchargement à usage unique, protégés par authentification à double facteur (email + code d'accès).

### 1.2 Objectifs

- **Sécurisation** : Distribution de fichiers sensibles avec protection par codes d'accès
- **Automatisation** : Mapping automatique entre fichiers PDF et destinataires via CSV
- **Traçabilité** : Suivi des téléchargements et réceptions en temps réel
- **Simplicité** : Interface d'administration intuitive pour la gestion des campagnes

### 1.3 Cas d'usage

- Distribution de bulletins de notes ou diplômes
- Envoi de documents contractuels personnalisés
- Distribution de rapports individuels
- Partage de documents confidentiels

---

## 2. Architecture et Technologies

### 2.1 Stack Technique

**Backend:**
- **Framework:** Django 6.0
- **Langage:** Python 3.x
- **Base de données:** SQLite (développement) / PostgreSQL (production via DATABASE_URL)
- **Authentification:** Django Auth System avec gestion des permissions

**Frontend:**
- Templates Django avec HTML/CSS/JavaScript
- Interface d'administration personnalisée

**Services externes:**
- **Email:** SMTP (configurable via variables d'environnement)
- **Stockage:** Système de fichiers local (media/pdfs/)
- **Déploiement:** Compatible Render.com avec WhiteNoise pour les fichiers statiques

### 2.2 Structure de l'Application

```
FastDistrib/
├── core/                    # Application principale
│   ├── models.py           # Modèles de données
│   ├── views.py            # Vues et logique métier
│   ├── urls.py             # Routage URL
│   ├── utils.py            # Fonctions utilitaires (mapping CSV/PDF)
│   ├── mapping_service.py  # Service de correspondance
│   └── LinkService.py      # Service de génération de liens
├── FastDistrib/
│   └── settings.py         # Configuration Django
└── media/
    └── pdfs/               # Stockage sécurisé des PDFs
```

### 2.3 Principes d'Architecture

- **Séparation des responsabilités** : Modèles, vues et services distincts
- **Sécurité par défaut** : Authentification requise pour toutes les opérations administratives
- **Gestion des fichiers** : Copie automatique des fichiers temporaires vers media/pdfs/ pour persistance
- **One-Time Links** : Chaque lien ne peut être utilisé qu'une seule fois

---

## 3. Modèles de Données

### 3.1 SendingGroup

Représente un groupe d'envoi (campagne de distribution).

**Champs:**
- `id` : Identifiant unique (auto-généré)
- `label` : Nom du groupe (TextField, max 255 caractères)

**Relations:**
- `sending_units` : Relation One-to-Many vers SendingUnit

**Usage:** Regroupe plusieurs unités d'envoi pour une campagne donnée.

### 3.2 SendingUnit

Représente un destinataire individuel avec son fichier associé.

**Champs:**
- `id` : Identifiant unique
- `sending_group` : ForeignKey vers SendingGroup (CASCADE)
- `name` : Nom du destinataire (TextField, max 255)
- `email` : Adresse email (EmailField, max 255)
- `file` : Fichier PDF associé (FileField, upload_to='sending_files/')
- `received` : Statut de réception (BooleanField, default=False)
- `sending_date` : Date d'envoi de l'email (DateTimeField, nullable)
- `received_date` : Date de téléchargement (DateTimeField, nullable)

**Relations:**
- `links` : Relation One-to-Many vers Link

**Usage:** Stocke les informations d'un destinataire et son fichier PDF personnalisé.

### 3.3 Link

Représente un lien de téléchargement sécurisé à usage unique.

**Champs:**
- `id` : Identifiant unique
- `token` : Token UUID unique pour l'URL (UUIDField, default=uuid.uuid4, unique=True)
- `sending_unit` : ForeignKey vers SendingUnit (CASCADE)
- `access_code` : Code d'accès à 6 chiffres (CharField, max 6, auto-généré)
- `used` : Statut d'utilisation (BooleanField, default=False)

**Méthodes:**
- `save()` : Génère automatiquement un code d'accès à 6 chiffres (100000-999999) si absent
- `get_download_url()` : Retourne l'URL de téléchargement `/download/{token}`
- `get_access_code()` : Retourne le code d'accès
- `is_used()` : Vérifie si le lien a été utilisé

**Usage:** Sécurise l'accès au téléchargement avec un token UUID et un code d'accès.

### 3.4 Schéma Relationnel

```
SendingGroup (1) ──< (N) SendingUnit (1) ──< (N) Link
```

---

## 4. Fonctionnalités Principales

### 4.1 Gestion des Groupes d'Envoi

**Création de groupe (`create_group`):**
- Upload d'un fichier CSV contenant les destinataires (nom, email, code)
- Upload de multiples fichiers PDF
- Mapping automatique CSV ↔ PDFs via la fonction `mappe()` dans `utils.py`
- Détection automatique du format CSV (avec/sans en-tête)
- Normalisation des données (nettoyage emails, codes, noms)
- Création automatique des SendingUnit et Link associés

**Détails du groupe (`group_detail`):**
- Affichage de tous les destinataires du groupe
- Statistiques : nombre envoyé, nombre reçu, total
- Statut individuel de chaque unité (envoyé/reçu)
- Actions : renvoyer un lien, exporter les résultats

### 4.2 Mapping Automatique CSV/PDF

**Fonction `mappe()` (utils.py):**
- Lecture flexible du CSV (détection automatique des colonnes)
- Support de formats variés : avec/sans en-tête, 2 ou 3 colonnes
- Normalisation des codes (001, 1, "001" → format standardisé)
- Correspondance intelligente entre codes CSV et noms de fichiers PDF
- Gestion des formats multiples (001 vs 1, codes textuels vs numériques)

**Algorithme de correspondance:**
1. Extraction des codes depuis le CSV
2. Indexation des fichiers PDF par leur nom (sans extension)
3. Recherche multi-format (exact, sans zéros, avec padding)
4. Génération des correspondances

### 4.3 Génération de Liens Sécurisés

**Création automatique:**
- Token UUID unique pour chaque lien
- Code d'accès à 6 chiffres généré aléatoirement (100000-999999)
- Association avec un SendingUnit
- URL format : `/download/{uuid_token}/`

**Sécurité:**
- Token UUID non prédictible
- Code d'accès indépendant du token
- Lien à usage unique (marqué comme `used` après téléchargement)

### 4.4 Envoi d'Emails Personnalisés

**Fonctionnalité (`send_emails`):**
- Envoi en masse aux destinataires d'un groupe
- Personnalisation du message avec variables :
  - `{nom}` : Nom du destinataire
  - `{code}` : Code d'accès à 6 chiffres
  - `{lien}` : URL complète de téléchargement
- Support HTML et texte brut
- Mise à jour automatique de `sending_date` après envoi
- Gestion des erreurs d'envoi avec compteurs (sent_count, failed_count)

**Configuration email:**
- SMTP configurable via variables d'environnement
- Support TLS/SSL
- Email expéditeur configurable

### 4.5 Téléchargement Sécurisé

**Processus de téléchargement (`download_file_view`):**

1. **Vérification du lien:**
   - Récupération du Link via token UUID
   - Vérification que le lien n'est pas déjà utilisé
   - Vérification de l'existence du fichier

2. **Affichage du formulaire de vérification:**
   - Formulaire demandant email et code d'accès
   - Pré-remplissage de l'email si disponible

3. **Validation des identifiants:**
   - Comparaison email (insensible à la casse)
   - Comparaison code d'accès
   - Affichage d'erreur si non correspondance

4. **Téléchargement:**
   - Marquage du lien comme utilisé (`used = True`)
   - Mise à jour du statut de réception (`received = True`, `received_date`)
   - Gestion des fichiers temporaires (copie vers media/pdfs/ si nécessaire)
   - Service du fichier via FileResponse avec nom d'affichage convivial

**Gestion des fichiers:**
- Détection automatique des fichiers temporaires
- Copie vers `media/pdfs/` pour persistance
- Gestion des erreurs (FileNotFoundError, PermissionError)

### 4.6 Tableau de Bord Administrateur

**Dashboard (`admin_dashboard`):**
- Liste de tous les groupes d'envoi
- Statistiques par groupe :
  - Nombre d'unités envoyées (`sent_count`)
  - Nombre d'unités en attente (`pending_count`)
- Accès rapide aux détails de chaque groupe

**Détails de groupe:**
- Liste complète des destinataires
- Statut individuel (envoyé/reçu)
- Dates d'envoi et de réception
- Actions : renvoyer un lien, exporter les résultats

### 4.7 Export des Résultats

**Fonctionnalité (`export_results`):**
- Export CSV des résultats d'un groupe
- Colonnes : Nom, Email, Date envoi, Reçu, Date réception, Code d'accès
- Format compatible Excel/LibreOffice
- Nom de fichier : `resultats_{group_label}.csv`

### 4.8 Gestion des Utilisateurs

**Création d'utilisateur (`create_user_view`):**
- Création du premier administrateur si aucun utilisateur n'existe
- Création d'utilisateurs supplémentaires (requiert authentification admin)
- Validation des mots de passe (minimum 8 caractères)
- Gestion des permissions (is_staff, is_superuser)

---

## 5. Sécurité et Authentification

### 5.1 Authentification

**Système d'authentification:**
- Utilisation du système d'authentification Django natif
- Décorateurs de sécurité :
  - `@login_required` : Vérifie l'authentification
  - `@user_passes_test(is_admin)` : Vérifie les droits administrateur
- Fonction `is_admin()` : Vérifie `user.is_authenticated` et `user.is_staff`

**Routes protégées:**
- `/dashboard/` : Requiert authentification
- `/admin/*` : Requiert authentification + droits admin
- `/download/<token>/` : Accessible publiquement mais protégé par code d'accès

### 5.2 Sécurité des Liens

**Protection multi-couches:**
1. **Token UUID** : Non prédictible, unique par lien
2. **Code d'accès** : 6 chiffres générés aléatoirement (100000-999999)
3. **Vérification email** : L'email doit correspondre à celui du destinataire
4. **One-Time Link** : Le lien est invalidé après utilisation

**Processus de vérification:**
```
Token UUID → Link → Vérification email + code → Téléchargement → Invalidation
```

### 5.3 Gestion des Fichiers

**Sécurité des fichiers:**
- Stockage dans `media/pdfs/` (hors accès direct web)
- Noms de fichiers sécurisés avec token UUID pour éviter les conflits
- Vérification d'existence avant service
- Gestion des permissions (0o644)

**Protection contre:**
- Accès non autorisé aux fichiers
- Fichiers temporaires supprimés
- Conflits de noms de fichiers

### 5.4 Configuration de Sécurité Production

**Settings.py (production):**
- `SECURE_SSL_REDIRECT = True` : Force HTTPS
- `SESSION_COOKIE_SECURE = True` : Cookies sécurisés
- `CSRF_COOKIE_SECURE = True` : Protection CSRF
- `SECURE_BROWSER_XSS_FILTER = True` : Protection XSS
- `SECURE_CONTENT_TYPE_NOSNIFF = True` : Protection MIME sniffing

---

## 6. Flux de Travail

### 6.1 Création et Envoi d'une Campagne

```
1. Connexion admin
   ↓
2. Création d'un groupe
   - Upload CSV (nom, email, code)
   - Upload PDFs (nommés selon les codes)
   ↓
3. Mapping automatique
   - Correspondance CSV ↔ PDFs
   - Création des SendingUnit
   - Génération des Link (token + code)
   ↓
4. Envoi des emails
   - Personnalisation du message
   - Envoi en masse
   - Mise à jour sending_date
   ↓
5. Suivi depuis le dashboard
   - Consultation des statuts
   - Export des résultats
```

### 6.2 Téléchargement par le Destinataire

```
1. Réception de l'email
   - Contient : nom, code, lien
   ↓
2. Clic sur le lien
   - Redirection vers /download/{token}/
   ↓
3. Affichage du formulaire
   - Saisie email + code
   ↓
4. Vérification
   - Comparaison email (insensible casse)
   - Comparaison code
   ↓
5. Téléchargement
   - Marquage lien comme utilisé
   - Mise à jour received = True
   - Enregistrement received_date
   - Service du fichier PDF
```

### 6.3 Renvoi d'un Lien

```
1. Depuis le dashboard
   - Sélection d'une unité
   - Action "Renvoyer le lien"
   ↓
2. Invalidation de l'ancien lien
   - used = True
   ↓
3. Création d'un nouveau lien
   - Nouveau token UUID
   - Nouveau code d'accès
   ↓
4. Réinitialisation du statut
   - received = False
   - received_date = None
   ↓
5. Envoi du nouvel email
```

---

## 7. Configuration et Déploiement

### 7.1 Variables d'Environnement

**Base de données:**
- `DATABASE_URL` : URL de connexion PostgreSQL (production)

**Sécurité:**
- `SECRET_KEY` : Clé secrète Django
- `DEBUG` : Mode debug (True/False)

**Email:**
- `EMAIL_HOST` : Serveur SMTP (défaut: smtp.gmail.com)
- `EMAIL_PORT` : Port SMTP (défaut: 587)
- `EMAIL_USE_TLS` : Utilisation TLS (défaut: True)
- `EMAIL_HOST_USER` : Utilisateur SMTP
- `EMAIL_HOST_PASSWORD` : Mot de passe SMTP
- `DEFAULT_FROM_EMAIL` : Email expéditeur

**Déploiement:**
- `RENDER_EXTERNAL_HOSTNAME` : Hostname externe (Render.com)

### 7.2 Structure des Répertoires

```
media/
└── pdfs/              # Fichiers PDF stockés de manière sécurisée

staticfiles/           # Fichiers statiques compilés (WhiteNoise)

db.sqlite3            # Base de données SQLite (développement)
```

### 7.3 Déploiement Render.com

**Configuration:**
- Base de données PostgreSQL via DATABASE_URL
- WhiteNoise pour les fichiers statiques
- Support des sous-domaines .onrender.com
- HTTPS forcé en production

**Build:**
- Script `build.sh` pour la compilation
- Migration automatique de la base de données
- Collecte des fichiers statiques

### 7.4 Limitations et Bonnes Pratiques

**Limitations:**
- Taille maximale d'upload : 5MB par fichier (configurable)
- Format CSV : UTF-8 recommandé
- Format PDF : Extension .pdf ou .PDF

**Bonnes pratiques:**
- Utiliser des codes uniques et cohérents dans le CSV
- Nommer les PDFs selon les codes du CSV
- Vérifier les correspondances avant l'envoi
- Sauvegarder régulièrement la base de données

---

## Conclusion

FastDistrib offre une solution complète et sécurisée pour la distribution automatisée de fichiers personnalisés. L'architecture Django, combinée à un système de liens à usage unique et une authentification à double facteur, garantit la sécurité des données sensibles tout en simplifiant le processus de distribution pour les administrateurs.

L'application est conçue pour être évolutive et maintenable, avec une séparation claire des responsabilités et une configuration flexible via variables d'environnement.

---

**Document généré le:** 2024  
**Version de l'application:** 1.0

