from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden, FileResponse
from django.utils import timezone
from .models import Link, SendingUnit
from .forms import VerificationForm

import os
import shutil
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden, FileResponse, HttpResponse
from django.utils import timezone
from .models import Link, SendingUnit
from .forms import VerificationForm

def download_file_view(request, token):
    """
    Vue de téléchargement sécurisée qui gère les fichiers temporaires
    et les copie dans le dossier media/ avant de les servir.
    """
    # 1. Récupérer le lien via le token UUID
    link_obj = get_object_or_404(Link, token=token)
    unit = link_obj.sending_unit

    # 2. Vérifier si le lien est déjà utilisé
    if link_obj.used:
        return render(request, 'core/error_page.html', {
            'message': "Ce lien de téléchargement a déjà été utilisé et n'est plus valide."
        }, status=403)

    # 3. Vérifier que l'unité a un fichier
    if not unit.file:
        return render(request, 'core/error_page.html', {
            'message': "Aucun fichier associé à ce lien."
        }, status=404)

    # 4. Traitement du formulaire de vérification
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            # Vérification des données saisies vs données en BDD
            input_email = form.cleaned_data['email'].strip().lower()
            input_code = form.cleaned_data['access_code']
            
            unit_email = unit.email.strip().lower() if unit.email else ""

            if input_email == unit_email and input_code == link_obj.access_code:
                # A. Marquer le lien comme utilisé (One-Time Link)
                link_obj.used = True
                link_obj.used_at = timezone.now()
                link_obj.save()

                # B. Mettre à jour le statut de réception
                unit.received = True
                unit.received_date = timezone.now()
                unit.save()

                # C. Vérifier et copier le fichier dans media/ si nécessaire
                try:
                    # Chemin d'origine du fichier
                    original_path = unit.file.path
                    
                    # Vérifier si le fichier est dans un dossier temporaire
                    is_temp_file = any(tmp_dir in str(original_path) for tmp_dir in ['/tmp', '/var/tmp', tempfile.gettempdir()])
                    
                    # Définir le chemin sûr dans media/pdfs/
                    safe_dir = settings.MEDIA_ROOT / 'pdfs'
                    safe_dir.mkdir(exist_ok=True)
                    
                    # Nom du fichier sécurisé (utiliser l'ID du lien pour éviter les conflits)
                    safe_filename = f"{link_obj.token}_{os.path.basename(unit.file.name)}"
                    safe_path = safe_dir / safe_filename
                    
                    # Si le fichier est temporaire ou n'existe pas à l'emplacement original
                    if is_temp_file or not os.path.exists(original_path):
                        # Si le fichier existe déjà dans le dossier safe, l'utiliser
                        if safe_path.exists():
                            file_to_serve = safe_path
                        else:
                            # Chercher le fichier par son nom original dans media/pdfs/
                            original_name = os.path.basename(unit.file.name)
                            possible_path = safe_dir / original_name
                            
                            if possible_path.exists():
                                file_to_serve = possible_path
                            else:
                                return render(request, 'core/error_page.html', {
                                    'message': "Le fichier demandé n'est pas disponible."
                                }, status=404)
                    else:
                        # Le fichier original existe et n'est pas temporaire
                        # Le copier dans le dossier safe pour usage futur
                        if not safe_path.exists():
                            shutil.copy2(original_path, safe_path)
                        file_to_serve = safe_path
                    
                    # D. Servir le fichier
                    filename_display = unit.file.name.split('/')[-1]  # Nom convivial
                    response = FileResponse(
                        open(file_to_serve, 'rb'),
                        as_attachment=True,
                        filename=filename_display,
                        content_type='application/pdf'
                    )
                    
                    # Incrémenter le compteur de téléchargements
                    unit.download_count = getattr(unit, 'download_count', 0) + 1
                    unit.save()
                    
                    return response
                    
                except FileNotFoundError:
                    return render(request, 'core/error_page.html', {
                        'message': "Le fichier n'a pas été trouvé sur le serveur."
                    }, status=404)
                except PermissionError:
                    return render(request, 'core/error_page.html', {
                        'message': "Permission refusée pour accéder au fichier."
                    }, status=403)
                except Exception as e:
                    # Log l'erreur pour le debug
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erreur de téléchargement: {str(e)}")
                    
                    return render(request, 'core/error_page.html', {
                        'message': f"Erreur lors du traitement du fichier: {str(e)[:100]}..."
                    }, status=500)
            else:
                form.add_error(None, "Les informations (Email ou Code) ne correspondent pas.")
    else:
        # Pré-remplir le formulaire avec l'email si disponible
        initial_data = {}
        if unit.email:
            initial_data['email'] = unit.email
        
        form = VerificationForm(initial=initial_data)

    # 5. Afficher le formulaire de vérification
    return render(request, 'core/download_page.html', {
        'form': form,
        'unit_name': unit.name,
        'token': token
    })
# views.py - Ajoutez ces vues à votre fichier existant

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
import csv
from django.http import HttpResponse
from .models import SendingGroup, SendingUnit, Link
from .forms import VerificationForm
from .utils import mappe
import os
from pathlib import Path
import tempfile
import zipfile
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import SendingGroup


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('login')

# Fonction pour vérifier si l'utilisateur est administrateur
def is_admin(user):
    return user.is_authenticated and user.is_staff

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

def custom_login(request):
    """Vue de connexion personnalisée"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenue {username} !')
                
                # Redirection vers la page demandée ou dashboard
                next_page = request.GET.get('next', 'dashboard')
                return redirect(next_page)
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'admin/login.html', {'form': form})
# Vue du tableau de bord principal
@login_required
@user_passes_test(is_admin)

@login_required
def admin_dashboard(request):
    groups = SendingGroup.objects.all()

    for group in groups:
        group.sent_count = group.sending_units.exclude(
            sending_date__isnull=True
        ).count()

        group.pending_count = group.sending_units.filter(
            sending_date__isnull=True
        ).count()

    context = {
        'groups': groups
    }
    return render(request, 'admin/dashboard.html', context)

# Vue de détail d'un groupe
@login_required
@user_passes_test(is_admin)
def group_detail(request, group_id):
    group = get_object_or_404(SendingGroup, id=group_id)
    units = group.sending_units.all().order_by('name')
    
    # Calcul des statistiques du groupe
    sent_count = units.exclude(sending_date__isnull=True).count()
    received_count = units.filter(received=True).count()
    
    return render(request, 'admin/group_detail.html', {
        'group': group,
        'units': units,
        'sent_count': sent_count,
        'received_count': received_count,
        'total_count': units.count()
    })

# Vue d'upload et création de groupe
# Dans views.py - MODIFIER create_group
import os
from django.core.files import File

@login_required
@user_passes_test(is_admin)
def create_group(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        pdf_files = request.FILES.getlist('pdf_files')
        group_name = request.POST.get('group_name', f'Groupe_{timezone.now().strftime("%Y%m%d_%H%M%S")}')
        
        # Créer un répertoire temporaire pour les fichiers
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Sauvegarder le CSV
            csv_path = tmp_path / 'data.csv'
            with open(csv_path, 'wb') as f:
                for chunk in csv_file.chunks():
                    f.write(chunk)
            
            # Sauvegarder les PDFs dans le dossier media/pdfs/ directement
            media_pdfs_dir = settings.MEDIA_ROOT / 'pdfs'
            media_pdfs_dir.mkdir(exist_ok=True)
            
            pdf_mapping = {}
            for pdf_file in pdf_files:
                # Sauvegarder dans media/pdfs/
                media_path = media_pdfs_dir / pdf_file.name
                with open(media_path, 'wb') as f:
                    for chunk in pdf_file.chunks():
                        f.write(chunk)
                pdf_mapping[pdf_file.name] = str(media_path)
            
            # Utiliser votre fonction mappe avec les chemins media/
            resultats = mappe(csv_path, media_pdfs_dir)
            
            if resultats:
                # Créer le groupe
                group = SendingGroup.objects.create(label=group_name)
                
                # Créer les unités d'envoi et les liens
                for resultat in resultats:
                    for name, data in resultat.items():
                        # Préparer le chemin relatif pour le FileField
                        file_path = Path(data['file'])
                        relative_path = f"pdfs/{file_path.name}"
                        
                        # Créer l'unité avec le FileField
                        unit = SendingUnit.objects.create(
                            sending_group=group,
                            name=name,
                            email=data['email'],
                        )
                        
                        # Assigner le fichier
                        with open(file_path, 'rb') as f:
                            unit.file.save(file_path.name, File(f), save=True)
                        
                        # Créer le lien
                        Link.objects.create(sending_unit=unit)
                
                return redirect('group_detail', group_id=group.id)
    
    return render(request, 'admin/create_group.html')
# Vue pour envoyer les emails
@login_required
@user_passes_test(is_admin)
def send_emails(request, group_id):
    group = get_object_or_404(SendingGroup, id=group_id)
    units = group.sending_units.filter(sending_date__isnull=True)
    
    if request.method == 'POST':
        email_subject = request.POST.get('email_subject', 'Votre fichier personnel')
        email_body = request.POST.get('email_body', '')
        
        sent_count = 0
        failed_count = 0
        
        for unit in units:
            link = unit.links.first()
            if link:
                try:
                    # Personnaliser le message
                    personalized_body = email_body.replace('{nom}', unit.name)
                    personalized_body = personalized_body.replace('{code}', str(link.access_code))
                    personalized_body = personalized_body.replace('{lien}', request.build_absolute_uri(link.get_download_url()))
                    
                    # Envoyer l'email
                    send_mail(
                        subject=email_subject,
                        message=personalized_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[unit.email],
                        html_message=personalized_body  # Version HTML
                    )
                    
                    # Mettre à jour la date d'envoi
                    unit.sending_date = timezone.now()
                    unit.save()
                    sent_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    print(f"Erreur d'envoi pour {unit.email}: {e}")
        
        return render(request, 'admin/send_result.html', {
            'group': group,
            'sent_count': sent_count,
            'failed_count': failed_count
        })
    
    return render(request, 'admin/send_emails.html', {
        'group': group,
        'units_count': units.count()
    })

# Vue pour renvoyer un lien spécifique
@login_required
@user_passes_test(is_admin)
def resend_link(request, unit_id):
    unit = get_object_or_404(SendingUnit, id=unit_id)
    
    if request.method == 'POST':
        # Invalider l'ancien lien
        old_link = unit.links.first()
        if old_link:
            old_link.used = True
            old_link.save()
        
        # Créer un nouveau lien
        new_link = Link.objects.create(sending_unit=unit)
        
        # Réinitialiser le statut de réception
        unit.received = False
        unit.received_date = None
        unit.sending_date = timezone.now()
        unit.save()
        
        # Envoyer le nouvel email
        try:
            email_body = f"""
            Bonjour {unit.name},
            
            Voici votre nouveau lien de téléchargement.
            Code d'accès: {new_link.access_code}
            Lien: {request.build_absolute_uri(new_link.get_download_url())}
            
            Ce lien est valable une seule fois.
            """
            
            send_mail(
                subject='Nouveau lien de téléchargement',
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[unit.email]
            )
            
            return redirect('group_detail', group_id=unit.sending_group.id)
            
        except Exception as e:
            return render(request, 'admin/error.html', {
                'message': f"Erreur lors de l'envoi: {str(e)}"
            })
    
    return render(request, 'admin/resend_confirm.html', {'unit': unit})

# Export CSV des résultats
@login_required
@user_passes_test(is_admin)
def export_results(request, group_id):
    group = get_object_or_404(SendingGroup, id=group_id)
    units = group.sending_units.all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="resultats_{group.label}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Nom', 'Email', 'Date envoi', 'Reçu', 'Date réception', 'Code d\'accès'])
    
    for unit in units:
        link = unit.links.first()
        writer.writerow([
            unit.name,
            unit.email,
            unit.sending_date.strftime('%Y-%m-%d %H:%M') if unit.sending_date else '',
            'Oui' if unit.received else 'Non',
            unit.received_date.strftime('%Y-%m-%d %H:%M') if unit.received_date else '',
            link.access_code if link else ''
        ])
    
    return response
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Q

def create_user_view(request):
    """
    Vue pour créer un utilisateur.
    - Si aucun utilisateur n'existe, permet de créer le premier admin
    - Si des utilisateurs existent, redirige vers la connexion
    """
    
    # Vérifier s'il existe déjà des utilisateurs
    user_count = User.objects.count()
    has_admin = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).exists()
    
    # Si des utilisateurs existent mais que l'utilisateur n'est pas connecté en admin
    if user_count > 0 and not request.user.is_authenticated:
        messages.warning(request, "Vous devez être connecté en tant qu'administrateur pour créer un utilisateur.")
        return redirect('login')
    
    # Si l'utilisateur est connecté mais pas admin
    if request.user.is_authenticated and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas les droits administrateur.")
        return redirect('dashboard')
    
    # Traitement du formulaire POST
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Pour le premier utilisateur, force admin et superuser
        is_first_user = user_count == 0
        
        if is_first_user:
            is_staff = True
            is_superuser = True
        else:
            is_staff = request.POST.get('is_staff') == 'on'
            is_superuser = request.POST.get('is_superuser') == 'on'
        
        # Validation
        errors = []
        
        if not username:
            errors.append("Le nom d'utilisateur est obligatoire.")
        
        if not password:
            errors.append("Le mot de passe est obligatoire.")
        
        if password != confirm_password:
            errors.append("Les mots de passe ne correspondent pas.")
        
        if len(password) < 8:
            errors.append("Le mot de passe doit contenir au moins 8 caractères.")
        
        if User.objects.filter(username=username).exists():
            errors.append("Ce nom d'utilisateur existe déjà.")
        
        if email and User.objects.filter(email=email).exists():
            errors.append("Cet email est déjà utilisé.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('create_user_view')
        
        # Création de l'utilisateur
        try:
            user = User.objects.create(
                username=username,
                email=email if email else '',
                is_staff=is_staff,
                is_superuser=is_superuser,
                password=make_password(password)
            )
            
            if is_first_user:
                messages.success(request, f"✅ Premier administrateur '{username}' créé avec succès ! Vous pouvez maintenant vous connecter.")
                return redirect('login')
            else:
                messages.success(request, f"✅ Utilisateur '{username}' créé avec succès.")
                
                if request.user.is_authenticated:
                    return redirect('dashboard')
                else:
                    return redirect('login')
                    
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {str(e)}")
            return redirect('create_user_view')
    
    # Contexte pour le template
    context = {
        'is_first_user': user_count == 0,
        'user_count': user_count,
        'has_admin': has_admin,
    }
    
    return render(request, 'admin/create_user.html', context)

# core/utils.py - Ajouter
import os
import shutil
from pathlib import Path
from django.conf import settings

def ensure_file_in_media(file_field, subfolder='pdfs'):
    """
    S'assure qu'un fichier d'un FileField est dans le dossier media/
    Retourne le chemin sûr vers le fichier.
    """
    if not file_field:
        return None
    
    # Chemin original
    original_path = file_field.path if hasattr(file_field, 'path') else None
    
    # Si pas de chemin ou fichier inexistant
    if not original_path or not os.path.exists(original_path):
        # Chercher dans media/ par nom de fichier
        filename = file_field.name.split('/')[-1]
        media_path = settings.MEDIA_ROOT / subfolder / filename
        
        if media_path.exists():
            return media_path
        return None
    
    # Vérifier si déjà dans media/
    media_root_str = str(settings.MEDIA_ROOT)
    if media_root_str in str(original_path):
        return original_path
    
    # Copier dans media/
    safe_dir = settings.MEDIA_ROOT / subfolder
    safe_dir.mkdir(exist_ok=True)
    
    safe_filename = f"{Path(original_path).stem}_{Path(original_path).name}"
    safe_path = safe_dir / safe_filename
    
    if not safe_path.exists():
        shutil.copy2(original_path, safe_path)
    
    return safe_path