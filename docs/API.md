# API REST

Base: `/api`. A documentação executável fica em `/docs`.

Rotas protegidas exigem `Authorization: Bearer <token>`.

## Autenticação

| Método | Rota | Acesso |
|---|---|---|
| POST | `/auth/register` | Público; cria Jogador |
| POST | `/auth/login` | Público |
| GET | `/auth/me` | Autenticado |
| POST | `/auth/logout` | Autenticado |

## Catálogo e personagens

| Método | Rota | Descrição |
|---|---|---|
| GET | `/catalog/{resource}` | Lista `classes`, `races`, `skills`, `items`, `missions` ou `enemies` |
| GET | `/characters` | Personagens do jogador |
| POST | `/characters` | Cria com `name`, `classId` e `raceId` |
| GET | `/characters/{id}` | Detalhes e habilidades |
| PATCH | `/characters/{id}/attributes` | Distribui `{ "attribute": "strength", "points": 1 }` |
| POST | `/characters/{id}/recover` | Recupera vida e energia de um personagem derrotado |

## Missões

| Método | Rota |
|---|---|
| GET | `/characters/{id}/missions/available` |
| GET | `/characters/{id}/missions` |
| POST | `/characters/{characterId}/missions/{missionId}/accept` |
| PATCH | `/mission-progress/{id}` com `{ "amount": 1 }` |
| POST | `/mission-progress/{id}/complete` |
| POST | `/mission-progress/{id}/cancel` |

## Inventário, combate e histórico

| Método | Rota |
|---|---|
| GET | `/characters/{id}/inventory` |
| POST | `/characters/{characterId}/inventory/{itemId}/equip` |
| POST | `/characters/{characterId}/inventory/{itemId}/unequip` |
| POST | `/characters/{characterId}/inventory/{itemId}/use` |
| DELETE | `/characters/{characterId}/inventory/{itemId}?quantity=1` |
| GET | `/characters/{id}/combats` |
| POST | `/characters/{characterId}/combats/{enemyId}` |
| POST | `/combats/{id}/actions` com `ATAQUE`, `HABILIDADE` ou `FUGIR` |
| GET | `/characters/{id}/history` |

Para usar habilidade:

```json
{
  "action": "HABILIDADE",
  "skillId": "id-da-habilidade"
}
```

Cada resposta de ação de combate inclui em `turn`:

```json
{
  "playerRoll": 72,
  "playerHitChance": 32,
  "playerHit": true,
  "damage": 14,
  "enemyRoll": 66,
  "enemyHitChance": 28,
  "enemyHit": false,
  "enemyDamage": 0
}
```

O acerto usa a regra `d100 + Agilidade do atacante − Agilidade do defensor > 70`. Os campos `playerHitChance` e `enemyHitChance` informam a probabilidade equivalente. Cada ponto de Agilidade aumenta a própria chance em 1% e reduz a chance adversária em 1%.

## Mestre e Administrador

Estas operações estão disponíveis visualmente no **Painel do Mestre** da aplicação. O Swagger em `/docs` é opcional.

| Método | Rota | Acesso |
|---|---|---|
| GET | `/admin/users` | Mestre/Admin |
| GET | `/admin/characters` | Mestre/Admin |
| POST | `/admin/characters/{characterId}/inventory/{itemId}` | Mestre/Admin |
| POST | `/admin/catalog/{resource}` | Mestre/Admin |
| PUT | `/admin/catalog/{resource}/{id}` | Mestre/Admin |
| DELETE | `/admin/catalog/{resource}/{id}` | Mestre/Admin |
| PATCH | `/admin/users/{id}/role` | Somente Admin |

Recursos administrativos aceitos: `classes`, `races`, `skills`, `items`, `missions` e `enemies`.

Erros:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Mensagem clara para o usuário."
  }
}
```
