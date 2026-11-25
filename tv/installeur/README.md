# 📺 René TV — v4.7

**La télé, la vidéo et la radio du monde entier dans une seule appli Windows, gratuite et sans publicité.**
Image restaurée en direct par IA, fluidité 240 Hz, son travaillé pour les petits haut-parleurs.

Conçu par **René Le Corre** (AISA), codé avec Claude (Anthropic) — 2026.

---

## ✨ Ce que fait René TV

**Chaînes et radios**
- Des milliers de chaînes TV et de radios en accès libre (listes publiques iptv-org et radio-browser), classées par pays, avec favoris, historique, zapping au clavier (↑ ↓, numéros).
- Ouverture d'une chaîne dans VLC, enregistrement (REC), image dans l'image, capture, boucle A-B, sous-titres .srt, minuterie de sommeil.

**Image — Fluidité (moteur maison WebGL2)**
- Interpolation d'images par flux optique sur la carte graphique : une chaîne à 25/50 i/s est affichée jusqu'à **240 Hz** sur un écran rapide.
- Désentrelacement, netteté, éclat (contraste + couleurs), grain, luminosité/contraste/saturation.
- Réglage automatique de la résolution d'analyse (480 → 1280 px) selon la puissance disponible.
- **Bords prudents** (anti-déchirures) : sur les contours des objets qui bougent, fondu doux au lieu de pixels déchirés.
- **MAX intégré** : un seul choix règle tout — 240 Hz + IA 8K → 4K + bords prudents.

**Image — Traitement FFmpeg (invisible, l'image ne quitte jamais René TV)**
FFmpeg tourne en arrière-plan sans fenêtre et renvoie la vidéo traitée à René TV par un petit serveur interne (127.0.0.1).

| Choix | Effet |
|---|---|
| Arrêt | flux d'origine |
| Doux | désentrelacement, débruitage léger, suppression des blocs et des bandes |
| Fort | même chose, plus appuyé — idéal pour les vieux films et les flux compressés |
| Fort + IA | Fort + agrandissement IA **FSRCNNX ×2** (720p → 1440p, 1080p → 4K) |
| IA Max | même chose avec le modèle **FSRCNNX 16**, deux fois plus riche |
| IA 8K → 4K | deux passes IA jusqu'en 8K puis suréchantillonnage en 4K — très lourd (RTX 4080 conseillée) |

Les niveaux IA renforcent aussi le déblocage des zones sombres. Calcul sur la carte graphique (Vulkan/libplacebo) et encodage NVENC sur NVIDIA. Si quelque chose ne suit pas, René TV redescend tout seul d'un cran puis revient au flux d'origine, avec un message en bas de l'écran. Les films des années 80 retrouvent une image propre.

**Son (Web Audio)**
Synchro lèvres, voix centrale renforcée, largeur stéréo, égaliseur 10 bandes, sonie constante (plus de pubs qui hurlent), mode nuit, grave virtuel pour petits haut-parleurs d'écran, limiteur.

---

## 🖥️ Ce qu'il faut

- Windows 10 ou 11 (64 bits) avec **WSL** et **Ubuntu** (gratuit, Microsoft Store).
- Une connexion internet.
- Recommandé : carte NVIDIA récente (NVENC + Vulkan) pour Fort + IA et IA Max. Sans NVIDIA, le traitement passe par le processeur (plus lent) et l'IA peut se désactiver d'elle-même.
- Pour la fluidité 240 Hz : un écran 144/240 Hz réglé à sa fréquence maximale dans Windows.

---

## 🚀 Installation (un seul fichier)

1. Copie **`installer_ReneTV.sh`** dans ton dossier Ubuntu (ex. `\\wsl$\Ubuntu\home\<toi>`).
2. Ouvre Ubuntu et tape :
   ```bash
   bash installer_ReneTV.sh
   ```
3. Le mot de passe Ubuntu peut être demandé (installation des paquets). Laisse faire : 2 à 5 minutes.
4. Double-clique **« Rene TV »** sur le Bureau.

L'installeur fait tout seul, dans l'ordre :

1. python3, curl, tar dans Ubuntu ;
2. Node.js 20 si absent ou trop ancien (NodeSource) ;
3. **FFmpeg** pour Windows (`winget install Gyan.FFmpeg`, build complète gratuite avec libplacebo et Vulkan) ;
4. les modèles IA **FSRCNNX** ×2 (8 et 16), téléchargés depuis leur dépôt officiel et vérifiés par empreinte SHA-256, rangés dans `%LOCALAPPDATA%\ReneTV` ;
5. les sources de René TV (contenues dans l'installeur, vérifiées par empreintes) dans `~/rene-tv` — une ancienne installation est mise de côté, jamais effacée ;
6. la fabrication de l'appli Windows dans `%USERPROFILE%\Applications-Rene\Rene-TV-win32-x64` et le raccourci du Bureau.

Relancer l'installeur répare ou met à jour sans rien perdre.

---

## 🎛️ Premiers réglages conseillés

Bouton **Son & image** :

- Au premier lancement : Fluidité MAX 240 Hz + Fort + IA, déjà réglés ;
- carte puissante : Fluidité **MAX intégré** ;
- **Haut-parleurs** : Écran (petits HP) si tu écoutes sur l'écran ;
- **Sonie constante** : cochée.

Coche **Diagnostic fluidité** pour voir les images par seconde réellement affichées.

---

## 🛠️ Dépannage

| Symptôme | Remède |
|---|---|
| « FFmpeg indisponible — flux original » | Rouvre Ubuntu et relance l'installeur, ou dans Windows : `winget install -e --id Gyan.FFmpeg` |
| « Niveau IA trop lourd — redescendu en … » | Normal : la carte ne suit pas, René TV a choisi le cran en dessous |
| Déchirures autour des objets qui bougent | Coche « Fluidité : bords prudents » |
| Coupures image/son | Redescends d'un cran (IA Max → Fort + IA → Fort) |
| 2 à 5 s d'attente au zapping | Normal avec FFmpeg activé (préparation du flux) |
| Une chaîne ne marche pas | Les flux publics changent souvent : zappe ou « Ouvrir dans VLC » |

---

## 📜 Historique

- **v3.3 → v3.9** : qualité HD, Fluidité 240 Hz (flux optique GPU, bidirectionnel avec gestion des occlusions), son complet.
- **v4.1 / v4.2** : réglage automatique de l'analyse jusqu'à 1280 px.
- **v4.3** : Traitement FFmpeg invisible (Doux / Fort), NVENC, repli automatique.
- **v4.4** : IA FSRCNNX ×2 (libplacebo / Vulkan).
- **v4.5.1** : IA Max FSRCNNX 16.
- **v4.6** : version complète — IA 8K → 4K, anti-blocs des zones sombres, bords prudents, étiquette Qualité flux, réglages par défaut MAX 240 Hz + Fort + IA.
- **v4.7** : Fluidité « MAX intégré » (240 Hz + IA 8K → 4K + bords prudents en un clic).

---

## ⚖️ Licences et crédits

René TV n'embarque que son propre code et **hls.js** (Apache-2.0). Ces logiciels sont téléchargés depuis leur source officielle :

- **FFmpeg** (GPL, build gyan.dev) ;
- **FSRCNNX** (GPL-3.0, igv / FSRCNN-TensorFlow) ;
- **Electron** (MIT) ;
- **Node.js**.

Les chaînes et radios sont des flux publics gratuits listés par des projets communautaires. René TV ne fournit aucun contenu payant ni piraté.

*« Explorer largement, affirmer étroitement. »* — René
