from src.assistant.llm import _commentaire_valide


def test_commentaire_correct():
    texte = """
    Diagnostic :
    Les montants non renseignés limitent l'analyse commerciale.

    Limites :
    Les causes des anomalies restent inconnues.

    Recommandations :
    Vérifier les montants et examiner les retards.
    """
    assert _commentaire_valide(texte) is True


def test_sections_manquantes():
    texte = """
    Diagnostic :
    Les montants non renseignés limitent l'analyse commerciale.

    Limites :
    Les causes restent inconnues.
    """
    assert _commentaire_valide(texte) is False


def test_chiffres_inventes():
    texte = """
    Diagnostic :
    Les ventes ont augmenté de 35 pour cent.

    Limites :
    Les causes restent inconnues.

    Recommandations :
    Examiner les anomalies.
    """
    assert _commentaire_valide(texte) is False


def test_commandes_manquantes():
    texte = """
    Diagnostic :
    Les commandes manquantes perturbent les résultats.

    Limites :
    Les causes restent inconnues.

    Recommandations :
    Examiner les commandes.
    """
    assert _commentaire_valide(texte) is False


def test_perte_revenus_non_demontree():
    texte = """
    Diagnostic :
    Les montants absents provoquent une perte de revenus.

    Limites :
    Les causes restent inconnues.

    Recommandations :
    Examiner les données commerciales.
    """
    assert _commentaire_valide(texte) is False
