const state = {
  token: localStorage.getItem('rpg-token'), user: null, characters: [], selected: null,
  catalogs: {}, combat: null, inventory: [],
  admin: { resource: 'skills', editingId: null, characters: [], users: [], inventoryCharacterId: null }
};

const $ = (selector) => document.querySelector(selector);
const authView = $('#auth-view');
const gameView = $('#game-view');
const userArea = $('#user-area');

const playerAttributes = [
  ['strength', 'Força'],
  ['defense', 'Defesa'],
  ['agility', 'Agilidade'],
  ['intelligence', 'Inteligência'],
  ['vitality', 'Vitalidade'],
  ['charisma', 'Carisma']
];

const attributeFields = (group) => playerAttributes.map(([key, label]) => ({
  key: `${group}.${key}`, label, type: 'number', default: 0
}));

const catalogDefinitions = {
  classes: {
    label: 'Classes', singular: 'classe', titleKey: 'name',
    fields: [
      { key: 'name', label: 'Nome', required: true, wide: true },
      { key: 'description', label: 'Descrição', type: 'textarea', wide: true },
      { key: 'baseHealth', label: 'Vida base', type: 'number', min: 1, default: 50, required: true },
      { key: 'baseEnergy', label: 'Energia base', type: 'number', min: 1, default: 20, required: true },
      ...attributeFields('attributes')
    ]
  },
  races: {
    label: 'Raças', singular: 'raça', titleKey: 'name',
    fields: [
      { key: 'name', label: 'Nome', required: true, wide: true },
      { key: 'description', label: 'Descrição', type: 'textarea', wide: true },
      ...attributeFields('modifiers')
    ]
  },
  skills: {
    label: 'Habilidades', singular: 'habilidade', titleKey: 'name',
    note: 'A habilidade pode ser geral ou vinculada a uma classe ou raça. Selecione no máximo um vínculo.',
    fields: [
      { key: 'name', label: 'Nome', required: true, wide: true },
      { key: 'description', label: 'Descrição', type: 'textarea', wide: true },
      { key: 'type', label: 'Tipo', type: 'select', required: true, default: 'MAGICA', options: ['FISICA', 'MAGICA', 'SUPORTE'] },
      { key: 'energyCost', label: 'Custo de energia', type: 'number', min: 0, default: 0, required: true },
      { key: 'damage', label: 'Dano', type: 'number', min: 0, default: 0, required: true },
      { key: 'effect', label: 'Efeito adicional', wide: true },
      { key: 'cooldown', label: 'Recarga em turnos', type: 'number', min: 0, default: 0, required: true },
      { key: 'minLevel', label: 'Nível mínimo', type: 'number', min: 1, default: 1, required: true },
      { key: 'classId', label: 'Classe vinculada', type: 'select', source: 'classes', nullable: true, blankLabel: 'Nenhuma classe' },
      { key: 'raceId', label: 'Raça vinculada', type: 'select', source: 'races', nullable: true, blankLabel: 'Nenhuma raça' }
    ]
  },
  items: {
    label: 'Itens', singular: 'item', titleKey: 'name',
    fields: [
      { key: 'name', label: 'Nome', required: true, wide: true },
      { key: 'description', label: 'Descrição', type: 'textarea', wide: true },
      { key: 'type', label: 'Tipo', type: 'select', required: true, default: 'POCAO', options: ['POCAO', 'ARMA', 'ARMADURA', 'ACESSORIO', 'MISSAO'] },
      { key: 'rarity', label: 'Raridade', type: 'select', required: true, default: 'COMUM', options: ['COMUM', 'INCOMUM', 'RARO', 'EPICO', 'LENDARIO'] },
      { key: 'value', label: 'Valor', type: 'number', min: 0, default: 0, required: true },
      { key: 'minLevel', label: 'Nível mínimo', type: 'number', min: 1, default: 1, required: true },
      { key: 'effectHealth', label: 'Recuperação de vida', type: 'number', default: 0, required: true },
      { key: 'effectEnergy', label: 'Recuperação de mana', type: 'number', default: 0, required: true },
      { key: 'attackBonus', label: 'Bônus de ataque', type: 'number', default: 0, required: true },
      { key: 'defenseBonus', label: 'Bônus de defesa', type: 'number', default: 0, required: true },
      { key: 'requiredClassId', label: 'Classe exigida', type: 'select', source: 'classes', nullable: true, blankLabel: 'Qualquer classe', wide: true }
    ]
  },
  missions: {
    label: 'Missões', singular: 'missão', titleKey: 'title',
    fields: [
      { key: 'title', label: 'Título', required: true, wide: true },
      { key: 'description', label: 'Descrição', type: 'textarea', wide: true },
      { key: 'objective', label: 'Objetivo', required: true, wide: true },
      { key: 'status', label: 'Disponibilidade', type: 'select', required: true, default: 'DISPONIVEL', options: ['DISPONIVEL', 'INDISPONIVEL'] },
      { key: 'minLevel', label: 'Nível mínimo', type: 'number', min: 1, default: 1, required: true },
      { key: 'target', label: 'Meta de progresso', type: 'number', min: 1, default: 1, required: true },
      { key: 'rewardExperience', label: 'Experiência de recompensa', type: 'number', min: 0, default: 0, required: true },
      { key: 'rewardCoins', label: 'Moedas de recompensa', type: 'number', min: 0, default: 0, required: true },
      { key: 'rewardItemId', label: 'Item de recompensa', type: 'select', source: 'items', nullable: true, blankLabel: 'Nenhum item' },
      { key: 'rewardItemQuantity', label: 'Quantidade do item', type: 'number', min: 0, default: 0, required: true }
    ]
  },
  enemies: {
    label: 'Inimigos', singular: 'inimigo', titleKey: 'name',
    fields: [
      { key: 'name', label: 'Nome', required: true, wide: true },
      { key: 'type', label: 'Tipo', type: 'select', required: true, default: 'MONSTRO', options: ['MONSTRO', 'HUMANOIDE', 'FERA', 'MORTO_VIVO', 'CHEFE'] },
      { key: 'level', label: 'Nível', type: 'number', min: 1, default: 1, required: true },
      { key: 'health', label: 'Vida', type: 'number', min: 1, default: 20, required: true },
      { key: 'strength', label: 'Força', type: 'number', min: 0, default: 5, required: true },
      { key: 'defense', label: 'Defesa', type: 'number', min: 0, default: 1, required: true },
      { key: 'agility', label: 'Agilidade', type: 'number', min: 0, default: 1, required: true },
      { key: 'rewardExperience', label: 'Experiência de recompensa', type: 'number', min: 0, default: 0, required: true },
      { key: 'rewardCoins', label: 'Moedas de recompensa', type: 'number', min: 0, default: 0, required: true },
      { key: 'rewardItemId', label: 'Item de recompensa', type: 'select', source: 'items', nullable: true, blankLabel: 'Nenhum item', wide: true }
    ]
  }
};

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
      ...options.headers
    }
  });
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* respostas vazias não possuem JSON */ }
  if (!response.ok) throw new Error(data?.error?.message ?? 'Não foi possível concluir a ação.');
  return data;
}

function message(text, error = false) {
  const box = $('#message');
  box.textContent = text;
  box.classList.toggle('error', error);
  box.classList.remove('hidden');
  setTimeout(() => box.classList.add('hidden'), 4500);
}

function formData(form) { return Object.fromEntries(new FormData(form)); }

document.addEventListener('click', async (event) => {
  const authTab = event.target.closest('[data-auth-tab]');
  if (authTab) {
    document.querySelectorAll('[data-auth-tab]').forEach((node) => node.classList.toggle('active', node === authTab));
    $('#login-form').classList.toggle('hidden', authTab.dataset.authTab !== 'login');
    $('#register-form').classList.toggle('hidden', authTab.dataset.authTab !== 'register');
  }

  const adminTab = event.target.closest('[data-admin-tab]');
  if (adminTab) openAdminTab(adminTab.dataset.adminTab);

  const action = event.target.closest('[data-action]');
  if (!action) return;
  try {
    const id = action.dataset.id;
    if (action.dataset.action === 'select-character') await selectCharacter(id);
    if (action.dataset.action === 'accept-mission') {
      await api(`/characters/${state.selected.id}/missions/${id}/accept`, { method: 'POST' });
      message('Missão aceita.');
      await loadCharacterDetails();
    }
    if (action.dataset.action === 'progress-mission') {
      await api(`/mission-progress/${id}`, { method: 'PATCH', body: JSON.stringify({ amount: 1 }) });
      await loadCharacterDetails();
    }
    if (action.dataset.action === 'complete-mission') {
      const result = await api(`/mission-progress/${id}/complete`, { method: 'POST' });
      const levelMessage = result.levelsGained.length
        ? ` Você alcançou o nível ${result.character.level} e agora possui ${result.character.attributePoints} pontos de atributo.`
        : '';
      message(`Missão concluída e recompensas entregues.${levelMessage}`);
      await refreshAll();
    }
    if (action.dataset.action === 'start-combat') {
      state.combat = await api(`/characters/${state.selected.id}/combats/${id}`, { method: 'POST' });
      message('Combate iniciado.');
      await refreshAll();
    }
    if (action.dataset.action === 'combat') await combatAction(action.dataset.combatAction, action.dataset.skillId);
    if (action.dataset.action === 'use-item') {
      const item = state.inventory.find((entry) => entry.itemId === id);
      await api(`/characters/${state.selected.id}/inventory/${id}/use`, { method: 'POST' });
      message(`${item?.name ?? 'Item'} utilizado.`);
      await refreshAll();
    }
    if (action.dataset.action === 'equip-item' || action.dataset.action === 'unequip-item') {
      const operation = action.dataset.action === 'equip-item' ? 'equip' : 'unequip';
      await api(`/characters/${state.selected.id}/inventory/${id}/${operation}`, { method: 'POST' });
      await refreshAll();
    }
    if (action.dataset.action === 'distribute-attribute') {
      const attribute = action.dataset.attribute;
      const label = playerAttributes.find(([key]) => key === attribute)?.[1] ?? attribute;
      await api(`/characters/${state.selected.id}/attributes`, {
        method: 'PATCH', body: JSON.stringify({ attribute, points: 1 })
      });
      message(`1 ponto distribuído em ${label}.`);
      await loadCharacters();
      await loadCharacterDetails();
    }
    if (action.dataset.action === 'recover-character') {
      await api(`/characters/${state.selected.id}/recover`, { method: 'POST' });
      message('Personagem recuperado. Vida e energia foram restauradas.');
      await loadCharacters();
      await loadCharacterDetails();
    }
    if (action.dataset.action === 'admin-new-catalog') showCatalogEditor();
    if (action.dataset.action === 'admin-edit-catalog') {
      const item = state.catalogs[state.admin.resource].find((entry) => entry.id === id);
      if (item) showCatalogEditor(item);
    }
    if (action.dataset.action === 'admin-delete-catalog') await deleteCatalogItem(id);
    if (action.dataset.action === 'admin-cancel-editor') closeCatalogEditor();
    if (action.dataset.action === 'admin-select-character') {
      $('#grant-character').value = id;
      await loadAdminInventory(id);
    }
    if (action.dataset.action === 'admin-remove-item') await removeAdminItem(id);
    if (action.dataset.action === 'admin-save-role') await saveUserRole(id);
  } catch (error) { message(error.message, true); }
});

$('#login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const result = await api('/auth/login', { method: 'POST', body: JSON.stringify(formData(event.target)) });
    state.token = result.token;
    localStorage.setItem('rpg-token', state.token);
    await enterGame();
  } catch (error) { message(error.message, true); }
});

$('#register-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await api('/auth/register', { method: 'POST', body: JSON.stringify(formData(event.target)) });
    message('Conta criada. Agora faça login.');
    document.querySelector('[data-auth-tab="login"]').click();
  } catch (error) { message(error.message, true); }
});

$('#logout').addEventListener('click', async () => {
  try { await api('/auth/logout', { method: 'POST' }); } catch { /* encerra a sessão local mesmo assim */ }
  localStorage.removeItem('rpg-token');
  state.token = null;
  location.reload();
});

$('#show-create').addEventListener('click', () => $('#character-form').classList.toggle('hidden'));
$('#character-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const created = await api('/characters', { method: 'POST', body: JSON.stringify(formData(event.target)) });
    event.target.reset();
    $('#character-form').classList.add('hidden');
    message('Personagem criado com sucesso.');
    await loadCharacters();
    if (state.user.role !== 'JOGADOR') await loadAdminCharacters();
    await selectCharacter(created.id);
  } catch (error) { message(error.message, true); }
});

$('#admin-resource').addEventListener('change', (event) => {
  state.admin.resource = event.target.value;
  closeCatalogEditor();
  renderCatalogList();
});

$('#admin-catalog-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const definition = catalogDefinitions[state.admin.resource];
  try {
    const data = readCatalogForm(event.target, definition);
    if (state.admin.resource === 'skills' && data.classId && data.raceId) {
      throw new Error('Vincule a habilidade a uma classe ou a uma raça, não às duas.');
    }
    const editing = Boolean(state.admin.editingId);
    const path = `/admin/catalog/${state.admin.resource}${editing ? `/${state.admin.editingId}` : ''}`;
    await api(path, { method: editing ? 'PUT' : 'POST', body: JSON.stringify(data) });
    message(`Cadastro ${editing ? 'atualizado' : 'criado'} com sucesso.`);
    closeCatalogEditor();
    await refreshAdminAfterCatalogChange();
  } catch (error) { message(error.message, true); }
});

$('#grant-character').addEventListener('change', async (event) => {
  try { await loadAdminInventory(event.target.value); } catch (error) { message(error.message, true); }
});

$('#grant-item-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = formData(event.target);
  try {
    await api(`/admin/characters/${data.characterId}/inventory/${data.itemId}`, {
      method: 'POST', body: JSON.stringify({ quantity: Number(data.quantity) })
    });
    const character = state.admin.characters.find((entry) => entry.id === data.characterId);
    const item = state.catalogs.items.find((entry) => entry.id === data.itemId);
    message(`${data.quantity} × ${item?.name ?? 'item'} entregue para ${character?.name ?? 'o personagem'}.`);
    await loadAdminInventory(data.characterId);
    if (state.selected?.id === data.characterId) await loadCharacterDetails();
  } catch (error) { message(error.message, true); }
});

async function enterGame() {
  state.user = await api('/auth/me');
  authView.classList.add('hidden');
  gameView.classList.remove('hidden');
  userArea.classList.remove('hidden');
  $('#user-name').textContent = state.user.name;
  $('#user-role').textContent = state.user.role;
  await loadCatalogs();
  await loadCharacters();
  if (state.user.role !== 'JOGADOR') await loadAdminPanel();
}

async function loadCatalogs() {
  const names = ['classes', 'races', 'enemies', 'items', 'missions', 'skills'];
  const values = await Promise.all(names.map((name) => api(`/catalog/${name}`)));
  state.catalogs = Object.fromEntries(names.map((name, index) => [name, values[index]]));
  $('#class-select').innerHTML = state.catalogs.classes.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join('');
  $('#race-select').innerHTML = state.catalogs.races.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join('');
  populateGrantItemOptions();
}

async function loadCharacters() {
  state.characters = await api('/characters');
  $('#character-list').innerHTML = state.characters.length
    ? state.characters.map((character) => `
      <div class="card ${state.selected?.id === character.id ? 'selected' : ''}">
        <strong>${escapeHtml(character.name)}</strong>
        <p>Nível ${character.level} · ${escapeHtml(character.className)} ${escapeHtml(character.raceName)}</p>
        <button class="button small" data-action="select-character" data-id="${escapeHtml(character.id)}">Selecionar</button>
      </div>`).join('')
    : '<p class="muted">Nenhum personagem criado.</p>';
}

async function selectCharacter(id) {
  state.selected = await api(`/characters/${id}`);
  state.combat = (await api(`/characters/${id}/combats`)).find((combat) => combat.status === 'EM_ANDAMENTO') ?? null;
  $('#empty-state').classList.add('hidden');
  $('#character-detail').classList.remove('hidden');
  await loadCharacters();
  await loadCharacterDetails();
}

async function loadCharacterDetails() {
  state.selected = await api(`/characters/${state.selected.id}`);
  const [available, missions, inventory, history] = await Promise.all([
    api(`/characters/${state.selected.id}/missions/available`), api(`/characters/${state.selected.id}/missions`),
    api(`/characters/${state.selected.id}/inventory`), api(`/characters/${state.selected.id}/history`)
  ]);
  state.inventory = inventory;
  renderSummary();
  renderMissions(available, missions);
  renderInventory(inventory);
  renderSkills();
  renderHistory(history);
  renderEnemies();
  renderCombat();
}

async function refreshAll() {
  await loadCharacters();
  await loadCatalogs();
  await loadCharacterDetails();
}

function renderSummary() {
  const c = state.selected;
  const unlockedSkills = c.skills.filter((skill) => c.level >= skill.minLevel).length;
  const stats = [
    ['Nível', c.level], ['Vida', `${c.health}/${c.maxHealth}`], ['Energia', `${c.energy}/${c.maxEnergy}`],
    ['Força', c.attributes.strength], ['Defesa', c.attributes.defense], ['Agilidade', c.attributes.agility],
    ['Inteligência', c.attributes.intelligence], ['Vitalidade', c.attributes.vitality],
    ['Carisma', c.attributes.charisma], ['Moedas', c.coins], ['Habilidades', `${unlockedSkills}/${c.skills.length}`]
  ];
  const cannotDistribute = c.attributePoints < 1 || c.status === 'EM_COMBATE';
  $('#character-summary').innerHTML = `
    <span class="eyebrow">${escapeHtml(c.status.replaceAll('_', ' '))}</span><h2>${escapeHtml(c.name)}</h2>
    <p>${escapeHtml(c.raceName)} · ${escapeHtml(c.className)} · ${c.experience}/${c.level * 100} XP</p>
    <div class="stats">${stats.map(([label, value]) => `<div class="stat"><b>${value}</b><span>${label}</span></div>`).join('')}</div>
    <section class="attribute-distribution ${c.attributePoints > 0 ? 'has-points' : ''}">
      <div class="attribute-heading">
        <div><span class="eyebrow">Evolução</span><h3>Distribuir atributos</h3></div>
        <strong>${c.attributePoints} ${c.attributePoints === 1 ? 'ponto disponível' : 'pontos disponíveis'}</strong>
      </div>
      <p>${c.attributePoints > 0 ? 'Escolha onde aplicar os pontos conquistados. Cada clique distribui 1 ponto.' : 'Ao subir de nível, você recebe 5 pontos para personalizar o personagem.'}</p>
      <div class="attribute-actions">
        ${playerAttributes.map(([key, label]) => `<button class="button small" data-action="distribute-attribute" data-attribute="${key}" ${cannotDistribute ? 'disabled' : ''}>+1 ${label}</button>`).join('')}
      </div>
      ${c.status === 'EM_COMBATE' && c.attributePoints > 0 ? '<small>Finalize o combate antes de distribuir os pontos.</small>' : ''}
    </section>
    ${c.status === 'DERROTADO' ? `<section class="recovery-panel">
      <div><strong>O personagem foi derrotado</strong><p>Descanse para restaurar completamente a vida e a energia antes de voltar à aventura.</p></div>
      <button class="button primary" data-action="recover-character">Descansar e recuperar</button>
    </section>` : ''}`;
}

function renderMissions(available, accepted) {
  const current = accepted.map((mission) => `
    <div class="card"><strong>${escapeHtml(mission.title)}</strong><p>${escapeHtml(mission.status.replaceAll('_', ' '))} · ${mission.progress}/${mission.target}</p>
      <div class="card-actions">
        ${['ACEITA', 'EM_ANDAMENTO'].includes(mission.status) ? `<button class="button small" data-action="progress-mission" data-id="${escapeHtml(mission.id)}">+ progresso</button>` : ''}
        ${mission.progress >= mission.target && mission.status !== 'CONCLUIDA' ? `<button class="button small" data-action="complete-mission" data-id="${escapeHtml(mission.id)}">Concluir</button>` : ''}
      </div></div>`);
  const offered = available.map((mission) => `
    <div class="card"><strong>${escapeHtml(mission.title)}</strong><p>${escapeHtml(mission.objective)} · nível ${mission.minLevel}</p>
      <button class="button small" data-action="accept-mission" data-id="${escapeHtml(mission.id)}">Aceitar</button></div>`);
  $('#mission-list').innerHTML = [...current, ...offered].join('') || '<p class="muted">Nenhuma missão disponível.</p>';
}

function renderEnemies() {
  $('#enemy-list').innerHTML = state.catalogs.enemies.map((enemy) => `
    <div class="card"><strong>${escapeHtml(enemy.name)}</strong><p>Nível ${enemy.level} · ${enemy.health} PV</p>
      <button class="button small" data-action="start-combat" data-id="${escapeHtml(enemy.id)}" ${!['ATIVO', 'EM_MISSAO'].includes(state.selected.status) ? 'disabled' : ''}>Enfrentar</button></div>`).join('');
}

function renderCombat() {
  if (!state.combat || state.combat.status !== 'EM_ANDAMENTO') return void ($('#combat-box').innerHTML = '');
  const skills = state.selected.skills.filter((skill) => state.selected.level >= skill.minLevel);
  const potions = state.inventory.filter((item) => item.type === 'POCAO' && item.quantity > 0);
  const turns = state.combat.turns ?? [];
  const lastTurn = turns.at(-1);
  const c = state.selected;
  const healthPercent = Math.max(0, Math.round((c.health / c.maxHealth) * 100));
  const energyPercent = Math.max(0, Math.round((c.energy / c.maxEnergy) * 100));
  const enemyHealthPercent = Math.max(0, Math.round((state.combat.enemyHealth / state.combat.enemyMaxHealth) * 100));
  $('#combat-box').innerHTML = `<div class="combat-backdrop"><section class="combat-hud" role="dialog" aria-live="polite" aria-label="Combate em andamento">
    <div class="combat-hud-header">
      <div><span class="eyebrow">Combate em andamento</span><h3>${escapeHtml(c.name)} × ${escapeHtml(state.combat.enemyName)}</h3></div>
      <span class="dice-label">d100</span>
    </div>
    <div class="combatants">
      <div class="combatant">
        <div class="combatant-title"><strong>${escapeHtml(c.name)}</strong><span>Nível ${c.level}</span></div>
        ${combatBar('Vida', c.health, c.maxHealth, healthPercent, 'health')}
        ${combatBar('Energia', c.energy, c.maxEnergy, energyPercent, 'energy')}
        <div class="combat-stats">
          <span><b>${c.attributes.strength}</b> Força</span><span><b>${c.attributes.defense}</b> Defesa</span>
          <span><b>${c.attributes.agility}</b> Agilidade</span><span><b>${c.attributes.intelligence}</b> Inteligência</span>
          <span><b>+${c.equipmentBonuses.attack}</b> Ataque</span><span><b>+${c.equipmentBonuses.defense}</b> Proteção</span>
        </div>
      </div>
      <div class="combatant enemy-combatant">
        <div class="combatant-title"><strong>${escapeHtml(state.combat.enemyName)}</strong><span>Inimigo</span></div>
        ${combatBar('Vida', state.combat.enemyHealth, state.combat.enemyMaxHealth, enemyHealthPercent, 'enemy-health')}
        <p class="combat-rule">d100 + Agilidade de quem ataca − Agilidade de quem defende. Acima de 70 acerta.</p>
      </div>
    </div>
    ${lastTurn?.playerRoll ? renderDiceResult(lastTurn) : '<div class="dice-empty">Faça um ataque para rolar os dados.</div>'}
    <div class="combat-items">
      <div><span class="eyebrow">Consumíveis</span><strong>Usar durante o combate</strong></div>
      <div class="combat-item-actions">${potions.length ? potions.map((item) => {
        const useful = (item.effectHealth > 0 && c.health < c.maxHealth) || (item.effectEnergy > 0 && c.energy < c.maxEnergy);
        const effect = [item.effectHealth > 0 ? `+${item.effectHealth} vida` : '', item.effectEnergy > 0 ? `+${item.effectEnergy} energia` : ''].filter(Boolean).join(' · ');
        return `<button class="button small" data-action="use-item" data-id="${escapeHtml(item.itemId)}" ${useful ? '' : 'disabled'}>${escapeHtml(item.name)} × ${item.quantity}<small>${effect}</small></button>`;
      }).join('') : '<span class="muted">Nenhuma poção no inventário.</span>'}</div>
    </div>
    <div class="combat-actions">
      <button class="button primary" data-action="combat" data-combat-action="ATAQUE">Ataque comum</button>
      ${skills.map((skill) => `<button class="button" data-action="combat" data-combat-action="HABILIDADE" data-skill-id="${escapeHtml(skill.id)}" ${c.energy < skill.energyCost ? 'disabled' : ''}>${escapeHtml(skill.name)} <small>${skill.energyCost} energia</small></button>`).join('')}
      <button class="button danger" data-action="combat" data-combat-action="FUGIR">Fugir</button>
    </div>
    ${turns.length ? `<details class="combat-log"><summary>Últimos turnos (${turns.length})</summary>${turns.slice(-4).reverse().map(renderCombatLogEntry).join('')}</details>` : ''}
  </section></div>`;
}

async function combatAction(action, skillId) {
  const result = await api(`/combats/${state.combat.id}/actions`, { method: 'POST', body: JSON.stringify({ action, skillId }) });
  state.combat = result.combat;
  if (action === 'FUGIR') {
    message('Você fugiu do combate.');
    await refreshAll();
    return;
  }
  const levelMessage = result.levelsGained.length
    ? ` Você alcançou o nível ${result.character.level} e agora possui ${result.character.attributePoints} pontos de atributo.`
    : '';
  const playerAgility = result.character.attributes.agility;
  const enemy = state.catalogs.enemies.find((item) => item.id === result.combat.enemyId);
  const enemyAgility = Number(enemy?.agility ?? 0);
  const playerTotal = result.turn.playerRoll + playerAgility - enemyAgility;
  const playerResult = result.turn.playerHit
    ? `Seu d100: ${result.turn.playerRoll} + ${playerAgility} − ${enemyAgility} = ${playerTotal}. Acertou e causou ${result.turn.damage} de dano.`
    : `Seu d100: ${result.turn.playerRoll} + ${playerAgility} − ${enemyAgility} = ${playerTotal}. Precisava passar de 70; o ataque errou.`;
  const enemyResult = result.turn.enemyRoll == null
    ? ''
    : result.turn.enemyHit
      ? ` Inimigo: ${result.turn.enemyRoll} + ${enemyAgility} − ${playerAgility} = ${result.turn.enemyRoll + enemyAgility - playerAgility}. Você recebeu ${result.turn.enemyDamage} de dano.`
      : ` Inimigo: ${result.turn.enemyRoll} + ${enemyAgility} − ${playerAgility} = ${result.turn.enemyRoll + enemyAgility - playerAgility}. Ele precisava passar de 70 e errou.`;
  message(result.combat.status === 'EM_ANDAMENTO'
    ? `${playerResult}${enemyResult}`
    : `Combate encerrado: ${result.combat.status}. ${playerResult}${enemyResult}${levelMessage}`);
  await refreshAll();
}

function combatBar(label, value, maximum, percent, kind) {
  return `<div class="combat-bar-row"><span>${label}</span><div class="combat-bar"><i class="${kind}" style="width:${percent}%"></i></div><b>${value}/${maximum}</b></div>`;
}

function renderDiceResult(turn) {
  const playerAgility = Number(state.selected?.attributes?.agility ?? 0);
  const enemy = state.catalogs.enemies.find((item) => item.id === state.combat?.enemyId);
  const enemyAgility = Number(enemy?.agility ?? 0);
  const enemyResult = turn.enemyRoll == null
    ? '<div class="dice-result neutral"><span>Inimigo</span><b>—</b><small>Derrotado antes de atacar</small></div>'
    : `<div class="dice-result ${turn.enemyHit ? 'hit' : 'miss'}"><span>Dado do inimigo</span><b>${turn.enemyRoll}</b><small>${turn.enemyRoll} + ${enemyAgility} − ${playerAgility} = ${turn.enemyRoll + enemyAgility - playerAgility} · ${turn.enemyHitChance}% · ${turn.enemyHit ? `${turn.enemyDamage} de dano` : 'Errou'}</small></div>`;
  return `<div class="dice-results">
    <div class="dice-result ${turn.playerHit ? 'hit' : 'miss'}"><span>Seu dado</span><b>${turn.playerRoll}</b><small>${turn.playerRoll} + ${playerAgility} − ${enemyAgility} = ${turn.playerRoll + playerAgility - enemyAgility} · ${turn.playerHitChance}% · ${turn.playerHit ? `${turn.damage} de dano` : 'Errou'}</small></div>
    ${enemyResult}
  </div>`;
}

function renderCombatLogEntry(turn) {
  if (turn.playerRoll == null) return `<p><strong>${escapeHtml(turn.action)}</strong></p>`;
  const player = turn.playerHit ? `acertou (${turn.damage})` : 'errou';
  const enemy = turn.enemyRoll == null ? 'não atacou' : turn.enemyHit ? `acertou (${turn.enemyDamage})` : 'errou';
  return `<p><strong>${escapeHtml(turn.action)}</strong> — Você rolou ${turn.playerRoll} e ${player}; inimigo ${enemy}.</p>`;
}

function renderInventory(items) {
  $('#inventory-list').innerHTML = items.length ? items.map((item) => `
    <div class="card"><strong>${escapeHtml(item.name)} × ${item.quantity}</strong><p>${escapeHtml(item.type)} ${item.equipped ? '· Equipado' : ''}</p>
      <div class="card-actions">
        ${item.type === 'POCAO' ? `<button class="button small" data-action="use-item" data-id="${escapeHtml(item.itemId)}">Usar</button>` : ''}
        ${!['POCAO', 'MISSAO'].includes(item.type) ? `<button class="button small" data-action="${item.equipped ? 'unequip-item' : 'equip-item'}" data-id="${escapeHtml(item.itemId)}">${item.equipped ? 'Desequipar' : 'Equipar'}</button>` : ''}
      </div></div>`).join('') : '<p class="muted">Inventário vazio.</p>';
}

function renderSkills() {
  const skills = state.selected.skills ?? [];
  $('#skill-list').innerHTML = skills.length
    ? skills.map((skill) => {
      const unlocked = state.selected.level >= skill.minLevel;
      const origin = skill.classId
        ? `Classe: ${catalogName('classes', skill.classId)}`
        : skill.raceId
          ? `Raça: ${catalogName('races', skill.raceId)}`
          : 'Habilidade geral';
      return `<div class="card skill-card ${unlocked ? 'unlocked' : 'locked'}">
        <div class="skill-heading"><strong>${escapeHtml(skill.name)}</strong><span class="badge">${unlocked ? 'Disponível' : `Nível ${skill.minLevel}`}</span></div>
        <p>${escapeHtml(skill.description || 'Sem descrição.')}</p>
        <small>${escapeHtml(skill.type)} · ${skill.damage} de dano · ${skill.energyCost} de energia · ${escapeHtml(origin)}</small>
      </div>`;
    }).join('')
    : '<p class="muted">Este personagem ainda não possui habilidades.</p>';
}

function renderHistory(events) {
  $('#history-list').innerHTML = events.length ? events.slice(0, 12).map((event) => `
    <div class="timeline-item"><p>${escapeHtml(event.description)}</p><time>${new Date(event.occurredAt).toLocaleString('pt-BR')}</time></div>`).join('')
    : '<p class="muted">A história ainda não começou.</p>';
}

async function loadAdminPanel() {
  $('#admin-panel').classList.remove('hidden');
  const [characters, users] = await Promise.all([api('/admin/characters'), api('/admin/users')]);
  state.admin.characters = characters;
  state.admin.users = users;
  renderAdminSummary();
  renderCatalogList();
  renderAdminCharacters();
  renderAdminUsers();
  populateGrantCharacterOptions();
  populateGrantItemOptions();
  if (state.admin.characters.length) await loadAdminInventory($('#grant-character').value);
}

function openAdminTab(tabName) {
  document.querySelectorAll('.admin-tabs [data-admin-tab]').forEach((node) => node.classList.toggle('active', node.dataset.adminTab === tabName));
  document.querySelectorAll('.admin-view').forEach((node) => node.classList.toggle('hidden', node.id !== `admin-view-${tabName}`));
}

function renderAdminSummary() {
  const entries = [
    ['Classes', state.catalogs.classes.length], ['Raças', state.catalogs.races.length],
    ['Habilidades', state.catalogs.skills.length], ['Itens', state.catalogs.items.length],
    ['Missões', state.catalogs.missions.length], ['Inimigos', state.catalogs.enemies.length],
    ['Personagens', state.admin.characters.length], ['Usuários', state.admin.users.length]
  ];
  $('#admin-summary').innerHTML = entries.map(([label, value]) => `<div class="stat"><b>${value}</b><span>${label}</span></div>`).join('');
}

function renderCatalogList() {
  const resource = state.admin.resource;
  const definition = catalogDefinitions[resource];
  const items = state.catalogs[resource] ?? [];
  $('#admin-resource').value = resource;
  $('#admin-catalog-title').innerHTML = `<div><span class="eyebrow">${items.length} cadastrados</span><h3>${definition.label}</h3></div>`;
  $('#admin-catalog-list').innerHTML = items.length
    ? items.map((item) => `
      <article class="admin-record ${state.admin.editingId === item.id ? 'selected' : ''}">
        <div class="admin-record-header">
          <div><strong>${escapeHtml(item[definition.titleKey])}</strong><p>${escapeHtml(catalogSummary(resource, item))}</p></div>
          <div class="card-actions">
            <button class="button small" data-action="admin-edit-catalog" data-id="${escapeHtml(item.id)}">Editar</button>
            <button class="button danger small" data-action="admin-delete-catalog" data-id="${escapeHtml(item.id)}">Excluir</button>
          </div>
        </div>
      </article>`).join('')
    : '<div class="admin-empty">Nenhum cadastro encontrado.</div>';
}

function catalogSummary(resource, item) {
  if (resource === 'classes') return `${item.description || 'Sem descrição'} · ${item.baseHealth} PV · ${item.baseEnergy} energia`;
  if (resource === 'races') return item.description || 'Sem descrição';
  if (resource === 'skills') {
    const link = item.classId ? `Classe: ${catalogName('classes', item.classId)}` : item.raceId ? `Raça: ${catalogName('races', item.raceId)}` : 'Habilidade geral';
    return `${item.type} · dano ${item.damage} · nível ${item.minLevel} · ${link}`;
  }
  if (resource === 'items') return `${item.type} · ${item.rarity} · nível ${item.minLevel} · valor ${item.value}`;
  if (resource === 'missions') return `${item.objective} · meta ${item.target} · nível ${item.minLevel}`;
  return `${item.type} · nível ${item.level} · ${item.health} PV`;
}

function showCatalogEditor(item = null) {
  const definition = catalogDefinitions[state.admin.resource];
  state.admin.editingId = item?.id ?? null;
  const article = ['items', 'enemies'].includes(state.admin.resource) ? 'Novo' : 'Nova';
  $('#admin-editor-title').textContent = item ? `Editar ${definition.singular}` : `${article} ${definition.singular}`;
  $('#admin-catalog-form').innerHTML = `
    <div class="admin-form-grid">
      ${definition.fields.map((field) => renderCatalogField(field, item)).join('')}
      ${definition.note ? `<p class="form-note">${escapeHtml(definition.note)}</p>` : ''}
      <div class="form-actions">
        <button class="button ghost" type="button" data-action="admin-cancel-editor">Cancelar</button>
        <button class="button primary" type="submit">${item ? 'Salvar alterações' : 'Cadastrar'}</button>
      </div>
    </div>`;
  $('#admin-catalog-editor').classList.remove('hidden');
  renderCatalogList();
  $('#admin-catalog-editor').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeCatalogEditor() {
  state.admin.editingId = null;
  $('#admin-catalog-editor').classList.add('hidden');
  $('#admin-catalog-form').innerHTML = '';
  renderCatalogList();
}

function renderCatalogField(field, item) {
  const current = item ? getPath(item, field.key) : field.default;
  const value = current ?? '';
  const attributes = `${field.required ? 'required' : ''} ${field.min !== undefined ? `min="${field.min}"` : ''}`;
  let control;
  if (field.type === 'textarea') {
    control = `<textarea name="${escapeHtml(field.key)}" ${attributes}>${escapeHtml(value)}</textarea>`;
  } else if (field.type === 'select') {
    const options = field.source
      ? (state.catalogs[field.source] ?? []).map((entry) => ({ value: entry.id, label: entry.name }))
      : field.options.map((entry) => ({ value: entry, label: formatEnum(entry) }));
    control = `<select name="${escapeHtml(field.key)}" ${attributes}>
      ${field.nullable ? `<option value="">${escapeHtml(field.blankLabel ?? 'Nenhum')}</option>` : ''}
      ${options.map((option) => `<option value="${escapeHtml(option.value)}" ${String(option.value) === String(value) ? 'selected' : ''}>${escapeHtml(option.label)}</option>`).join('')}
    </select>`;
  } else {
    control = `<input name="${escapeHtml(field.key)}" type="${field.type ?? 'text'}" value="${escapeHtml(value)}" ${attributes}>`;
  }
  return `<label class="${field.wide ? 'field-wide' : ''}">${escapeHtml(field.label)}${control}</label>`;
}

function readCatalogForm(form, definition) {
  const result = {};
  for (const field of definition.fields) {
    const raw = form.elements.namedItem(field.key).value;
    let value = raw;
    if (field.type === 'number') value = raw === '' ? Number(field.default ?? 0) : Number(raw);
    if (field.nullable && raw === '') value = null;
    setPath(result, field.key, value);
  }
  return result;
}

async function deleteCatalogItem(id) {
  const definition = catalogDefinitions[state.admin.resource];
  const item = state.catalogs[state.admin.resource].find((entry) => entry.id === id);
  if (!item || !confirm(`Excluir ${item[definition.titleKey]}? Esta ação não pode ser desfeita.`)) return;
  await api(`/admin/catalog/${state.admin.resource}/${id}`, { method: 'DELETE' });
  message('Cadastro excluído com sucesso.');
  closeCatalogEditor();
  await refreshAdminAfterCatalogChange();
}

async function refreshAdminAfterCatalogChange() {
  await Promise.all([loadCatalogs(), loadAdminCharacters()]);
  await loadCharacters();
  renderAdminSummary();
  renderCatalogList();
  if (state.selected) await loadCharacterDetails();
}

async function loadAdminCharacters() {
  state.admin.characters = await api('/admin/characters');
  renderAdminCharacters();
  populateGrantCharacterOptions();
}

function renderAdminCharacters() {
  const users = new Map(state.admin.users.map((user) => [user.id, user.name]));
  $('#admin-character-list').innerHTML = state.admin.characters.length
    ? state.admin.characters.map((character) => `
      <article class="admin-record ${state.admin.inventoryCharacterId === character.id ? 'selected' : ''}">
        <div class="admin-record-header">
          <div><strong>${escapeHtml(character.name)}</strong>
            <p>${escapeHtml(users.get(character.playerId) ?? 'Jogador')} · ${escapeHtml(character.className)} · ${escapeHtml(character.raceName)} · nível ${character.level}</p></div>
          <button class="button small" data-action="admin-select-character" data-id="${escapeHtml(character.id)}">Gerenciar itens</button>
        </div>
      </article>`).join('')
    : '<div class="admin-empty">Nenhum personagem cadastrado.</div>';
}

function populateGrantCharacterOptions() {
  const select = $('#grant-character');
  const previous = state.admin.inventoryCharacterId || select.value;
  select.innerHTML = state.admin.characters.map((character) => `<option value="${escapeHtml(character.id)}">${escapeHtml(character.name)} — nível ${character.level}</option>`).join('');
  if (state.admin.characters.some((character) => character.id === previous)) select.value = previous;
  state.admin.inventoryCharacterId = select.value || null;
  $('#grant-item-form button[type="submit"]').disabled = !select.value || !$('#grant-item').value;
}

function populateGrantItemOptions() {
  const select = $('#grant-item');
  const previous = select.value;
  select.innerHTML = (state.catalogs.items ?? []).map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} — ${escapeHtml(item.type)}</option>`).join('');
  if ((state.catalogs.items ?? []).some((item) => item.id === previous)) select.value = previous;
  $('#grant-item-form button[type="submit"]').disabled = !select.value || !$('#grant-character').value;
}

async function loadAdminInventory(characterId) {
  if (!characterId) {
    state.admin.inventoryCharacterId = null;
    $('#admin-inventory-owner').textContent = '';
    $('#admin-inventory-list').innerHTML = '<p class="muted">Nenhum personagem selecionado.</p>';
    return;
  }
  state.admin.inventoryCharacterId = characterId;
  const character = state.admin.characters.find((entry) => entry.id === characterId);
  const items = await api(`/characters/${characterId}/inventory`);
  $('#grant-character').value = characterId;
  $('#admin-inventory-owner').textContent = character?.name ?? '';
  $('#admin-inventory-list').innerHTML = items.length
    ? items.map((item) => `
      <div class="card"><strong>${escapeHtml(item.name)} × ${item.quantity}</strong><p>${escapeHtml(item.type)} ${item.equipped ? '· Equipado' : ''}</p>
        <div class="card-actions"><button class="button danger small" data-action="admin-remove-item" data-id="${escapeHtml(item.itemId)}">Remover 1</button></div></div>`).join('')
    : '<p class="muted">Inventário vazio.</p>';
  renderAdminCharacters();
}

async function removeAdminItem(itemId) {
  const characterId = state.admin.inventoryCharacterId;
  const item = state.catalogs.items.find((entry) => entry.id === itemId);
  if (!characterId || !confirm(`Remover uma unidade de ${item?.name ?? 'este item'}?`)) return;
  await api(`/characters/${characterId}/inventory/${itemId}?quantity=1`, { method: 'DELETE' });
  message('Item removido do personagem.');
  await loadAdminInventory(characterId);
  if (state.selected?.id === characterId) await loadCharacterDetails();
}

function renderAdminUsers() {
  const isAdmin = state.user.role === 'ADMINISTRADOR';
  $('#admin-role-help').textContent = isAdmin
    ? 'Administradores podem transformar jogadores em Mestres e gerenciar os perfis das outras contas.'
    : 'Como Mestre, você pode consultar as contas. Somente um Administrador pode alterar perfis.';
  $('#admin-user-list').innerHTML = state.admin.users.length
    ? state.admin.users.map((user) => {
      const isSelf = user.id === state.user.id;
      const controls = isAdmin
        ? `<div class="role-control"><select id="admin-role-${escapeHtml(user.id)}" ${isSelf ? 'disabled' : ''}>
            ${['JOGADOR', 'MESTRE', 'ADMINISTRADOR'].map((role) => `<option value="${role}" ${role === user.role ? 'selected' : ''}>${formatEnum(role)}</option>`).join('')}
          </select><button class="button small" data-action="admin-save-role" data-id="${escapeHtml(user.id)}" ${isSelf ? 'disabled' : ''}>Salvar perfil</button></div>`
        : '';
      return `<article class="admin-record"><div class="admin-record-header"><div><strong>${escapeHtml(user.name)}${isSelf ? ' (você)' : ''}</strong>
        <p>${escapeHtml(user.email)} · ${formatEnum(user.role)}</p></div></div>${controls}</article>`;
    }).join('')
    : '<div class="admin-empty">Nenhum usuário cadastrado.</div>';
}

async function saveUserRole(userId) {
  if (state.user.role !== 'ADMINISTRADOR') throw new Error('Somente administradores podem alterar perfis.');
  const select = document.getElementById(`admin-role-${userId}`);
  if (!select) return;
  await api(`/admin/users/${userId}/role`, { method: 'PATCH', body: JSON.stringify({ role: select.value }) });
  message('Perfil atualizado com sucesso.');
  state.admin.users = await api('/admin/users');
  renderAdminUsers();
  renderAdminCharacters();
}

function catalogName(resource, id) { return state.catalogs[resource]?.find((item) => item.id === id)?.name ?? 'registro removido'; }
function getPath(object, path) { return path.split('.').reduce((value, key) => value?.[key], object); }

function setPath(object, path, value) {
  const keys = path.split('.');
  const last = keys.pop();
  const target = keys.reduce((current, key) => (current[key] ??= {}), object);
  target[last] = value;
}

function formatEnum(value) {
  return String(value ?? '').replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\p{L}/gu, (letter) => letter.toUpperCase());
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
}

if (state.token) enterGame().catch(() => {
  localStorage.removeItem('rpg-token');
  state.token = null;
});
