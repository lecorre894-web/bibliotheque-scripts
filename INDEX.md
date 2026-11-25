# INDEX — bibliothèque de scripts

| Nom | Rôle | Chemin | Sceau sha256 | Commande |
|-----|------|--------|--------------|----------|
| exemple.sh | Modèle d'entrée (à remplacer) | scripts/exemple.sh | à générer via outils/sceau.sh | bash scripts/exemple.sh |
| memoire_chaine.py | Chaine de continuite scellee (genese + ajouter + verifier) | memoire/memoire_chaine.py | genere au scellage | python3 memoire/memoire_chaine.py verifier |
René TV v3.9 | Fluidité 240 Hz (flux optique GPU) + Son (sonie constante, voix centrale, grave virtuel) | tv/v3.9/ | index bb4ca37e38a3ce87 main 1bab40d89d40d0fa | cp tv/v3.9/* ~/rene-tv/ puis packager
René TV v4.4 | v3.9 + gouverneur d'analyse 480-1280 (v4.1/4.2) + Traitement FFmpeg invisible Doux/Fort (v4.3) + IA FSRCNNX x2 libplacebo/Vulkan NVENC (v4.4) ; shader FSRCNNX_x2_8-0-4-1.glsl sha256 e800dbc5…2ae dans %LOCALAPPDATA%\ReneTV ; FFmpeg = winget Gyan.FFmpeg | tv/v4.4/ | index b512c5e16c6cb53f main 58c325863413ce5a | cp tv/v4.4/* ~/rene-tv/ puis packager
René TV v4.5.1 | v4.4 + IA Max FSRCNNX 16 (1080p→4K une passe ; passage 8K abandonné : coupures) ; shaders FSRCNNX_x2_8-0-4-1 (e800dbc5…2ae) + FSRCNNX_x2_16-0-4-1 (d5a24a27…965) dans %LOCALAPPDATA%\ReneTV | tv/v4.5.1/ | index 85afa3e6466991f2 main 35802b33501d0d74 | cp tv/v4.5.1/* ~/rene-tv/ puis packager
René TV v4.5.1 INSTALLEUR | un seul fichier : bash installer_ReneTV.sh dans WSL (deps, FFmpeg winget, shaders FSRCNNX vérifiés, appli + raccourci Bureau) | tv/installeur/ | README.md
René TV v4.7 | v4.4 + IA Max + IA 8K→4K + anti-blocs sombres + bords prudents + étiquette Qualité + Fluidité MAX intégré ; défaut MAX 240 Hz + Fort + IA | tv/v4.7/ + tv/installeur/ (installer_ReneTV.sh v4.7) | index 275b5b88acc4e34d main d6887f834b9dff7b | bash installer_ReneTV.sh dans WSL
René TV v4.9.3 | v4.7 + Retouche photo/LUT/Courbes Photoshop + Finale RTX VSR + télécommande téléphone (HTML5 mosaïque logos + QR code, Termux rtv) | tv/v4.9.3/ + tv/installeur/ | index 0d2daa940e132d0b main 05bbfda8bc626a74 | bash installer_ReneTV.sh dans WSL
