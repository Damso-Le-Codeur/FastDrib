from .models import SendingGroup, SendingUnit, Link
import logging
def generate_link(group_name: str,**kwargs):
    group = SendingGroup.objects.create(label=group_name)
    try:
        for key in kwargs:
            unit = SendingUnit.objects.create(sending_group=group, name=key,
            email=kwargs[key]['email'], file=kwargs[key]['file'])
            link = Link.objects.create(sending_unit=unit)
            kwargs[key]['link'] = link.get_download_url()
    except Exception as e:
        logging.error(f"Erreur lors de la création de lien : {e}")
    return kwargs