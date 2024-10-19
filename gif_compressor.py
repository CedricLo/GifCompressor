import os
import shutil
import logging
from pygifsicle import optimize
from alive_progress import alive_bar
from concurrent.futures import ProcessPoolExecutor, as_completed

# Créer un formateur coloré pour les logs
log_format = "%(log_color)s%(asctime)s - %(levelname)s - %(message)s"

# Configurer le logger
logger = logging.getLogger(__name__)

# Fonction pour ajouter une couleur selon la taille du fichier compressé
def format_file_size_with_color(size_in_bytes):
    size_in_mb = size_in_bytes / (1024 * 1024)
    
    if size_in_mb < 6:
        # Vert si inférieur à 6 MB
        color = '\033[92m'  # ANSI code pour vert
    elif 6 <= size_in_mb < 8:
        # Orange (jaune foncé) si entre 6 MB et 8 MB
        color = '\033[93m'  # ANSI code pour jaune/orange
    else:
        # Rouge si 8 MB ou plus
        color = '\033[91m'  # ANSI code pour rouge

    reset_color = '\033[0m'  # Code ANSI pour réinitialiser la couleur
    return f"{color}{size_in_mb:.2f} MB{reset_color}"

def format_size_diff(size_diff_bytes):
    """
    Formate la différence de taille pour l'afficher en KB ou MB selon la valeur.
    """
    if size_diff_bytes >= 1024 * 1024:  # Si la différence est d'au moins 1 MB
        return f"{size_diff_bytes / (1024 * 1024):.2f} MB"
    else:  # Sinon, affiche en KB
        return f"{size_diff_bytes / 1024:.2f} KB"

def is_file_small_enough(file_path):
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        return file_size <= 9 * 1024 * 1024  # Si la taille est en dessous de 9 MB
    else:
        return False

def optimize_file(file, source_file_path, output_file_path):
    """
    Fonction qui optimise un fichier GIF avec différents paramètres si nécessaire,
    puis affiche la taille finale du fichier optimisé.
    """
    source_file_size = os.path.getsize(source_file_path)
    
    # Étapes d'optimisation avec des paramètres différents
    optimizations = [
        {"options": ["-w", "--optimize=3", "--scale=0.9"]},
        {"options": ["-w", "--optimize=3", "--scale=0.8"]},
        {"options": ["-w", "--optimize=3", "--lossy=90", "--scale=0.7"]},
        {"options": ["-w", "--optimize=3", "--lossy=70", "--scale=0.6"]},
        {"options": ["-w", "--optimize=3", "--lossy=50", "--scale=0.5"]}
    ]

    # Appliquer les étapes d'optimisation jusqu'à ce que le fichier soit suffisamment réduit
    for params in optimizations:
        optimize(source_file_path, output_file_path, **params)
        if is_file_small_enough(output_file_path):
            break

    # Comparer la taille finale avec la taille d'origine
    output_file_size = os.path.getsize(output_file_path) if os.path.exists(output_file_path) else source_file_size
    size_diff = source_file_size - output_file_size

    # Si aucune réduction significative, copier le fichier original
    if output_file_size >= source_file_size:
        shutil.copyfile(source_file_path, output_file_path)
    else:
        colored_file_size = format_file_size_with_color(output_file_size)
        logger.info(f"File {file} optimized to {colored_file_size} [-{format_size_diff(size_diff)}]")


def process_file(file, source_file_path, output_file_path):
    """
    Fonction pour traiter un fichier.
    """
    if os.path.isfile(source_file_path):
        if source_file_path.endswith(".gif"):
            optimize_file(file, source_file_path, output_file_path)
        else:
            shutil.copyfile(source_file_path, output_file_path)

def replicate_directory_structure(source_dir, output_dir):
    """
    Réplique la structure du dossier source dans le dossier output et traite les fichiers GIF.
    """
    for root, dirs, files in os.walk(source_dir):
        relative_path = os.path.relpath(root, source_dir)
        output_subdir = os.path.join(output_dir, relative_path)
        os.makedirs(output_subdir, exist_ok=True)

        with alive_bar(len(files), title=f'Traitement de {relative_path}') as bar:
            with ProcessPoolExecutor() as executor:
                # Soumettre les fichiers pour traitement en parallèle
                futures = {
                    executor.submit(process_file, file, os.path.join(root, file), os.path.join(output_subdir, file)): file
                    for file in files if file.endswith('.gif')
                }

                # Gérer les résultats et mettre à jour la barre de progression
                for future in as_completed(futures):
                    file = futures[future]
                    try:
                        future.result()  # Récupérer le résultat ou lever une exception
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement de {file}: {e}")

                    bar()  # Mise à jour de la barre de progression

# Exemple d'utilisation
source_directory = "sources"
output_directory = "outputs"

replicate_directory_structure(source_directory, output_directory)
