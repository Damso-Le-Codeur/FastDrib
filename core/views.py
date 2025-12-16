from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden, FileResponse
from django.utils import timezone
from .models import Link, SendingUnit
from .forms import VerificationForm

def download_file_view(request, token):
    # 1. Récupérer le lien via le token UUID
    link_obj = get_object_or_404(Link, token=token)
    unit = link_obj.sending_unit

    # 2. Vérifier si le lien est déjà utilisé
    if link_obj.used:
        return render(request, 'error_page.html', {
            'message': "Ce lien de téléchargement a déjà été utilisé et n'est plus valide."
        })

    # 3. Traitement du formulaire
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            # Vérification des données saisies vs données en BDD
            input_email = form.cleaned_data['email']
            input_code = form.cleaned_data['access_code']

            # Comparaison (on utilise strip() et lower() pour être flexible sur la casse/espaces)
            if (input_email.strip().lower() == unit.email.strip().lower() and 
                input_code == link_obj.access_code):
                
                # A. Marquer le lien comme utilisé (One-Time Link)
                link_obj.used = True
                link_obj.save()

                # B. Mettre à jour le statut de réception
                unit.received = True
                unit.received_date = timezone.now()
                unit.save()

                # C. Servir le fichier (Le navigateur lance le téléchargement)
                # as_attachment=True force le téléchargement au lieu de l'affichage
                return FileResponse(unit.file.open(), as_attachment=True, filename=unit.file.name)
            else:
                form.add_error(None, "Les informations (Email ou Code) ne correspondent pas.")
    else:
        form = VerificationForm()

    return render(request, 'download_page.html', {'form': form, 'unit_name': unit.name})
