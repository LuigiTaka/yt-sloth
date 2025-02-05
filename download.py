import subprocess
from concurrent.futures import ThreadPoolExecutor
import threading
import sys

# Cria um Lock para sincronizar a impressão
print_lock = threading.Lock()



def download_video_rotine( url, output_dir='./videos/' ) :


    download_video( url, output_dir )

    return

def download_video(url, output_dir='./videos/'):
    command = [
        'yt-dlp',
        '--quiet',
        '-f', '136+140',
        '-o', f'{output_dir}%(title)s.%(ext)s',
        url
    ]
    
    try:
        # Executa o comando yt-dlp
        subprocess.run(command, check=True)
        
        with print_lock:  # Garante que apenas uma thread imprima de cada vez
            print(f'✅ Vídeo baixado com sucesso! Salvo em: {output_dir}')
    
    except subprocess.CalledProcessError as e:
        with print_lock:
            print(f'❌ Ocorreu um erro durante o download: {e}')
    except FileNotFoundError:
        with print_lock:
            print('❌ yt-dlp não foi encontrado! Certifique-se de que está instalado.')

def download_multiple_videos(urls, output_dir='./videos/'):
    # Cria um ThreadPoolExecutor com 4 threads (pode ser ajustado conforme necessário)
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Mapeia as URLs para a função de download
        executor.map(lambda url: download_video_rotine(url, output_dir), urls)

# Lista de URLs para baixar os vídeos


try:

    output_dir = './lazy-downloads/'
    print("Digite as URLS do Youtube a serem baixadas. Pressione Ctrl+C para cancelar.")
    while True:
        line = input()  # Lê uma linha de entrada
        if line:
            threading.Thread( target=download_video, args=(line, output_dir) ).start()
except KeyboardInterrupt:
    print("\nOperação cancelada pelo usuário.")

# Chama a função para baixar os vídeos

