# YouTube Shorts Uploader + Temu Video Extractor

Este projeto consiste em duas ferramentas poderosas para automatizar a extração de vídeos do Temu e fazer upload como Shorts no YouTube.

## 🚀 Funcionalidades

### 1. Extrator de Vídeos do Temu (`temu_video_extractor.py`)
- Extrai vídeos de produtos do Temu
- Análise automática do conteúdo usando Google Gemini
- Geração de títulos descritivos
- Download automático dos vídeos

### 2. Uploader de YouTube Shorts (`youtube_shorts_uploader.py`)
- Upload automático de vídeos como Shorts
- Suporte a múltiplos canais
- Descrições personalizadas
- Sistema de hashtags inteligente
- Gerenciamento de uploads em lote

## 📋 Pré-requisitos

1. Python 3.7 ou superior
2. Bibliotecas necessárias:
```bash
pip install google-auth-oauthlib google-api-python-client opencv-python pillow requests numpy
```

3. Credenciais do Google Cloud:
   - Conta Google
   - Projeto no Google Cloud Platform
   - API do YouTube Data v3 ativada
   - Credenciais OAuth 2.0

## 🔧 Configuração

### 1. Configuração do Google Cloud

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um novo projeto ou selecione um existente
3. Ative a API do YouTube Data v3:
   - Menu lateral > APIs e Serviços > Biblioteca
   - Procure por "YouTube Data API v3"
   - Clique em "Ativar"

4. Configure o OAuth:
   - Menu lateral > APIs e Serviços > Tela de consentimento OAuth
   - Escolha "Externo"
   - Preencha as informações necessárias
   - Adicione o escopo: `https://www.googleapis.com/auth/youtube.upload`
   - Adicione seu email como usuário de teste

5. Crie as credenciais:
   - Menu lateral > APIs e Serviços > Credenciais
   - "Criar Credenciais" > "ID do Cliente OAuth"
   - Tipo: "Aplicativo para Computador"
   - Baixe o JSON e renomeie para `client_secrets.json`

### 2. Estrutura de Diretórios

```
UPLOADS_SHORTS/
├── client_secrets.json
├── temu_video_extractor.py
├── youtube_shorts_uploader.py
├── videos_temu/
└── uploads_log.json
```

## 📖 Como Usar

### 1. Extrator de Vídeos do Temu

1. Execute o script:
```bash
python temu_video_extractor.py
```

2. Insira a URL da página de produtos do Temu
3. O script irá:
   - Extrair os vídeos
   - Analisar o conteúdo
   - Gerar títulos descritivos
   - Salvar na pasta `videos_temu`

### 2. Uploader de YouTube Shorts

1. Execute o script:
```bash
python youtube_shorts_uploader.py
```

2. Escolha uma opção:
   - 1: Usar canal existente
   - 2: Adicionar novo canal
   - 3: Trocar de canal
   - 4: Sair

3. Para novo canal:
   - Digite um nome identificador
   - Faça login no navegador
   - Autorize o aplicativo

4. Para upload:
   - Selecione o canal
   - Os vídeos da pasta `videos_temu` serão enviados
   - Intervalo de 1 minuto entre uploads

## 📝 Logs e Monitoramento

- `uploads_log.json`: Registro detalhado de uploads
  - Timestamp
  - Nome do vídeo
  - ID do vídeo
  - URL do Short
  - Status do upload

## ⚠️ Limites e Considerações

1. **Limites da API do YouTube**:
   - 10.000 unidades de cota por dia
   - Cada upload consome aproximadamente 1.600 unidades

2. **Múltiplos Canais**:
   - Use tokens diferentes para cada canal
   - Arquivos de token são nomeados como `token_NOME.pickle`

3. **Segurança**:
   - Nunca compartilhe `client_secrets.json`
   - Não comite tokens no git
   - Mantenha suas credenciais seguras

## 🔄 Fluxo de Trabalho Recomendado

1. **Extração**:
   - Use o extrator para baixar vídeos
   - Verifique os títulos gerados
   - Organize os vídeos se necessário

2. **Upload**:
   - Configure seus canais
   - Faça upload em lotes
   - Monitore os logs
   - Alterne entre canais conforme necessário

## 🆘 Solução de Problemas

1. **Erro de Autenticação**:
   - Use opção 3 para reautenticar
   - Verifique as credenciais
   - Confirme as permissões da API

2. **Falha no Upload**:
   - Verifique a conexão
   - Confirme o formato do vídeo
   - Observe os logs de erro

3. **Limite de API**:
   - Alterne para outro canal
   - Aguarde 24 horas
   - Monitore o uso da cota

## 📫 Suporte

Para problemas e sugestões:
1. Abra uma issue no GitHub
2. Descreva o problema detalhadamente
3. Inclua logs relevantes

## 🔒 Segurança

- Mantenha `client_secrets.json` seguro
- Não compartilhe tokens
- Use o `.gitignore` fornecido
- Revogue credenciais comprometidas

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
