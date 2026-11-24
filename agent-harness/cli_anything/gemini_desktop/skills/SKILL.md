---
name: cli-anything-gemini-desktop
description: Conversar diretamente com o Gemini Desktop no terminal e delegar tarefas usando os créditos do app oficial (0 tokens de IDE) para Claude Code, Codex e Antigravity.
---

# Gemini Desktop CLI-Anything Skill

Este skill permite conversar diretamente com o cliente oficial do **Google Gemini Desktop** no Windows via terminal (com resposta exibida no stdout) e utilizá-lo como arquiteto principal para planejar e delegar tarefas automaticamente aos agentes operacionais (**Claude Code**, **Codex** e **Antigravity/IDE**) através da fila `00-Sistema/fila/`, consumindo **zero tokens da IDE**.

## 🚀 Principais Comandos

### 1. Conversa Direta no Terminal (`ask`)
Envia uma pergunta ou instrução ao Gemini Desktop e exibe a resposta completa no terminal:
```bash
cli-anything-gemini-desktop ask "Qual a diferença entre latência e throughput?"
```
*Opções:*
- `--timeout 90`: Tempo máximo de espera para conclusão da resposta (padrão: 90s).
- `--json`: Retorna a resposta estruturada em JSON (`{ "success": true, "response": "..." }`).

---

### 2. Delegação Automática com Créditos do Gemini (`delegate`)
Usa o raciocínio e a cota do Gemini Desktop (gratuita/pro do app oficial) para tomar decisões de arquitetura e emitir ordens executivas diretamente para a fila do `despachante.py` (`00-Sistema/fila/`):
```bash
cli-anything-gemini-desktop delegate "Refatore o componente Navbar para mobile"
```
Com arquivo de contexto anexado:
```bash
cli-anything-gemini-desktop delegate -f "docs/especificacao.md" "Analise a spec e crie ordens para o Claude Code e testes para a IDE"
```
*O que acontece:*
1. O Gemini Desktop analisa a solicitação e formula a arquitetura.
2. Gera blocos de código ```json no schema oficial da fila do LLM-OS:
   - `peso_3` / `claude` ➔ Claude Code (frontend, UX, design).
   - `peso_3` / `codex` ➔ Codex (auditoria crítica).
   - `peso_2` / `agy` ➔ Antigravity (scripts, testes na IDE).
3. O CLI salva automaticamente cada ordem em `00-Sistema/fila/<id>.json`.
4. O `despachante.py` assume e orquestra a execução.

---

### 3. Envio e Injeção Rápida (`send` e `bridge`)
- Injetar texto sem esperar resposta:
  ```bash
  cli-anything-gemini-desktop send "Texto longo ou instrução" --submit
  ```
- Anexar arquivos de código/markdown e colar no chat:
  ```bash
  cli-anything-gemini-desktop bridge -f "arquivo.py" "Explique esta função" --submit
  ```

---

### 4. Monitoramento e Configurações (`status`, `settings`, `session`)
- Verificar status e consumo de memória:
  ```bash
  cli-anything-gemini-desktop status --json
  ```
- Inspecionar ou alterar configurações locais (`settings.json`):
  ```bash
  cli-anything-gemini-desktop settings --list --json
  cli-anything-gemini-desktop settings --set shortcut "Alt+Space" --json
  ```
- Auditoria de arquivos e cache de sessão:
  ```bash
  cli-anything-gemini-desktop session --detailed --json
  ```
- REPL interativo:
  ```bash
  cli-anything-gemini-desktop repl
  ```

## 🛡️ Garantias de Usabilidade e Modo Stealth
- **Zero ocupação de tela (Off-screen):** A janela do Gemini opera fora da área visível do monitor (`30000, 30000`) e é ocultada de volta à bandeja (`SW_HIDE`) ao concluir. O usuário nunca tem sua tela coberta.
- **Zero perturbação do mouse:** O cursor do usuário não é deslocado na sua tela visível e o estado é preservado.
- **Zero perda de área de transferência:** O conteúdo original do clipboard do usuário é salvo e restaurado imediatamente.
- **Foco preservado:** A janela ativa do usuário (terminal, editor ou navegador) é restaurada instantaneamente (<20ms).
- **Zero tokens da IDE:** O raciocínio e planejamento são processados nos servidores da Google via cliente Desktop oficial.
