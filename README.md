<p align="center">
<img src="./static/assets/logo.png" alt="Seerr" style="margin: 20px 0;">
</p>

**Uploadarr** est une petite interface web permettant d’uploader facilement des films vers un serveur multimédia, puis de les préparer pour leur import dans Radarr.

L’objectif est de simplifier l’ajout de fichiers vidéo sans avoir à manipuler manuellement les dossiers du serveur. Depuis une interface simple, l’utilisateur peut envoyer un fichier, qui sera ensuite placé dans le bon répertoire afin d’être détecté et importé par Radarr.

## Fonctionnalités

- Upload de fichiers vidéo depuis une interface web
- Déplacement automatique des fichiers vers le dossier configuré
- Compatible avec Radarr
- Configuration simple via variables d’environnement
- Pensé pour une utilisation avec Docker
- Interface légère et facile à déployer

## À quoi ça sert ?

Uploadarr sert de passerelle entre un upload manuel de film et son intégration dans une médiathèque gérée par Radarr.

Au lieu de copier les fichiers à la main sur le serveur, Uploadarr permet de les envoyer directement depuis le navigateur, puis de les rendre disponibles pour l’import dans Radarr.
