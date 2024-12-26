import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
import os
import requests
import time
import re
from urllib.parse import urljoin, urlparse
import cv2
import base64
import numpy as np
from PIL import Image
import io

class VideoAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    def extract_frames(self, video_path, num_frames=3):
        """Extrai frames do vídeo para análise"""
        frames = []
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames == 0:
                return frames
            
            # Pega frames em diferentes pontos do vídeo
            frame_positions = [int(total_frames * i / (num_frames + 1)) for i in range(1, num_frames + 1)]
            
            for pos in frame_positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ret, frame = cap.read()
                if ret:
                    # Converte BGR para RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame_rgb)
            
            cap.release()
        except Exception as e:
            print(f"Erro ao extrair frames: {str(e)}")
        
        return frames
    
    def encode_frame(self, frame):
        """Converte frame para base64"""
        try:
            # Converte numpy array para imagem PIL
            img = Image.fromarray(frame)
            
            # Redimensiona se necessário (Gemini tem limite de tamanho)
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Converte para JPEG em memória
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            
            # Converte para base64
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Erro ao codificar frame: {str(e)}")
            return None
    
    def analyze_frames(self, frames):
        """Analisa frames usando Google Gemini"""
        try:
            # Prepara a requisição para o Gemini
            parts = [
                {
                    "text": "Analise estas imagens de um produto e forneça um título curto e atraente que descreva o produto. Foque nas características principais e no uso do produto. Responda APENAS com o título, sem explicações adicionais."
                }
            ]
            
            # Adiciona cada frame como uma imagem
            for frame in frames:
                base64_frame = self.encode_frame(frame)
                if base64_frame:
                    parts.append({
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_frame
                        }
                    })
            
            # Monta o payload
            payload = {
                "contents": [{
                    "parts": parts
                }]
            }
            
            # Faz a requisição para a API
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    title = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    return title
            
            return None
        
        except Exception as e:
            print(f"Erro na análise de frames: {str(e)}")
            return None

class VideoExtractor:
    def __init__(self, api_key):
        self.videos = set()
        self.network_urls = set()
        self.analyzer = VideoAnalyzer(api_key)
        
    def setup_driver(self):
        """Configura o driver com capacidades de interceptação de rede"""
        caps = DesiredCapabilities.CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}
        
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-gpu')
        options.add_argument('--enable-logging')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        
        # Adiciona headers customizados
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = uc.Chrome(options=options, desired_capabilities=caps)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def process_browser_logs(self, driver):
        """Processa logs do browser para encontrar requisições de rede"""
        logs = driver.get_log('performance')
        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']
                if (
                    'Network.response' in log['method'] or 
                    'Network.request' in log['method'] or 
                    'Network.webSocket' in log['method']
                ):
                    if 'request' in log['params']:
                        url = log['params']['request'].get('url', '')
                        if self.is_video_url(url):
                            self.network_urls.add(url)
                            print(f"Encontrado vídeo via rede: {url}")
            except Exception as e:
                continue
    
    def is_video_url(self, url):
        """Verifica se uma URL é de vídeo"""
        video_patterns = [
            r'\.mp4',
            r'goods-vod',
            r'/video/',
            r'videoplayback',
            r'video_content',
            r'media/video'
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in video_patterns)
    
    def extract_from_xhr(self, driver):
        """Extrai URLs de vídeo de requisições XHR"""
        xhr_logs = driver.execute_script("""
            const entries = performance.getEntriesByType('resource');
            return entries.map(entry => entry.name);
        """)
        
        for url in xhr_logs:
            if self.is_video_url(url):
                self.network_urls.add(url)
                print(f"Encontrado vídeo via XHR: {url}")
    
    def extract_from_scripts(self, driver):
        """Extrai URLs de vídeo de scripts na página"""
        scripts = driver.execute_script("""
            return Array.from(document.getElementsByTagName('script')).map(s => s.textContent);
        """)
        
        for script in scripts:
            if not script:
                continue
            
            # Procura por URLs em strings JSON
            try:
                # Tenta encontrar objetos JSON no script
                matches = re.finditer(r'\{[^{}]*\}', script)
                for match in matches:
                    try:
                        data = json.loads(match.group())
                        self.extract_urls_from_json(data)
                    except:
                        continue
            except:
                pass
            
            # Procura por URLs diretas
            urls = re.findall(r'https?://[^\s<>"\'](?:[^\s<>"\']|(?<=\/)\/)*?(?:\.mp4|goods-vod|/video/)', script)
            for url in urls:
                if self.is_video_url(url):
                    self.network_urls.add(url)
                    print(f"Encontrado vídeo em script: {url}")
    
    def extract_urls_from_json(self, data):
        """Extrai URLs de vídeo de objetos JSON"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and self.is_video_url(value):
                    self.network_urls.add(value)
                    print(f"Encontrado vídeo em JSON: {value}")
                elif isinstance(value, (dict, list)):
                    self.extract_urls_from_json(value)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self.extract_urls_from_json(item)
                elif isinstance(item, str) and self.is_video_url(item):
                    self.network_urls.add(item)
                    print(f"Encontrado vídeo em JSON: {item}")
    
    def extract_product_info(self, driver, url):
        """Extrai informações do produto próximo ao vídeo"""
        try:
            # Tenta encontrar o container do produto mais próximo
            script = """
            function findProductInfo(videoUrl) {
                // Encontra elementos de vídeo ou elementos com a URL do vídeo
                let videoElements = Array.from(document.querySelectorAll('video, [src*="' + videoUrl + '"], [data-src*="' + videoUrl + '"]'));
                
                for (let element of videoElements) {
                    let current = element;
                    let maxDepth = 5; // Limite de níveis para procurar
                    let depth = 0;
                    
                    // Sobe na árvore DOM procurando informações do produto
                    while (current && depth < maxDepth) {
                        // Procura por títulos
                        let titleElements = current.querySelectorAll('[class*="title"], [class*="name"], h1, h2, h3, .product-title, .item-title');
                        for (let title of titleElements) {
                            if (title.textContent.trim()) {
                                return {
                                    title: title.textContent.trim(),
                                    price: findPrice(current),
                                    description: findDescription(current)
                                };
                            }
                        }
                        
                        current = current.parentElement;
                        depth++;
                    }
                }
                
                // Se não encontrou nada específico, procura no documento inteiro
                let mainTitle = document.querySelector('h1, [class*="title"]:not([class*="footer"]):not([class*="header"])');
                return {
                    title: mainTitle ? mainTitle.textContent.trim() : '',
                    price: findPrice(document),
                    description: findDescription(document)
                };
            }
            
            function findPrice(element) {
                let priceElement = element.querySelector('[class*="price"], [class*="Price"], .product-price, .item-price');
                return priceElement ? priceElement.textContent.trim() : '';
            }
            
            function findDescription(element) {
                let descElement = element.querySelector('[class*="description"], [class*="Description"], .product-description, .item-description');
                return descElement ? descElement.textContent.trim() : '';
            }
            
            return findProductInfo(arguments[0]);
            """
            
            info = driver.execute_script(script, url)
            
            # Limpa e formata o título
            title = info.get('title', '').strip()
            price = info.get('price', '').strip()
            description = info.get('description', '').strip()
            
            # Se não encontrou título, tenta extrair da URL
            if not title:
                # Extrai o nome do produto da URL
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.split('/')
                # Pega a última parte da URL e remove extensão
                title = path_parts[-1].split('.')[0].replace('-', ' ').replace('_', ' ')
            
            # Combina as informações para criar um título amigável
            friendly_title = title
            if price:
                friendly_title += f" - {price}"
            
            # Remove caracteres inválidos para nome de arquivo
            friendly_title = re.sub(r'[<>:"/\\|?*]', '', friendly_title)
            friendly_title = friendly_title.strip()
            
            # Limita o tamanho do título
            if len(friendly_title) > 100:
                friendly_title = friendly_title[:97] + "..."
            
            return friendly_title or "video"
            
        except Exception as e:
            print(f"Erro ao extrair título: {str(e)}")
            return "video"
    
    def monitor_network(self, driver, duration=10):
        """Monitora o tráfego de rede por um período"""
        print(f"Monitorando tráfego de rede por {duration} segundos...")
        end_time = time.time() + duration
        while time.time() < end_time:
            self.process_browser_logs(driver)
            self.extract_from_xhr(driver)
            time.sleep(1)
    
    def scroll_and_extract(self, driver):
        """Scroll pela página e extrai vídeos"""
        print("Iniciando scroll e extração...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll até o fim
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Extrai dados
            self.process_browser_logs(driver)
            self.extract_from_xhr(driver)
            self.extract_from_scripts(driver)
            
            # Monitora a rede por alguns segundos após cada scroll
            self.monitor_network(driver, 5)
            
            # Verifica se chegou ao fim
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
            print(f"Total de vídeos encontrados até agora: {len(self.network_urls)}")
    
    def download_and_analyze_video(self, url, output_folder, index):
        """Baixa o vídeo e gera um título usando IA"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'video/webm,video/mp4,video/*;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Referer': 'https://www.temu.com/'
            }
            
            # Primeiro baixa o vídeo com um nome temporário
            temp_filename = f"temp_video_{index}.mp4"
            temp_filepath = os.path.join(output_folder, temp_filename)
            
            print(f"Baixando vídeo {index}...")
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(temp_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Extrai frames e analisa
            print("Analisando vídeo com IA...")
            frames = self.analyzer.extract_frames(temp_filepath)
            if frames:
                title = self.analyzer.analyze_frames(frames)
                if not title:
                    title = f"Produto Temu {index}"
            else:
                title = f"Produto Temu {index}"
            
            # Remove caracteres inválidos do título
            title = re.sub(r'[<>:"/\\|?*]', '', title)
            title = title.strip()
            
            # Renomeia o arquivo com o novo título
            final_filename = f"{index:03d}_{title}.mp4"
            final_filepath = os.path.join(output_folder, final_filename)
            
            try:
                os.rename(temp_filepath, final_filepath)
            except Exception as e:
                print(f"Erro ao renomear arquivo: {str(e)}")
                final_filepath = temp_filepath
            
            print(f"✓ Baixado e analisado: {os.path.basename(final_filepath)}")
            return final_filepath
            
        except Exception as e:
            print(f"✗ Erro ao processar vídeo {index}: {str(e)}")
            return None
    
    def process_page(self, url):
        """Processa uma página para encontrar e baixar vídeos"""
        try:
            print(f"\nAcessando: {url}")
            driver = self.setup_driver()
            
            try:
                # Carrega a página
                driver.get(url)
                print("Aguardando carregamento inicial (15s)...")
                time.sleep(15)
                
                # Extrai vídeos
                self.scroll_and_extract(driver)
                
                if not self.network_urls:
                    print("Nenhum vídeo encontrado.")
                    return []
                
                print(f"\nEncontrados {len(self.network_urls)} vídeos únicos!")
                
                # Cria pasta para os vídeos
                output_folder = 'videos_temu'
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                
                # Baixa e analisa os vídeos
                downloaded_files = []
                for i, video_url in enumerate(self.network_urls, 1):
                    print(f"\nProcessando vídeo {i}/{len(self.network_urls)}")
                    print(f"URL: {video_url}")
                    
                    filepath = self.download_and_analyze_video(video_url, output_folder, i)
                    if filepath:
                        downloaded_files.append(filepath)
                
                return downloaded_files
                
            finally:
                input("\nPressione ENTER para fechar o navegador...")
                try:
                    driver.quit()
                except:
                    pass
                
        except Exception as e:
            print(f"Erro: {str(e)}")
            return []

def main():
    # API key do Gemini
    api_key = "AIzaSyAlCUCT94C5WCSkC1YjBphbVhZr9GlJJ0s"
    
    url = input("Digite a URL da página de produtos do Temu: ")
    if 'temu.com' not in url:
        print("Por favor, insira uma URL válida do Temu.")
        return
    
    extractor = VideoExtractor(api_key)
    downloaded_files = extractor.process_page(url)
    
    if downloaded_files:
        print(f"\nSucesso! {len(downloaded_files)} vídeos baixados:")
        for file in downloaded_files:
            print(f"- {file}")
    else:
        print("\nNenhum vídeo foi baixado.")

if __name__ == "__main__":
    main()
