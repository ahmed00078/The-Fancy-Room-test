# Projet de Sourcing et Scraping pour Démarchage (The Fancy Room)

Ce projet a pour objectif de collecter et enrichir des données sur des entreprises ciblées dans le secteur de la rénovation et de la construction afin de générer des opportunités de démarchage par email, téléphone, ou LinkedIn. L'ensemble du processus est automatisé via un pipeline de scraping et de traitement des données.

## Architecture du Projet

L'architecture de ce projet se compose de plusieurs composants principaux :

1. **Scraping des données**  
   Utilisation de Python et de bibliothèques telles que `requests`, `beautifulsoup4`, `scrapy`, et `selenium` pour récupérer des informations publiques sur les entreprises depuis plusieurs sources :
   - INPI (Informations sur les sociétés)
   - Pappers.fr (Registre des entreprises)
   - BODACC (Annonces légales de création de sociétés)
   - Dataset des permis de construire/renover (Statistiques du Ministère de la Transition Écologique)
   
2. **Enrichissement des données**  
   Utilisation d'outils externes pour enrichir les informations collectées avec des contacts (emails, téléphones, profils LinkedIn) :
   - Scraping des pages "Contact" des entreprises sur leurs sites officiels
   - Recherche d'emails via des outils gratuits comme Hunter.io
   - Recherche de profils LinkedIn via des requêtes Google avancées

3. **Traitement des données**  
   Les données collectées sont nettoyées, filtrées et structurées dans une base de données (SQLite ou CSV) pour faciliter leur gestion et exploitation.

4. **Automatisation et Planification**  
   Mise en place d’un processus d'automatisation pour exécuter le pipeline régulièrement (via cron jobs ou Azure Functions).

5. **Déploiement**  
   Le projet peut être déployé sur Azure (via Azure Functions ou VM) pour exécuter des tâches de scraping intensives.

## Fonctionnalités

- **Scraping automatique des données** : Collecte des informations sur les entreprises via des API et du scraping web.
- **Enrichissement des données** : Recherche automatisée d'emails et de profils LinkedIn.
- **Traitement et stockage des données** : Nettoyage et structuration des données dans une base de données SQLite.
- **Automatisation** : Planification du scraping et de l'enrichissement des données.

## Installation

### Prérequis

Avant de commencer, assurez-vous d'avoir installé Python 3.x et pip sur votre machine. Vous pouvez installer les dépendances nécessaires en utilisant les commandes suivantes :

```bash
# Créer un environnement virtuel
python -m venv env
source env/bin/activate   # sous Linux/Mac ou env\Scripts\activate sous Windows

# Installer les dépendances
pip install requests beautifulsoup4 scrapy selenium pandas sqlite3