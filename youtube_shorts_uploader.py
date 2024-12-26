import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import json
import random
import time
from datetime import datetime

class YouTubeShortsUploader:
    def __init__(self, client_secrets_file, channel_name="default"):
        self.client_secrets_file = client_secrets_file
        self.channel_name = channel_name
        self.api_name = "youtube"
        self.api_version = "v3"
        self.scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        self.credentials = None
        self.youtube = None
        self.token_file = f'token_{channel_name}.pickle'
    
    def force_new_authentication(self):
        """Força uma nova autenticação removendo o token existente"""
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
            print(f"Token removido para o canal {self.channel_name}")
        self.credentials = None
        self.youtube = None
    
    def get_channel_info(self):
        """Obtém informações do canal atual"""
        try:
            response = self.youtube.channels().list(
                part="snippet,statistics",
                mine=True
            ).execute()
            
            if response['items']:
                channel = response['items'][0]
                return {
                    'title': channel['snippet']['title'],
                    'id': channel['id'],
                    'videos': channel['statistics']['videoCount']
                }
        except Exception as e:
            print(f"Erro ao obter informações do canal: {str(e)}")
        return None

    def authenticate(self):
        """Autenticação com o YouTube"""
        # Verifica se já temos credenciais salvas
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                self.credentials = pickle.load(token)
        
        # Se não há credenciais válidas, faz login
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, 
                    self.scopes,
                    redirect_uri='http://localhost:8080'
                )
                self.credentials = flow.run_local_server(
                    port=8080,
                    prompt='consent',
                    access_type='offline'
                )
            
            # Salva as credenciais para o próximo uso
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.credentials, token)
        
        self.youtube = build(
            self.api_name, 
            self.api_version, 
            credentials=self.credentials,
            cache_discovery=False
        )
        
        # Mostra informações do canal
        channel_info = self.get_channel_info()
        if channel_info:
            print(f"\nConectado ao canal: {channel_info['title']}")
            print(f"ID do canal: {channel_info['id']}")
            print(f"Total de vídeos: {channel_info['videos']}")

    def generate_description(self, title):
        """Gera uma descrição para o vídeo"""
        hashtags = [
            "#TecnologiaParaTodos",
            "#GadgetsDoDia",
            "#ProdutosInovadores",
            "#EletronicosEssenciais",
            "#VidaMaisFácil",
            "#NovidadesTecnológicas",
            "#ReviewDeProdutos",
            "#PraticidadeDiária",
            "#TecnologiaEmCasa",
            "#MelhoresEletronicos",
            "#shorts"
        ]
        
        selected_hashtags = random.sample(hashtags[:-1], 5) + ["#shorts"]
        
        description = f"""✨ {title}

🎯 Compartilhando dicas e novidades tecnológicas!
💡 Descubra produtos que podem melhorar seu dia a dia
🌟 Conhecimento é para ser compartilhado

{' '.join(selected_hashtags)}

👋 Deixe seu comentário e compartilhe suas experiências!"""
        
        return description
    
    def upload_video(self, video_path, title=None):
        """Faz upload de um vídeo como Short"""
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")
            
            # Se não forneceu título, usa o nome do arquivo
            if not title:
                title = os.path.splitext(os.path.basename(video_path))[0]
            
            # Limita o título a 100 caracteres
            if len(title) > 100:
                title = title[:97] + "..."
            
            # Gera descrição
            description = self.generate_description(title)
            
            # Define os metadados do vídeo
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': ['shorts', 'tecnologia', 'inovação', 'produtos'],
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': 'private',  # Começa como privado para verificação
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Prepara o arquivo para upload
            media = MediaFileUpload(
                video_path,
                mimetype='video/mp4',
                resumable=True
            )
            
            # Faz o upload
            print(f"\nIniciando upload de: {title}")
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Upload {int(status.progress() * 100)}% completo...")
            
            video_id = response['id']
            print(f"Upload concluído! ID do vídeo: {video_id}")
            
            # Registra o upload
            self._log_upload(video_path, video_id, title)
            
            return video_id
            
        except HttpError as e:
            print(f"Erro no upload: {str(e)}")
            return None
        except Exception as e:
            print(f"Erro inesperado: {str(e)}")
            return None
    
    def _log_upload(self, video_path, video_id, title):
        """Registra informações do upload"""
        log_file = "uploads_log.json"
        
        # Carrega logs existentes
        logs = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                try:
                    logs = json.load(f)
                except:
                    logs = []
        
        # Adiciona novo log
        logs.append({
            'timestamp': datetime.now().isoformat(),
            'video_path': video_path,
            'video_id': video_id,
            'title': title,
            'url': f'https://youtube.com/shorts/{video_id}'
        })
        
        # Salva logs
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def upload_directory(self, directory_path, delay_minutes=1):
        """Faz upload de todos os vídeos em um diretório"""
        if not os.path.exists(directory_path):
            print(f"Diretório não encontrado: {directory_path}")
            return
        
        # Lista todos os vídeos MP4
        videos = [f for f in os.listdir(directory_path) if f.endswith('.mp4')]
        
        if not videos:
            print("Nenhum vídeo encontrado no diretório.")
            return
        
        print(f"Encontrados {len(videos)} vídeos para upload.")
        
        # Faz upload de cada vídeo
        for i, video in enumerate(videos, 1):
            video_path = os.path.join(directory_path, video)
            
            # Extrai título do nome do arquivo
            title = os.path.splitext(video)[0]
            if title.startswith(('video_', 'temp_')):
                title = ' '.join(title.split('_')[1:])
            
            print(f"\nProcessando vídeo {i}/{len(videos)}: {title}")
            
            # Tenta fazer o upload com retry em caso de erro
            max_retries = 3
            retry_count = 0
            video_id = None
            
            while retry_count < max_retries and not video_id:
                try:
                    video_id = self.upload_video(video_path, title)
                    if video_id:
                        print(f"Upload bem sucedido após {retry_count + 1} tentativa(s)")
                    else:
                        raise Exception("Upload falhou")
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = retry_count * 30  # Aumenta o tempo de espera a cada retry
                        print(f"Tentativa {retry_count} falhou. Aguardando {wait_time} segundos...")
                        time.sleep(wait_time)
                    else:
                        print(f"Todas as tentativas falharam para o vídeo: {title}")
                        print(f"Erro: {str(e)}")
            
            # Aguarda entre uploads (apenas se não for o último vídeo)
            if i < len(videos) and video_id:
                print(f"Aguardando {delay_minutes} minuto(s) até o próximo upload...")
                for remaining in range(delay_minutes * 60, 0, -1):
                    mins = remaining // 60
                    secs = remaining % 60
                    print(f"Próximo upload em: {mins:02d}:{secs:02d}", end='\r')
                    time.sleep(1)
                print("\nIniciando próximo upload...")

def main():
    # Arquivo de credenciais do projeto Google Cloud
    client_secrets_file = "client_secrets.json"
    
    if not os.path.exists(client_secrets_file):
        print("""
Erro: Arquivo client_secrets.json não encontrado!

Para obter este arquivo:
1. Acesse https://console.cloud.google.com
2. Crie um projeto (ou selecione um existente)
3. Ative a API do YouTube Data v3
4. Crie credenciais OAuth 2.0
5. Baixe o arquivo JSON e renomeie para client_secrets.json
""")
        return
    
    while True:
        print("\n=== YouTube Shorts Uploader ===")
        print("1. Usar canal existente")
        print("2. Adicionar novo canal")
        print("3. Trocar de canal")
        print("4. Sair")
        
        choice = input("\nEscolha uma opção: ")
        
        if choice == "1":
            # Lista os canais disponíveis
            tokens = [f for f in os.listdir('.') if f.startswith('token_') and f.endswith('.pickle')]
            if not tokens:
                print("Nenhum canal configurado. Escolha a opção 2 para adicionar um canal.")
                continue
            
            print("\nCanais disponíveis:")
            for i, token in enumerate(tokens, 1):
                channel_name = token[6:-7]  # Remove 'token_' e '.pickle'
                print(f"{i}. {channel_name}")
            
            channel_idx = int(input("\nEscolha o canal: ")) - 1
            if 0 <= channel_idx < len(tokens):
                channel_name = tokens[channel_idx][6:-7]
                uploader = YouTubeShortsUploader(client_secrets_file, channel_name)
                uploader.authenticate()
                
                # Diretório com os vídeos
                videos_dir = "videos_temu"
                if not os.path.exists(videos_dir):
                    print(f"Diretório {videos_dir} não encontrado!")
                    continue
                
                uploader.upload_directory(videos_dir)
            
        elif choice == "2":
            channel_name = input("Digite um nome para identificar o canal: ")
            uploader = YouTubeShortsUploader(client_secrets_file, channel_name)
            uploader.force_new_authentication()
            uploader.authenticate()
            print(f"\nCanal {channel_name} configurado com sucesso!")
            
        elif choice == "3":
            tokens = [f for f in os.listdir('.') if f.startswith('token_') and f.endswith('.pickle')]
            if not tokens:
                print("Nenhum canal configurado.")
                continue
            
            print("\nCanais disponíveis:")
            for i, token in enumerate(tokens, 1):
                channel_name = token[6:-7]
                print(f"{i}. {channel_name}")
            
            channel_idx = int(input("\nEscolha o canal para reautenticar: ")) - 1
            if 0 <= channel_idx < len(tokens):
                channel_name = tokens[channel_idx][6:-7]
                uploader = YouTubeShortsUploader(client_secrets_file, channel_name)
                uploader.force_new_authentication()
                uploader.authenticate()
                print(f"\nCanal {channel_name} reautenticado com sucesso!")
        
        elif choice == "4":
            break
        
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    main()
