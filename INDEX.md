# INDEX — bibliothèque de scripts

| Nom | Rôle | Chemin | Sceau sha256 | Commande |
|-----|------|--------|--------------|----------|
| exemple.sh | Modèle d'entrée (à remplacer) | scripts/exemple.sh | à générer via outils/sceau.sh | bash scripts/exemple.sh |
| memoire_chaine.py | Chaine de continuite scellee (genese + ajouter + verifier) | memoire/memoire_chaine.py | genere au scellage | python3 memoire/memoire_chaine.py verifier |
René TV v3.9 | Fluidité 240 Hz (flux optique GPU) + Son (sonie constante, voix centrale, grave virtuel) | tv/v3.9/ | index bb4ca37e38a3ce87 main 1bab40d89d40d0fa | cp tv/v3.9/* ~/rene-tv/ puis packager
René TV v4.4 | v3.9 + gouverneur d'analyse 480-1280 (v4.1/4.2) + Traitement FFmpeg invisible Doux/Fort (v4.3) + IA FSRCNNX x2 libplacebo/Vulkan NVENC (v4.4) ; shader FSRCNNX_x2_8-0-4-1.glsl sha256 e800dbc5…2ae dans %LOCALAPPDATA%\ReneTV ; FFmpeg = winget Gyan.FFmpeg | tv/v4.4/ | index b512c5e16c6cb53f main 58c325863413ce5a | cp tv/v4.4/* ~/rene-tv/ puis packager
