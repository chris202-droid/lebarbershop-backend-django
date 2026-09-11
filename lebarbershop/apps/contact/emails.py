"""
Notifications email des formulaires publics de la landing page.
Utilise le backend SMTP configuré dans config/settings.py (EMAIL_*).
En développement (EMAIL_BACKEND non configuré), Django utilise la console :
les emails s'affichent dans les logs au lieu d'être réellement envoyés.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

DESTINATAIRE_EQUIPE = getattr(settings, "CONTACT_EMAIL_DESTINATAIRE", "information@kalarai.com")


def _envoyer(sujet, corps, reply_to=None):
    try:
        send_mail(
            subject=sujet,
            message=corps,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[DESTINATAIRE_EQUIPE],
            fail_silently=False,
            **({"reply_to": [reply_to]} if reply_to else {}),
        )
    except Exception:
        # On ne bloque jamais la réponse à l'utilisateur si l'envoi d'email échoue
        # (ex. SMTP non configuré) — la demande reste enregistrée en base.
        logger.exception("Échec de l'envoi de l'email de notification vers %s", DESTINATAIRE_EQUIPE)


def notifier_demande_contact(demande):
    sujet = f"[LeBarberShop] Nouveau message — {demande.get_motif_display()}"
    corps = (
        f"Nom : {demande.nom}\n"
        f"Email : {demande.email}\n"
        f"Motif : {demande.get_motif_display()}\n\n"
        f"Message :\n{demande.message}\n"
    )
    _envoyer(sujet, corps, reply_to=demande.email)


def notifier_demande_partenariat(demande):
    sujet = "[LeBarberShop] Nouvelle demande de partenariat"
    corps = (
        f"Nom : {demande.nom}\n"
        f"Structure : {demande.structure or '—'}\n"
        f"Contact : {demande.contact}\n"
    )
    _envoyer(sujet, corps)
