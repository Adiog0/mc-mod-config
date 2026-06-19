# ⛏ Minecraft Mod Config Editor — by Makalove

Editor visual multiplataforma para arquivos de configuração de mods Minecraft.  
Suporta instâncias do **Minecraft** / **ElyPrismLauncher** em Windows, Linux e macOS.

![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Platform: Cross-platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)
![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![UI: PyQt6](https://img.shields.io/badge/UI-PyQt6-green)

---

## 📸 Screenshots

<details open>
<summary><b>Clique para expandir/colapsar</b></summary>
<br>
<img src="Screenshots/interface_1.png" alt="Tela principal" width="800">
<br><br>
<img src="Screenshots/interface_2.png" alt="Editor de parametros" width="800">
<br><br>
<img src="Screenshots/interface_3.png" alt="Selecao de mods" width="800">
<br><br>
<img src="Screenshots/interface_4.png" alt="Editor raw e visual" width="800">
</details>

---

## 📋 Funcionalidades

- **Editor visual** com cards estilizados para cada parâmetro (TOML, JSON, JSON5, YAML)
- **Editor Raw** com abas `Visual | Raw` para formatos legados (CFG, Properties, TXT, SNBT, INI)
- **Toggle Switch** customizado para booleanos (substitui checkbox)
- **Campos numéricos** com botões +/− visíveis
- **Árvore expansível** de mods → arquivos com seleção destacada
- **Seções recolhíveis** com indicador ▶/▼ e hint `[Clique para expandir]`
- **Adicionar/remover parâmetros** via interface
- **Backup automático** com timestamp antes de cada salvamento
- **Última instância lembrada** — reabre onde você parou
- **100% customizável via CSS** — edite `style/default.css` ou crie `style/custom.css`
- **Ícones PNG** (30×30) com fallback automático para emoji
- **Instalação automática de dependências** ao abrir o app

---

## 🚀 Como usar

### Linux / macOS
```bash
cd mc-mod-config
./mc-config-editor                          # seletor de instância
./mc-config-editor -i "caminho/instancia"   # direto
```

### Windows
```cmd
cd mc-mod-config
mc-config-editor.bat                        # seletor de instância
python mc-config-editor.py -i "C:\caminho\instancia"
```

### Python direto (qualquer SO)
```bash
pip install PyQt6 tomlkit pyjson5 pyyaml
python mc-config-editor.py
```

> Se alguma dependência faltar, o app pergunta se deseja instalar automaticamente.

---

## 📦 Dependências

| Pacote | Uso |
|---|---|
| **PyQt6** >= 6.0 | Interface gráfica |
| **tomlkit** | Leitura/escrita de TOML preservando comentários |
| **pyjson5** | Leitura/escrita de JSON5 |
| **pyyaml** | Leitura/escrita de YAML |

Instalação única:
```bash
pip install PyQt6 tomlkit pyjson5 pyyaml
```

Ou crie um ambiente virtual:
```bash
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
pip install PyQt6 tomlkit pyjson5 pyyaml
```

---

## 🎨 Temas e CSS

O app é **100% controlado por CSS** (QSS — Qt Style Sheets).  
Zero cores hardcoded no código Python.

### Trocando o tema
1. Copie o template documentado:
   ```bash
   cp style/example.css style/custom.css
   ```
2. Edite `style/custom.css` com suas cores
3. Reinicie o app — ele detecta automaticamente

### Paletas prontas (no `style/example.css`)
- **Azul Noturno** — tons de azul escuro
- **Verde Floresta** — verde musgo
- **Cinza Minimalista** — clean e neutro

### Menu Visual
- `Visual → Carregar CSS Customizado` — seleciona qualquer arquivo `.css`
- `Visual → Resetar CSS Padrão` — volta ao tema original

### Estrutura dos arquivos de estilo
```
style/
├── default.css   ← tema padrão (não edite — use custom.css)
├── example.css   ← documentação de todos os seletores + paletas
└── custom.css    ← seu tema (crie este arquivo)
```

---

## 🖼️ Ícones

Os ícones são carregados da pasta `icons/` como arquivos **PNG** (fundo transparente).  
Se um ícone não existir, o app usa o emoji correspondente como fallback.

### Lista de ícones
| Arquivo | Tamanho | Descrição |
|---|---|---|
| `pickaxe.png` | 30×30 | Ícone do app (janela e cabeçalho) |
| `castle.png` | 30×30 | Instância atual |
| `block.png` | 16×16 | Mods na árvore |
| `folder.png` | 22×22 | Abrir instância |
| `refresh.png` | 22×22 | Recarregar |
| `palette.png` | 22×22 | Carregar CSS |
| `save.png` | 22×22 | Salvar / Backup |
| `undo.png` | 22×22 | Cancelar |
| `settings.png` | 16×16 | Arquivos TOML |
| `crafting.png` | 16×16 | Arquivos JSON |
| `scroll.png` | 16×16 | Arquivos YAML |
| `file.png` | 16×16 | Outros formatos |
| `add.png` | 22×22 | Adicionar parâmetro |
| `delete.png` | 22×22 | Excluir parâmetro |
| `wrench.png` | 16×16 | Placeholder |
| `check.png` | 16×16 | Sucesso |
| `error.png` | 16×16 | Erro |

> O nome do arquivo é case-insensitive e ignora espaços extras.  
> `pickaxe.png`, `Pickaxe.PNG `, `PICKAXE.png` — todos funcionam.

---

## 🗂️ Estrutura do projeto

```
mc-mod-config/
├── mc-config-editor          ← launcher Linux/macOS
├── mc-config-editor-qt       ← launcher alternativo
├── mc-config-editor.bat      ← launcher Windows
├── mc-config-editor.py       ← entry point (wrapper + auto-install deps)
├── mc-config-editor-qt.py    ← aplicacao principal (PyQt6)
├── README.md                 ← esta documentacao
├── .gitignore
├── icons/                    ← icones PNG (opcionais)
│   └── README.txt            ← referencia dos icones
├── style/
│   ├── default.css           ← tema padrao (pastel)
│   └── example.css           ← template documentado + paletas alternativas
└── logs/                     ← logs de execucao (gitignored)
```

---

## 🔒 Segurança

- **Zero chamadas de rede** — o app nunca acessa a internet
- **Zero coleta de dados** — nenhuma telemetria ou analytics
- Arquivos de configuração são lidos e escritos **apenas localmente**
- Logs contêm apenas informações de debug (versão Python, paths, nome de arquivos)
- `settings.json` armazena apenas o caminho da última instância e geometria da janela

---

## 🧪 Formatos suportados

| Formato | Editor | Preserva comentários |
|---|---|---|
| `.toml` | Visual (campos tipados) | ✅ Sim (via tomlkit) |
| `.json` | Visual (campos tipados) | ❌ |
| `.json5` | Visual (campos tipados) | ❌ |
| `.yaml` / `.yml` | Visual (campos tipados) | ✅ Sim |
| `.cfg` | Raw (editor de texto) | ✅ Sim |
| `.properties` | Raw (editor de texto) | ✅ Sim |
| `.txt` | Raw (editor de texto) | ✅ Sim |
| `.snbt` | Raw (editor de texto) | ✅ Sim |
| `.ini` | Raw (editor de texto) | ✅ Sim |

---

## 📝 Notas

- O app foi testado com instâncias do **PrismLauncher** e **ElyPrismLauncher**
- A estrutura de diretórios esperada é: `instância/minecraft/config/`
- Backups são criados como `arquivo.bak.YYYYMMDD_HHMMSS` no mesmo diretório
- Para desenvolver, use o branch `hml` (homologação). O branch `main` é produção

---

**Feito com 💛 por Makalove**
