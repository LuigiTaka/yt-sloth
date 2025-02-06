import subprocess
from concurrent.futures import ThreadPoolExecutor
import threading
import sys
import re
import pprint
# Cria um Lock para sincronizar a impressão
import json
print_lock = threading.Lock()



def normalize_storage_size(size):
    try:
        size = size.strip()
      # Define as unidades e seus fatores de conversão
        units = {
            'KiB': 2**10, 'MiB': 2**20, 'GiB': 2**30, 'TiB': 2**40, 'PiB': 2**50 , # Base 2
            'KB': 10**3, 'MB': 10**6, 'GB': 10**9, 'TB': 10**12, 'PB': 10**15,  # Base 10
            'B': 1, 'K': 10**3,
        }

        for unit, factor in units.items():
            if size.upper().endswith(unit.upper()) and size.upper()[-len(unit):] == unit.upper():
                return float(size[:-len(unit)]) * factor


        return float(size)
    except (ValueError, AttributeError):
        raise ValueError(f"Formato inválido: {size}")
valid_resolutions= ["1280x720", "1920x1080"]
valid_resolutions= ["1280x720", "1920x1080","720x720" ]
valid_resolutions = []



valid_resolutions_simple = ["1080p","720p","1280p","1920p","480p"]
max_file_size = normalize_storage_size("20MB")  # Tamanho máximo em MiB


print( f"max_file_size: {max_file_size}" )
print( f"valid_resolutions: {valid_resolutions}" )
print( f"valid_resolutions_simple: {valid_resolutions_simple}" )


class LogException(BaseException):
    pass

class InvalidVideo( LogException ):
    pass



def is_valid_youtube_url(url):
    # Regex para validar URLs do YouTube no formato https://www.youtube.com/watch?v=ID_DO_VIDEO
    regex = re.compile(
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}(?:&.*)?$'
    )
    return re.match(regex, url) is not None

def download_video_rotine( url, output_dir='./videos/' ) :

    try:
        audio_id, video_id =    get_best_video_audio_format_id( url )
        download_video( url, output_dir, audio_id=audio_id, video_id=video_id )
    except InvalidVideo as e:
            print(f'❌ Vídeo inválido para download: {e}')


            print("Ocorreu um erro:")
            print(f"Mensagem da exceção: {str(e)}")
            print("Detalhes da exceção:")
    return



def raiseInvalidVideo( message, formats ):

    details = "\n".join(
        f"- {video} " 
        for video in formats 
    )
    raise InvalidVideo(
        message,
        f"Vídeos encontrados:{details}"
    )
    pass


def get_best_video_audio_format_id(url):
    
    command = [
        'yt-dlp',
        '--list-formats', url,
    ]


    try:
        # Executa o comando yt-dlp
        result = subprocess.run(command, check=True, capture_output=True, text=True)

        with print_lock:
            # Print the standard output (stdout)
            # print("Standard Output:")
            # print(result.stdout)

            formats = parse_formats( result.stdout )

        

            if not formats:
                raiseInvalidVideo("Nenhum vídeo encontrado", formats)

            valid_video_formats = formats


            if valid_resolutions:
                valid_video_formats = filter_valid_resolutions(formats, valid_resolutions)

                if not  valid_video_formats:
                    raiseInvalidVideo( "Nenhum vídeo nos formatos válidos." ,formats)




            # Filtra por tamanho de arquivo
            valid_formats_by_size = valid_video_formats
            if max_file_size:
                valid_formats_by_size = filter_by_file_size(valid_video_formats, max_file_size)
                if not valid_formats_by_size:
                    # Coleta as resoluções e tamanhos dos vídeos filtrados
                    raiseInvalidVideo(  f"Tamanho do vídeo ultrapassa o limite de {max_file_size} MiB.\n", valid_video_formats)

            video_formats = get_video_formats(valid_formats_by_size)
            audio_formats = get_audio_formats( valid_formats_by_size )
            best_video = get_best_video_format(video_formats)
            best_audio = get_best_audio_format(audio_formats)



            print(  'video')  
            print( json.dumps(  best_video, indent=4 ) )

            print(  'audio')  
            print( json.dumps(  best_audio, indent=4) )
            return best_audio['id'], best_video['id']

    
    except subprocess.CalledProcessError as e:
        with print_lock:
            print(f'❌ Ocorreu um erro durante a verificação de arquivos: {e}')
            print("Standard Error:")
            print(e.stderr)  # Print the standard error output
    except FileNotFoundError:
        with print_lock:
            print('❌ yt-dlp não foi encontrado! Certifique-se de que está instalado.')

    pass


def filter_valid_qualities(formats, valid_qualities):
    """
    Filtra os formatos de vídeo com base nas qualidades (resoluções válidas).
    Retorna uma lista de formatos que correspondem às qualidades permitidas.
    """

    valid_formats = []
    for fmt in formats:
        # Verifica se a resolução do formato está nas qualidades válidas
        if not fmt['more']:
            continue
    resolution = fmt['more'].split('p')[0]
    if resolution in valid_qualities:
        valid_formats.append(fmt)
    return valid_formats


def filter_valid_resolutions(formats, valid_resolutions):
    """
    Filtra os formatos de vídeo com base em uma lista de resoluções válidas.
    Retorna uma lista de formatos que correspondem às resoluções permitidas.
    """
    valid_formats = []
    for fmt in formats:
        if fmt['resolution'] in valid_resolutions:
            valid_formats.append(fmt)
    return valid_formats


def filter_by_file_size(formats, max_file_size):
    """
    Filtra os formatos com base em um limite máximo de tamanho de arquivo.
    Retorna uma lista de formatos cujo tamanho do arquivo é menor ou igual ao limite.
    """
    valid_formats = []
    for fmt in formats:
        # Remove o '~' e converte o tamanho do arquivo para um valor numérico (em MiB)
        filesize = fmt['filesize'].replace('~', '')
        filesize = normalize_storage_size( fmt['filesize'] )

        if filesize and float(filesize) <= max_file_size:
            valid_formats.append(fmt)
    return valid_formats


def get_video_formats(formats):
    """
    Retorna uma lista de formatos que contêm vídeo.
    """
    video_formats = []
    for fmt in formats:
        if fmt['vcodec'] and fmt['vcodec'] != 'none':
            video_formats.append(fmt)
    return video_formats


def get_audio_formats(formats):
    """
    Retorna uma lista de formatos que contêm áudio.
    """
    audio_formats = []
    for fmt in formats:
        if fmt['acodec'] and fmt['acodec'] != 'none' :
            audio_formats.append(fmt)
    return audio_formats



def get_best_video_format(video_formats):
    """
    Retorna o melhor formato de vídeo disponível (maior resolução).
    """
    best_video = None
    max_resolution = 0
    
    for fmt in video_formats:
        resolution = fmt['resolution']
        if resolution == 'audio only':
            continue  # Ignorar formatos de áudio
        
        # Converte a resolução para pixels (largura x altura)
        width, height = map(int, resolution.split('x'))
        total_pixels = width * height
        
        if total_pixels > max_resolution:
            max_resolution = total_pixels
            best_video = fmt
    
    return best_video


def convert_bitrate(bitrate):
    if not bitrate:
        return None

    # Remover espaços e verificar se existe algum sufixo (k ou M)
    bitrate = bitrate.strip().lower()

    if bitrate.endswith('k'):
        # Kilobits
        return float(bitrate[:-1])  # Retorna em Kbps
    elif bitrate.endswith('m'):
        # Megabits
        return float(bitrate[:-1]) * 1000  # Converte para Kbps
    elif bitrate.isdigit():
        # Caso não tenha sufixo, assumir que é em Kbps
        return float(bitrate)
    return None

def get_best_audio_format(audio_formats):
    """
    Retorna o melhor formato de áudio disponível (maior taxa de bits).
    """
    best_audio = None
    max_bitrate = 0
    
    for fmt in audio_formats:
        bitrate = convert_bitrate(fmt['tbr'])  # Remove 'k' e converte para int
        if bitrate > max_bitrate:
            max_bitrate = bitrate
            best_audio = fmt
    
    return best_audio

# Exemplo de uma linha de entrada

# Regex para capturar os campos
pattern = re.compile(
    r'(?P<ID>\d+)\s+(?P<EXT>\w+)\s+(?P<RESOLUTION>[\w\.\-x]+)\s+(?P<CH>\d*)\s*\|\s*(?P<FILESIZE>[\w\.\-]+)\s*(?P<TBR>\d*[kM]*\s*)\s*(?P<PROTO>\w*)\s*\|\s*(?P<VCODEC>[\w\.]+)\s*(?P<VBR>\d*[kM]*\s*)\s*(?P<ACODEC>[\w\.]+)\s*(?P<ABR>\d*[kM]*\s*)\s*(?P<ASR>\d*[kM]*\s*)\s*(?P<INFO>[\w\s,]*)'
)

# Função para parsear a linha e retornar um dicionário
def parse_line(line):
    match = pattern.match(line.strip())
    if match:
        return {key.lower(): value for key, value in match.groupdict().items()}
    return {}


def parse_formats(output):

    """
    Parse the output of `yt-dlp --list-formats` to extract available formats.
    Returns a list of dictionaries containing format details.
    """
    formats = []
    lines = output.splitlines()

    # Find the line that starts the table of formats
    start_index = next((i for i, line in enumerate(lines) if line.startswith('ID')), -1)
    if start_index == -1:
        return formats  # No formats found

    # Parse the table rows
    for line in lines[start_index + 2:]:


        parsed_line = parse_line( line )

        if parsed_line:
            formats.append( parsed_line )

        continue
        if not line.strip():
            continue  # Skip empty lines
        parts = line.split()

        # print( line )
        if len(parts) < 9:
            continue  # Skip invalid lines


        format_info = {
            'id': parts[0],
            'extension': parts[1],
            'resolution': parts[2],
            'fps': parts[3],
            'filesize': parts[6],
            'tbr': parts[7],
            'protocol': parts[8],
            'vcodec': parts[9] if len(parts) > 9 else None,
            'acodec': parts[10] if len(parts) > 10 else None,
            'more': parts[13] if(len)(parts) > 13 else None, 
        }

        

        formats.append(format_info)

    return formats

def download_video(url, output_dir='./videos/', audio_id = None, video_id=None):

    
    formatOption = 'best'
    if audio_id:
        formatOption = f"{audio_id}"

    if video_id:
        if audio_id:
            formatOption += "+"
        formatOption += f"{video_id}"

    command = [
        'yt-dlp',
        '--quiet',
        '-f', formatOption,
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
            if not is_valid_youtube_url( line ):
                print("URL inválida.")
                continue
            threading.Thread( target=download_video_rotine, args=(line, output_dir) ).start()
except KeyboardInterrupt:
    print("\nOperação cancelada pelo usuário.")

# Chama a função para baixar os vídeos

