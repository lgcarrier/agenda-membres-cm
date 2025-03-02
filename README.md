# Agenda des membres du Conseil des ministres

Ce projet permet de télécharger et de suivre automatiquement les agendas publics des membres du Conseil des ministres du Québec à partir du site web officiel du gouvernement du Québec.

![François Legault, Premier ministre du Québec](/docs/francois-legault-quebec-premier.jpg)

## Structure du projet

Le projet est organisé comme suit :

- `main.py` : Script d'extraction automatique des agendas depuis quebec.ca
- `requirements.txt` : Liste des dépendances Python requises
- `minister_agendas/` : Répertoire contenant les agendas des ministres
  - `active/` : Agendas des ministres actuellement en fonction
  - `inactive/` : Agendas des anciens ministres
- `minister_agendas.log` : Journal des opérations d'extraction

## Prérequis

Les bibliothèques Python suivantes sont requises :
- requests : Pour les requêtes HTTP
- beautifulsoup4 : Pour l'analyse du HTML
- fake-useragent : Pour la rotation des User-Agents

## Installation

1. Clonez le dépôt :
```bash
git clone [URL_du_depot]
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

Pour télécharger les agendas des ministres :
```bash
python main.py
```

Le script va :
1. Récupérer la liste des ministres actifs et inactifs
2. Télécharger leurs agendas au format CSV
3. Classer les fichiers dans les dossiers appropriés (active/inactive)
4. Journaliser les opérations dans minister_agendas.log

## Structure des données

Les agendas sont stockés au format CSV dans les dossiers `active` et `inactive`. Chaque fichier correspond à un ministre et contient leurs activités publiques. Les données sont extraites directement du site officiel du gouvernement du Québec.

## Licence

© 2025 - Tous droits réservés

## Disclaimer

Ce projet n'est pas affilié au gouvernement du Québec. Les données sont extraites de sources publiques à des fins d'information seulement. L'exactitude et l'actualité des données ne sont pas garanties. Les utilisateurs sont invités à consulter le site officiel du gouvernement du Québec pour les informations les plus à jour.

Les agendas collectés sont des données publiques disponibles sur quebec.ca. Ce projet facilite uniquement leur accès et leur organisation.

Ceci ne constitue pas un avis juridique. Pour toute question légale, veuillez consulter un professionnel du droit qualifié.

## Contribution

Pour contribuer au projet :

1. Créez une branche (`git checkout -b feature/amelioration`)
2. Committez vos changements (`git commit -am 'Ajout d'une nouvelle fonctionnalité'`)
3. Poussez vers la branche (`git push origin feature/amelioration`)
4. Créez une Pull Request