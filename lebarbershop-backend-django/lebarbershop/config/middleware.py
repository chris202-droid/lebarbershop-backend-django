class NormaliserSlashFinalMiddleware:
    """
    Ajoute automatiquement un slash final aux requêtes vers /api/ qui n'en
    ont pas, AVANT le routage Django.

    Contexte : certains proxys/CDN (dont Vercel, en configuration par
    défaut) normalisent les URLs en retirant leur slash final. Sans ce
    middleware, une requête POST vers /api/v1/abonnements/essai (sans
    slash) ne correspond à aucune route (seule /abonnements/essai/ existe),
    et le mécanisme APPEND_SLASH de Django répond alors par une redirection
    — redirection qui, pour une requête POST, est souvent rejouée en GET
    par le client, ce qui produit une erreur 405 Method Not Allowed sur un
    endpoint qui n'accepte que POST. En forçant le slash final ICI, avant
    la résolution d'URL, la requête POST originale atteint directement la
    bonne vue sans jamais passer par une redirection.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        chemin = request.path
        if chemin.startswith("/api/") and not chemin.endswith("/"):
            dernier_segment = chemin.rsplit("/", 1)[-1]
            # On évite d'ajouter un slash après un nom de fichier (ex. une
            # future route servant un export .csv) : uniquement si le
            # dernier segment ne contient pas de point.
            if "." not in dernier_segment:
                request.path = chemin + "/"
                request.path_info = request.path_info + "/"
        return self.get_response(request)
