# Crônicas do Reino — Sistema de RPG

Backend Python baseado no documento [Descricao_Projeto.pdf](./Descricao_Projeto.pdf). O projeto usa Clean Architecture, SOLID, Builder, Strategy e Observer para implementar autenticação, personagens, missões, inventário, combates, evolução, histórico e administração do jogo. As entidades ficam explícitas em `app/entities` e os casos de uso UC01–UC03 possuem classes com método `execute` em `app/use_case`.

O diagrama de classes do PDF foi mantido como referência e será atualizado somente quando o código estiver fechado, conforme combinado.

## Tecnologias

- Python 3.14;
- FastAPI com versão fixada;
- `sqlite3` da biblioteca padrão, sem ORM;
- `dataclasses` e classes abstratas para POO;
- `unittest` para testes;
- HTML, CSS e JavaScript na interface.

Essa combinação mantém o projeto pequeno: a única dependência declarada instala a stack oficial do FastAPI, enquanto domínio, banco, segurança e testes usam recursos nativos do Python.

## Instalação no Windows

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Execute:

```powershell
.venv\Scripts\python.exe run.py
```

Abra:

- aplicação: `http://localhost:3000`;
- documentação interativa da API: `http://localhost:3000/docs`.

Na primeira execução, o banco e o Mestre Administrador são criados automaticamente:

```text
E-mail: mestre@rpg.local
Senha:  Mestre@123
```

Copie [.env.example](./.env.example) para `.env` para alterar porta, banco e credenciais. Troque a senha padrão fora do ambiente acadêmico.

## Painel do Mestre

Entre na aplicação com uma conta `MESTRE` ou `ADMINISTRADOR`. O **Painel do Mestre** aparece no início da área principal e permite trabalhar sem preencher JSON no Swagger:

- **Cadastros:** criar, editar e excluir classes, raças, habilidades, itens, missões e inimigos;
- **Personagens e itens:** consultar todos os personagens, entregar itens e remover unidades do inventário;
- **Usuários:** consultar contas; Administradores também podem alterar os perfis entre Jogador, Mestre e Administrador;
- **Visão geral:** acompanhar a quantidade de registros de cada área.

Para dar uma poção ao Pedrinho, abra **Personagens e itens**, selecione `Pedrinho`, escolha a poção, informe a quantidade e clique em **Entregar item**.

O Swagger em `http://localhost:3000/docs` continua disponível no botão **API avançada** para testes técnicos.

## Conteúdo para demonstração

O banco recebe automaticamente um conjunto variado para testes: 6 classes, 6 raças, 18 habilidades, 16 itens — incluindo 7 armas e poções de vida e mana —, 9 missões e 10 inimigos. Classes, raças, habilidades, itens e missões possuem descrições completas.

A carga é idempotente: cada inicialização adiciona somente os registros de demonstração ausentes. Personagens, inventários e cadastros criados manualmente são preservados.

## Evolução e atributos

Cada nível conquistado concede **5 pontos de atributo**. Ao selecionar o personagem, o jogador encontra a seção **Distribuir atributos** no resumo e pode aplicar os pontos, um por vez, em Força, Defesa, Agilidade, Inteligência, Vitalidade ou Carisma.

Vitalidade também concede 2 pontos de vida máxima por ponto distribuído; Inteligência concede 1 ponto de energia máxima. A distribuição fica bloqueada durante combates.

Habilidades vinculadas à classe ou à raça são herdadas dinamicamente. Portanto, uma habilidade criada pelo Mestre também aparece nos personagens existentes daquele grupo; antes do nível mínimo ela é mostrada como bloqueada e, ao alcançar o nível exigido, fica disponível no combate.

Habilidades sem classe e sem raça são consideradas gerais e aparecem para todos. Quando um personagem é derrotado, o botão **Descansar e recuperar** restaura sua vida e energia e permite que ele volte a se aventurar.

## Combate com d100 e Agilidade oposta

Cada ataque do personagem e do inimigo segue a conta `d100 + Agilidade do atacante − Agilidade do defensor`. Se o resultado ajustado for **maior que 70**, o ataque acerta; com 70 ou menos, erra e não causa dano. Assim, cada ponto de Agilidade aumenta em 1% a própria chance de acerto e reduz em 1% a chance do adversário. Habilidades gastam energia mesmo quando erram.

Durante a luta, um HUD central mantém vida, energia, Força, Defesa, Agilidade, Inteligência, bônus de equipamento, botões de ação e resultados dos dados sempre visíveis. Poções de vida e mana podem ser usadas no próprio modal, e os últimos turnos também ficam disponíveis para consulta.

## Testes

```powershell
.venv\Scripts\python.exe -m unittest discover -v
.venv\Scripts\python.exe -m compileall -q app test
```

## Estrutura

```text
app/
├── entities/        # Entidades: usuário, personagem, missão, item, combate etc.
├── use_case/        # UC01 Criar Personagem, UC02 Aceitar Missão e UC03 Realizar Combate
├── domain/          # Enums, erros, eventos e padrões
├── application/
│   ├── game_services.py  # Operações auxiliares agrupadas por área
│   └── ports.py     # Interfaces de entrada e saída da aplicação
├── infrastructure/  # SQLite, segurança, eventos e repositório
├── interfaces/      # API FastAPI
├── config.py
├── container.py     # Injeção de dependências
└── main.py
public/              # Interface web
test/                # Testes unitários e integrados
run.py               # Inicialização simples
```

Mais detalhes em [docs/ARQUITETURA.md](./docs/ARQUITETURA.md) e [docs/API.md](./docs/API.md).
