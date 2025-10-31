# Image Studio IA

Aplicação desktop em Python utilizando PyQt6 que organiza bibliotecas de imagens, centraliza ajustes de geração de conteúdo e armazena preferências do usuário.

## Executando

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\\Scripts\\activate  # Windows
pip install PyQt6
python main.py
```

Os ajustes visuais estão definidos em `assets/styles.qss`. As preferências do usuário são persistidas em `~/.image_studio_config.json`.
