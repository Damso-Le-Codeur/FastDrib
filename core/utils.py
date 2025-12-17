# utils.py
import pandas as pd
import numpy as np
import re
import os
import logging
from pathlib import Path
from django.core.files import File

logger = logging.getLogger(__name__)

# ==================== FONCTIONS DE LECTURE DE DOSSIER ====================

def lire_dossier(dossier_path):
    """Lit un dossier et retourne un dictionnaire {code: chemin}"""
    try:
        dossier_path = Path(dossier_path)
        print(f"=== Lecture du dossier : {dossier_path} ===")
        
        if not dossier_path.exists():
            print(f"ERREUR: Le dossier {dossier_path} n'existe pas")
            return {}
        
        if not dossier_path.is_dir():
            print(f"ERREUR: {dossier_path} n'est pas un dossier")
            return {}
        
        fichiers = {}
        extensions = ['.pdf', '.PDF']  # Prendre en compte les extensions en majuscules/minuscules
        
        # Lister tous les fichiers du dossier
        for extension in extensions:
            for fichier in dossier_path.glob(f"*{extension}"):
                code = fichier.stem  # Nom du fichier sans extension
                code = str(code).strip()
                
                print(f"  Trouvé: {fichier.name} -> code: '{code}'")
                fichiers[code] = str(fichier)
        
        print(f"Total fichiers trouvés: {len(fichiers)}")
        print("Codes disponibles:", list(fichiers.keys()))
        return fichiers
        
    except Exception as e:
        print(f"ERREUR dans lire_dossier: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

# ==================== FONCTIONS DE TRAITEMENT CSV ====================

def read_csv_file(file_path):
    """
    Lit un fichier CSV avec différentes structures et le normalise
    Gère plusieurs formats :
    1. Avec en-tête : nom,email,code
    2. Sans en-tête : 2 colonnes (email, code) ou 3 colonnes
    3. Codes numériques ou textuels
    """
    try:
        print(f"=== Lecture du CSV : {file_path} ===")
        
        # Détection du format du fichier
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            second_line = f.readline() if f.readline() else ""
            f.seek(0)
        
        # Analyse de la première ligne pour déterminer le format
        first_line_parts = first_line.split(',')
        
        # Vérifier si c'est un en-tête
        has_header = any(col in first_line.lower() for col in ['nom', 'name', 'email', 'mail', 'code', 'id'])
        
        # Options de lecture
        if has_header:
            print("Format détecté : Avec en-tête")
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding='utf-8')
            
            # Normalisation des noms de colonnes
            df.columns = df.columns.str.strip().str.lower()
            
            # Déterminer quel champ correspond à quoi
            column_mapping = {}
            
            for col in df.columns:
                col_lower = col.strip().lower()
                if any(keyword in col_lower for keyword in ['nom', 'name', 'prenom', 'first']):
                    column_mapping['nom'] = col
                elif any(keyword in col_lower for keyword in ['email', 'mail', 'courriel']):
                    column_mapping['email'] = col
                elif any(keyword in col_lower for keyword in ['code', 'id', 'identifiant', 'matricule']):
                    column_mapping['code'] = col
                elif 'code' in column_mapping:
                    # Si on a déjà un code, ne rien faire
                    pass
                else:
                    # Par défaut, assigner aux colonnes manquantes
                    if 'nom' not in column_mapping:
                        column_mapping['nom'] = col
                    elif 'email' not in column_mapping:
                        column_mapping['email'] = col
                    elif 'code' not in column_mapping:
                        column_mapping['code'] = col
            
            # Renommer les colonnes
            df = df.rename(columns={v: k for k, v in column_mapping.items() if k in ['nom', 'email', 'code']})
            
        else:
            print("Format détecté : Sans en-tête")
            # Lire sans en-tête
            df = pd.read_csv(file_path, header=None, dtype=str, keep_default_na=False, encoding='utf-8')
            
            # Déterminer le nombre de colonnes
            num_cols = len(df.columns)
            print(f"Nombre de colonnes détectées : {num_cols}")
            
            if num_cols == 3:
                # Format : nom, email, code
                df.columns = ['nom', 'email', 'code']
            elif num_cols == 2:
                # Format : email, code (probablement votre cas)
                df.columns = ['email', 'code']
                # Créer un nom à partir de l'email
                df['nom'] = df['email'].apply(lambda x: x.split('@')[0] if '@' in str(x) else x)
            elif num_cols == 1:
                # Une seule colonne - essayer de parser différemment
                print("Format à une seule colonne détecté - tentative de parsing...")
                df = parse_single_column_csv(file_path)
            else:
                # Prendre les 3 premières colonnes
                df = df.iloc[:, :3]
                df.columns = ['nom', 'email', 'code']
        
        print(f"DataFrame initial - Shape: {df.shape}")
        print(f"Colonnes: {df.columns.tolist()}")
        print(f"Premières lignes:\n{df.head()}")
        
        # Nettoyage et normalisation des données
        df = clean_and_normalize_data(df)
        
        # Conversion finale en liste de dictionnaires
        result = df.to_dict('records')
        
        print(f"=== Résultat final : {len(result)} enregistrements ===")
        for i, item in enumerate(result):
            print(f"{i+1}. {item}")
        
        return result
        
    except Exception as e:
        print(f"ERREUR dans read_csv_file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def parse_single_column_csv(file_path):
    """Parse un CSV avec une seule colonne contenant des données combinées"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        data = []
        for line in lines:
            # Essayer différents séparateurs
            if ';' in line:
                parts = line.split(';')
            elif ',' in line:
                parts = line.split(',')
            elif '\t' in line:
                parts = line.split('\t')
            else:
                parts = [line]
            
            # Nettoyer les parties
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) >= 3:
                data.append(parts[:3])
            elif len(parts) == 2:
                # Ajouter un nom par défaut
                data.append([parts[0].split('@')[0] if '@' in parts[0] else parts[0]] + parts)
            else:
                # Une seule partie - utiliser comme email
                email = parts[0] if parts else ""
                data.append([email.split('@')[0] if '@' in email else email, email, ""])
        
        return pd.DataFrame(data, columns=['nom', 'email', 'code'])
    except Exception as e:
        print(f"Erreur dans parse_single_column_csv: {e}")
        return pd.DataFrame(columns=['nom', 'email', 'code'])

def clean_and_normalize_data(df):
    """Nettoie et normalise les données du DataFrame"""
    
    # S'assurer que toutes les colonnes existent
    for col in ['nom', 'email', 'code']:
        if col not in df.columns:
            df[col] = ''
    
    # Conversion en string et nettoyage
    df = df.fillna('')
    
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    
    # Traitement spécial pour les emails
    df['email'] = df['email'].apply(lambda x: clean_email(x))
    
    # Traitement spécial pour les noms
    df['nom'] = df.apply(lambda row: clean_name(row['nom'], row['email']), axis=1)
    
    # Traitement spécial pour les codes
    df['code'] = df['code'].apply(clean_code)
    
    # Supprimer les lignes où email ou code est vide
    df = df[(df['email'] != '') & (df['code'] != '')]
    
    # Supprimer les doublons basés sur email+code
    df = df.drop_duplicates(subset=['email', 'code'])
    
    # Réinitialiser l'index
    df = df.reset_index(drop=True)
    
    return df

def clean_email(email):
    """Nettoie une adresse email"""
    if not email or pd.isna(email):
        return ''
    
    email = str(email).strip().lower()
    
    # Si l'email contient des espaces, prendre la dernière partie
    if ' ' in email:
        parts = email.split()
        for part in reversed(parts):
            if '@' in part and '.' in part:
                email = part
                break
    
    # Validation basique d'email
    if '@' not in email or '.' not in email:
        print(f"AVERTISSEMENT: Email potentiellement invalide: {email}")
    
    return email

def clean_name(name, email):
    """Nettoie un nom, utilise l'email si le nom est vide"""
    if not name or pd.isna(name) or name.lower() in ['nan', 'null', 'none', '']:
        # Essayer d'extraire un nom de l'email
        if '@' in email:
            username = email.split('@')[0]
            # Capitaliser la première lettre
            return username.capitalize()
        return 'Utilisateur'
    
    name = str(name).strip()
    
    # Si le nom ressemble à un email, extraire le nom d'utilisateur
    if '@' in name and '.' in name:
        username = name.split('@')[0]
        return username.capitalize()
    
    return name

def clean_code(code):
    """Nettoie et formate un code"""
    if not code or pd.isna(code):
        return ''
    
    code = str(code).strip()
    
    # Si le code est un nombre (1, 2, 001, etc.)
    if code.replace('.', '').isdigit():
        # Convertir en entier
        try:
            num = int(float(code))
            # Formater avec 3 chiffres (001, 002, etc.)
            return f"{num:03d}"
        except:
            return code
    
    return code

# ==================== FONCTION PRINCIPALE DE MAPPAGE ====================

def mappe(file_path, dossier_pdf):
    """Fonction principale qui mappe les fichiers aux destinataires"""
    try:
        print("=== DÉBUT mappe ===")
        
        # Lire les données CSV
        data_frame = read_csv_file(file_path)
        
        if not data_frame:
            print("ERREUR: Aucune donnée chargée du CSV")
            return []
        
        print(f"Données chargées: {len(data_frame)} enregistrements")
        
        # Lire les fichiers PDF
        fichiers = lire_dossier(dossier_pdf)
        if not fichiers:
            print("AVERTISSEMENT: Aucun fichier PDF trouvé")
            return []
        
        print(f"Fichiers PDF trouvés: {len(fichiers)}")
        print("Codes PDF disponibles:", list(fichiers.keys())[:10])
        
        # Faire la correspondance
        resultats = []
        correspondances_trouvees = 0
        
        for record in data_frame:
            code = record.get('code', '')
            nom = record.get('nom', '')
            email = record.get('email', '')
            
            if not code or not email:
                print(f"AVERTISSEMENT: Ligne ignorée - code ou email manquant: {record}")
                continue
            
            # Chercher le fichier correspondant
            fichier_trouve = None
            
            # Essayer plusieurs formats de correspondance
            formats_a_essayer = [
                code,                    # Format exact
                code.lstrip('0'),        # Sans les zéros de début
                code.zfill(3),           # Avec 3 chiffres
                str(code).split('.')[0]  # Sans décimale
            ]
            
            # Également essayer avec différentes extensions
            for format_code in formats_a_essayer:
                if format_code in fichiers:
                    fichier_trouve = fichiers[format_code]
                    break
            
            if fichier_trouve:
                correspondances_trouvees += 1
                resultat = {
                    nom: {
                        "email": email,
                        "file": fichier_trouve
                    }
                }
                resultats.append(resultat)
                print(f"✓ Correspondance trouvée: {nom} -> {code} -> {fichier_trouve}")
            else:
                print(f"✗ Aucun fichier trouvé pour le code: '{code}' (nom: {nom})")
                print(f"  Codes disponibles: {list(fichiers.keys())}")
        
        print(f"=== FIN mappe ===")
        print(f"Correspondances trouvées: {correspondances_trouvees}/{len(data_frame)}")
        
        if correspondances_trouvees == 0:
            print("AVERTISSEMENT: Aucune correspondance trouvée. Vérifiez que:")
            print("1. Les codes dans le CSV correspondent aux noms des fichiers PDF")
            print("2. Les fichiers PDF ont la bonne extension (.pdf)")
            print("3. Les codes sont dans le même format (001 vs 1)")
        
        return resultats
        
    except Exception as e:
        print(f"ERREUR dans mappe: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

# ==================== FONCTIONS UTILITAIRES SUPPLEMENTAIRES ====================

def sauvegarder_fichier_upload(fichier_upload, dossier_destination):
    """Sauvegarde un fichier uploadé et retourne son chemin"""
    try:
        if not os.path.exists(dossier_destination):
            os.makedirs(dossier_destination)
        
        chemin = os.path.join(dossier_destination, fichier_upload.name)
        
        with open(chemin, 'wb+') as destination:
            for chunk in fichier_upload.chunks():
                destination.write(chunk)
        
        return chemin
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier: {e}")
        return None

def extraire_zip(zip_path, destination):
    """Extrait un fichier ZIP"""
    try:
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destination)
        return True
    except Exception as e:
        print(f"Erreur lors de l'extraction du ZIP: {e}")
        return False

def valider_fichiers(csv_path, pdfs_path):
    """Valide la cohérence entre CSV et fichiers PDF"""
    try:
        # Lire le CSV
        data = read_csv_file(csv_path)
        if not data:
            return False, "Erreur de lecture du CSV"
        
        # Lire les PDFs
        pdfs = lire_dossier(pdfs_path)
        
        # Vérifier les correspondances
        codes_csv = {item['code'] for item in data}
        codes_pdf = set(pdfs.keys())
        
        correspondances = codes_csv.intersection(codes_pdf)
        manquants = codes_csv - codes_pdf
        
        return True, {
            'total_csv': len(codes_csv),
            'total_pdf': len(codes_pdf),
            'correspondances': len(correspondances),
            'manquants': list(manquants)
        }
        
    except Exception as e:
        return False, str(e)