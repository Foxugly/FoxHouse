"""Schéma de la vue d'une partie, commun à tous les jeux. N'importe pas Django."""

from tapis import cartes as c

SCHEMA = 1
TYPES_ZONES = ("main", "pile", "combinaisons", "pli", "annonces", "mises", "communes")
CLES = ("schema", "jeu", "version", "terminee", "sieges", "zones", "menu", "actions", "resultat")


class VueInvalide(ValueError):
    pass


def _exiger(condition, message):
    if not condition:
        raise VueInvalide(message)


def _est_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _valider_carte(carte, contexte):
    _exiger(isinstance(carte, dict), f"{contexte} : carte mal formée")
    if carte.get("cachee") is True:
        _exiger(set(carte) == {"cachee"}, f"{contexte} : une carte cachée ne porte rien d'autre")
        return
    cid = carte.get("id")
    _exiger(c.est_carte(cid), f"{contexte} : carte inconnue {cid!r}")
    if carte.get("joker") is True:
        _exiger(c.est_joker(cid), f"{contexte} : joker incohérent {cid!r}")
        _exiger(
            set(carte) <= {"id", "joker", "represente"}, f"{contexte} : clés de joker inattendues"
        )
        rep = carte.get("represente")
        _exiger(
            rep is None or isinstance(rep, str), f"{contexte} : « represente » doit être une chaîne"
        )
    else:
        _exiger(not c.est_joker(cid), f"{contexte} : joker sans « joker »")
        _exiger(
            set(carte) == {"id", "valeur", "enseigne"}, f"{contexte} : clés de carte inattendues"
        )
        _exiger(
            carte["valeur"] == c.valeur(cid) and carte["enseigne"] == c.enseigne(cid),
            f"{contexte} : carte incohérente {cid!r}",
        )


def _valider_sieges(sieges):
    _exiger(isinstance(sieges, list) and sieges, "sièges manquants")
    ids = set()
    for s in sieges:
        _exiger(isinstance(s, dict) and _est_int(s.get("id")), "siège mal formé")
        _exiger(isinstance(s.get("nom"), str) and isinstance(s.get("actif"), bool), "siège mal formé")
        _exiger(s["id"] not in ids, "siège en double")
        ids.add(s["id"])
        compteurs = s.get("compteurs")
        _exiger(isinstance(compteurs, list), "compteurs mal formés")
        for k in compteurs:
            _exiger(
                isinstance(k, dict)
                and isinstance(k.get("libelle"), str)
                and (isinstance(k.get("valeur"), str) or _est_int(k.get("valeur"))),
                "compteur mal formé",
            )
    return ids


def _valider_zones(zones, ids_sieges):
    _exiger(isinstance(zones, list), "zones mal formées")
    ids_zones = set()
    for z in zones:
        _exiger(isinstance(z, dict), "zone mal formée")
        zid = z.get("id")
        _exiger(isinstance(zid, str) and zid, "zone sans id")
        _exiger(zid not in ids_zones, f"zone en double : {zid}")
        ids_zones.add(zid)
        _exiger(z.get("type") in TYPES_ZONES, f"zone {zid} : type inconnu")
        _exiger(z.get("siege") is None or z["siege"] in ids_sieges, f"zone {zid} : siège inconnu")
        _exiger(isinstance(z.get("libelle"), str), f"zone {zid} : libellé manquant")
        _exiger(z.get("nombre") is None or _est_int(z["nombre"]), f"zone {zid} : nombre invalide")
        _exiger(isinstance(z.get("cartes"), list), f"zone {zid} : cartes mal formées")
        for carte in z["cartes"]:
            _valider_carte(carte, f"zone {zid}")
        _exiger(isinstance(z.get("groupes"), list), f"zone {zid} : groupes mal formés")
        ids_groupes = set()
        for g in z["groupes"]:
            _exiger(isinstance(g, dict), f"zone {zid} : groupe mal formé")
            gid = g.get("id")
            _exiger(isinstance(gid, str) and gid, f"zone {zid} : groupe sans id")
            _exiger(gid not in ids_groupes, f"zone {zid} : groupe en double : {gid}")
            ids_groupes.add(gid)
            _exiger(
                isinstance(g.get("provisoire"), bool) and isinstance(g.get("ciblable"), bool),
                f"groupe {gid} : indicateurs invalides",
            )
            _exiger(isinstance(g.get("cartes"), list), f"groupe {gid} : cartes mal formées")
            for carte in g["cartes"]:
                _valider_carte(carte, f"groupe {gid}")


def _valider_resultat(r):
    _exiger(isinstance(r, dict), "résultat mal formé")
    _exiger(isinstance(r.get("titre"), str), "résultat sans titre")
    cols, lignes = r.get("colonnes"), r.get("lignes")
    _exiger(isinstance(cols, list) and all(isinstance(x, str) for x in cols), "colonnes invalides")
    _exiger(isinstance(lignes, list), "lignes invalides")
    for ligne in lignes:
        _exiger(
            isinstance(ligne, list)
            and len(ligne) == len(cols)
            and all(isinstance(x, str) or _est_int(x) for x in ligne),
            "ligne de résultat invalide",
        )


def valider_vue(vue: dict) -> None:
    """Lève VueInvalide si la vue ne respecte pas le schéma."""
    _exiger(isinstance(vue, dict), "la vue doit être un objet")
    for cle in CLES:
        _exiger(cle in vue, f"clé manquante : {cle}")
    _exiger(vue["schema"] == SCHEMA, "schéma inconnu")
    _exiger(isinstance(vue["jeu"], str) and vue["jeu"], "jeu manquant")
    _exiger(_est_int(vue["version"]), "version invalide")
    _exiger(isinstance(vue["terminee"], bool), "« terminee » doit être un booléen")

    _valider_zones(vue["zones"], _valider_sieges(vue["sieges"]))

    _exiger(isinstance(vue["menu"], list), "menu mal formé")
    for m in vue["menu"]:
        _exiger(
            isinstance(m, dict)
            and isinstance(m.get("libelle"), str)
            and (m.get("valeur") is None or isinstance(m["valeur"], str) or _est_int(m["valeur"])),
            "entrée de menu mal formée",
        )

    _exiger(isinstance(vue["actions"], list), "actions mal formées")
    for a in vue["actions"]:
        _exiger(
            isinstance(a, dict) and isinstance(a.get("id"), str)
            and isinstance(a.get("libelle"), str),
            "action mal formée",
        )
        _exiger(
            _est_int(a.get("cartes_min")) and _est_int(a.get("cartes_max")),
            "bornes d'action invalides",
        )
        _exiger(0 <= a["cartes_min"] <= a["cartes_max"], f"action {a['id']} : bornes incohérentes")
        _exiger(a.get("cible") in (None, "groupe"), f"action {a['id']} : cible inconnue")

    if vue["resultat"] is not None:
        _valider_resultat(vue["resultat"])
