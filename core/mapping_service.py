from pathlib import Path
import pandas as pd
import logging

def read_csv_file(file_path): #Lit le CSV et retourne une liste
    try:
        df = pd.read_csv(file_path)
        df.drop_duplicates(inplace=True)
        liste = df.to_dict(orient='records')
        return liste
    except Exception as e:
        print(f"Erreur lors de la lecture du CSV: {e}")
        return None

def lire_dossier(dossier_pdf):
    try:
        if not dossier_pdf.is_dir():
            logging.debug(f"{dossier_pdf} n'est pas un dossier valide.")
            return []
        
        pdfs = {}
        for element in dossier_pdf.glob("*.pdf"):
            code = element.stem  # Obtient le nom sans extension
            pdfs[code] = str(element)  # Dictionnaire {code: chemin}
        
        return pdfs
    except Exception as e:
        logging.debug(f"Erreur lors de la lecture du dossier: {e}")
        return {}

def liaison(liste, pdfs):
    resultats = []
    
    for record in liste:
        code = record.get('code', '').strip()
        
        if code in pdfs:  # Recherche directe O(1) au lieu de O(n)
            enregistrement = {
                record.get("nom", ""): {"email": record.get("email", ""), "file": pdfs[code]},
            }
            resultats.append(enregistrement)
    
    return resultats

 
def mappe(file_path, dossier_pdf):

    data_frame = read_csv_file(file_path)
    if data_frame is not None:
        print(f"Données chargées: {len(data_frame)} enregistrements")
        print(data_frame[:5])
        
        pdfs = lire_dossier(dossier_pdf)
        if pdfs:
            resultats = liaison(data_frame, pdfs)
            logging.debug(f"Correspondances trouvées: {len(resultats)}")
            logging.debug(resultats)
            return resultats
        else:
            logging.debug("Aucun PDF trouvé.")
    else:
        logging.debug("Impossible de charger le CSV.")