---
name: cli-anything-gemini-desktop
description: Conversar diretamente com o Gemini Desktop no terminal e delegar tarefas usando os créditos do app oficial (0 tokens de IDE) para Claude Code, Codex e Antigravity.
---

# Gemini Desktop CLI-Anything Skill

Este skill permite conversar com o **Google Gemini Desktop** no Windows via terminal, pedir Deep Research e exportar tarefas para uma fila configurável.

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
Usa o raciocínio e a cota do Gemini Desktop para tomar decisões de arquitetura e emitir ordens para uma fila opcional, configurada em `GEMINI_DESKTOP_QUEUE_DIR` (diretório existente):
```bash
cli-anything-gemini-desktop delegate "Refatore o componente Navbar para mobile"
```
Com arquivo de contexto anexado:
```bash
cli-anything-gemini-desktop delegate -f "docs/especificacao.md" "Analise a spec e crie ordens para o Claude Code e testes para a IDE"
```
*O que acontece:*
1. O Gemini Desktop analisa a solicitação e formula a arquitetura.
2. Gera blocos de código JSON no formato da fila configurada:
   - `peso_3` / `claude` ➔ Claude Code (frontend, UX, design).
   - `peso_3` / `codex` ➔ Codex (auditoria crítica).
   - `peso_2` / `agy` ➔ Antigravity (scripts, testes na IDE).
3. Quando a fila está configurada, o CLI salva cada ordem em `<GEMINI_DESKTOP_QUEUE_DIR>/<id>.json`.
4. Um executor externo pode consumir esses arquivos. Sem a variável, nenhuma ordem é salva.

### Deep Research (`deep-research`)

```powershell
cli-anything-gemini-desktop deep-research "Compare fornecedores de energia solar" --json
```

Seleciona a ferramenta Deep Research pela acessibilidade do Windows antes de
enviar o pedido. Falha sem enviar uma pergunta comum quando não consegue confirmar
a seleção. Revise o plano no Gemini e clique em iniciar pesquisa quando estiver
pronto. O comando não aprova o plano nem coleta o relatório final.
Use `--no-submit` para preparar um rascunho. A janela fica visível por padrão.

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
- **Deep Research:** Exceção ao modo off-screen por padrão: a janela fica visível para seleção da ferramenta e revisão do plano. A seleção pode levar até 15 segundos.
- **Zero ocupação de tela (Off-screen):** A janela do Gemini opera fora da área visível do monitor (`30000, 30000`) e é ocultada de volta à bandeja (`SW_HIDE`) ao concluir. O usuário nunca tem sua tela coberta.
- **Zero perturbação do mouse:** O cursor do usuário não é deslocado na sua tela visível e o estado é preservado.
- **Zero perda de área de transferência:** O conteúdo original do clipboard do usuário é salvo e restaurado imediatamente.
- **Foco preservado:** A janela ativa do usuário (terminal, editor ou navegador) é restaurada instantaneamente (<20ms).
- **Zero tokens da IDE:** O raciocínio e planejamento são processados nos servidores da Google via cliente Desktop oficial.
