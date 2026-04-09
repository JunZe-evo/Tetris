const COLS = 10;
const ROWS = 20;
const BLOCK = 30;

const SHAPES = {
  I: [[1, 1, 1, 1]],
  O: [
    [1, 1],
    [1, 1],
  ],
  T: [
    [0, 1, 0],
    [1, 1, 1],
  ],
  S: [
    [0, 1, 1],
    [1, 1, 0],
  ],
  Z: [
    [1, 1, 0],
    [0, 1, 1],
  ],
  J: [
    [1, 0, 0],
    [1, 1, 1],
  ],
  L: [
    [0, 0, 1],
    [1, 1, 1],
  ],
};

const COLORS = {
  I: '#22d3ee',
  O: '#facc15',
  T: '#a855f7',
  S: '#4ade80',
  Z: '#f43f5e',
  J: '#3b82f6',
  L: '#fb923c',
};

const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
ctx.scale(BLOCK, BLOCK);

const scoreNode = document.getElementById('score');
const levelNode = document.getElementById('level');
const linesNode = document.getElementById('lines');
const comboNode = document.getElementById('combo');
const speedTextNode = document.getElementById('speedText');
const speedControl = document.getElementById('speedControl');
const fxNode = document.getElementById('fxText');
const pauseBtn = document.getElementById('pauseBtn');
const startBtn = document.getElementById('startBtn');

let audioCtx;

const state = {
  board: createBoard(),
  active: null,
  lastDrop: 0,
  speed: 850,
  baseSpeed: 850,
  speedMultiplier: 1,
  score: 0,
  lines: 0,
  level: 1,
  combo: 0,
  flash: 0,
  shake: 0,
  fxText: '',
  fxTimer: 0,
  gameOver: false,
  paused: false,
};

function recalcSpeed() {
  state.baseSpeed = Math.max(120, 850 - (state.level - 1) * 70);
  state.speed = Math.max(60, state.baseSpeed / state.speedMultiplier);
  speedTextNode.textContent = `${state.speedMultiplier.toFixed(1)}x`;
}

function createBoard() {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(null));
}

function randomType() {
  return Object.keys(SHAPES)[Math.floor(Math.random() * 7)];
}

function spawnPiece() {
  const type = randomType();
  const shape = SHAPES[type].map((row) => [...row]);
  const piece = {
    type,
    shape,
    x: Math.floor(COLS / 2) - Math.ceil(shape[0].length / 2),
    y: -1,
  };

  if (collides(piece)) {
    state.gameOver = true;
    playTone(140, 0.25, 'sawtooth');
  }
  state.active = piece;
}

function rotate(shape) {
  return shape[0].map((_, i) => shape.map((row) => row[i]).reverse());
}

function collides(piece) {
  return piece.shape.some((row, y) =>
    row.some((cell, x) => {
      if (!cell) return false;
      const nx = piece.x + x;
      const ny = piece.y + y;
      if (nx < 0 || nx >= COLS || ny >= ROWS) return true;
      if (ny < 0) return false;
      return state.board[ny][nx];
    })
  );
}

function mergePiece() {
  state.active.shape.forEach((row, y) => {
    row.forEach((cell, x) => {
      if (!cell) return;
      const ny = state.active.y + y;
      if (ny >= 0) {
        state.board[ny][state.active.x + x] = state.active.type;
      }
    });
  });
}

function showFx(text, ms = 900) {
  state.fxText = text;
  state.fxTimer = ms;
  fxNode.textContent = text;
  fxNode.classList.add('show');
}

function clearLines() {
  let cleared = 0;
  for (let y = ROWS - 1; y >= 0; y--) {
    if (state.board[y].every(Boolean)) {
      state.board.splice(y, 1);
      state.board.unshift(Array(COLS).fill(null));
      cleared++;
      y++;
    }
  }

  if (cleared > 0) {
    state.lines += cleared;
    state.combo += 1;
    const baseScore = [0, 100, 300, 500, 800][cleared] * state.level;
    const comboBonus = Math.max(0, state.combo - 1) * 50 * state.level;
    state.score += baseScore + comboBonus;
    state.level = Math.floor(state.lines / 10) + 1;
    recalcSpeed();
    state.flash = 190;
    state.shake = Math.min(10, 2 + cleared * 2 + state.combo);

    if (state.combo >= 2) {
      showFx(`COMBO x${state.combo}`);
    } else {
      showFx(cleared === 4 ? 'TETRIS!' : `+${baseScore}`);
    }

    playTone(420 + cleared * 90, 0.08 + cleared * 0.03);
  } else {
    state.combo = 0;
  }

  updateStats();
  return cleared;
}

function updateStats() {
  scoreNode.textContent = state.score;
  levelNode.textContent = state.level;
  linesNode.textContent = state.lines;
  comboNode.textContent = state.combo;
}

function drawCell(x, y, color, alpha = 1) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = color;
  ctx.fillRect(x, y, 1, 1);
  ctx.strokeStyle = 'rgba(15, 23, 42, 0.8)';
  ctx.lineWidth = 0.05;
  ctx.strokeRect(x, y, 1, 1);
  ctx.restore();
}

function getGhostY(piece) {
  const ghost = { ...piece };
  while (!collides(ghost)) {
    ghost.y += 1;
  }
  return ghost.y - 1;
}

function applyShake() {
  if (state.shake <= 0) {
    canvas.style.transform = 'translate(0, 0)';
    return;
  }
  const x = (Math.random() * 2 - 1) * state.shake;
  const y = (Math.random() * 2 - 1) * state.shake;
  canvas.style.transform = `translate(${x}px, ${y}px)`;
}

function draw() {
  applyShake();

  ctx.fillStyle = '#020617';
  ctx.fillRect(0, 0, COLS, ROWS);

  state.board.forEach((row, y) => {
    row.forEach((type, x) => {
      if (type) drawCell(x, y, COLORS[type]);
    });
  });

  if (state.active) {
    const ghostY = getGhostY(state.active);
    state.active.shape.forEach((row, y) => {
      row.forEach((cell, x) => {
        if (!cell) return;
        drawCell(state.active.x + x, ghostY + y, COLORS[state.active.type], 0.18);
      });
    });

    state.active.shape.forEach((row, y) => {
      row.forEach((cell, x) => {
        if (cell) drawCell(state.active.x + x, state.active.y + y, COLORS[state.active.type]);
      });
    });
  }

  if (state.flash > 0) {
    ctx.fillStyle = `rgba(255, 255, 255, ${state.flash / 1000})`;
    ctx.fillRect(0, 0, COLS, ROWS);
  }

  if (state.gameOver) {
    ctx.fillStyle = 'rgba(2, 6, 23, 0.75)';
    ctx.fillRect(0, 0, COLS, ROWS);
    ctx.fillStyle = '#f8fafc';
    ctx.font = '0.9px sans-serif';
    ctx.fillText('游戏结束', 2.8, 9.5);
    ctx.fillText('点击重新开始', 1.8, 11);
  }
}

function settlePiece() {
  mergePiece();
  clearLines();
  spawnPiece();
}

function move(dx, dy) {
  if (!state.active || state.gameOver) return false;
  const next = { ...state.active, x: state.active.x + dx, y: state.active.y + dy };

  if (!collides(next)) {
    state.active = next;
    return true;
  }

  if (dy === 1) {
    settlePiece();
  }
  return false;
}

function hardDrop() {
  if (!state.active || state.gameOver) return;
  let dropped = 0;
  while (move(0, 1)) {
    dropped += 1;
  }
  if (dropped > 0) {
    state.score += dropped * 2;
    state.shake = Math.min(8, 2 + Math.floor(dropped / 2));
    playTone(240 + dropped * 8, 0.06, 'triangle');
    updateStats();
  }
}

function doRotate() {
  if (!state.active || state.gameOver) return;
  const rotated = rotate(state.active.shape);
  const tries = [0, -1, 1, -2, 2];

  for (const offset of tries) {
    const candidate = { ...state.active, shape: rotated, x: state.active.x + offset };
    if (!collides(candidate)) {
      state.active = candidate;
      playTone(300, 0.03, 'square');
      return;
    }
  }
}

function playTone(freq, duration = 0.05, wave = 'sine') {
  if (!audioCtx) return;

  const now = audioCtx.currentTime;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();

  osc.type = wave;
  osc.frequency.value = freq;

  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.05, now + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.start(now);
  osc.stop(now + duration + 0.01);
}

function tick(ts = 0) {
  if (!state.paused && !state.gameOver) {
    if (ts - state.lastDrop > state.speed) {
      move(0, 1);
      state.lastDrop = ts;
    }

    state.flash = Math.max(0, state.flash - 12);
    state.shake = Math.max(0, state.shake - 0.35);
  }

  if (state.fxTimer > 0) {
    state.fxTimer -= 16;
    if (state.fxTimer <= 0) {
      fxNode.classList.remove('show');
      state.fxText = '';
      fxNode.textContent = '';
    }
  }

  draw();
  requestAnimationFrame(tick);
}

function restart() {
  state.board = createBoard();
  state.score = 0;
  state.lines = 0;
  state.level = 1;
  state.combo = 0;
  state.baseSpeed = 850;
  state.speed = 850;
  state.speedMultiplier = Number(speedControl.value) || 1;
  state.lastDrop = 0;
  state.flash = 0;
  state.shake = 0;
  state.gameOver = false;
  state.paused = false;
  pauseBtn.textContent = '暂停';
  startBtn.textContent = '开始/继续';
  fxNode.classList.remove('show');
  updateStats();
  recalcSpeed();
  spawnPiece();
}

function ensureAudioUnlocked() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

function bindControls() {
  document.addEventListener('keydown', (e) => {
    ensureAudioUnlocked();
    if (state.gameOver) return;
    if (e.key.toLowerCase() === 'p') {
      state.paused = !state.paused;
      pauseBtn.textContent = state.paused ? '继续' : '暂停';
      return;
    }
    if (e.key === 'Enter') {
      state.paused = false;
      pauseBtn.textContent = '暂停';
      return;
    }
    if (state.paused) return;
    if (e.key === 'ArrowLeft') move(-1, 0);
    if (e.key === 'ArrowRight') move(1, 0);
    if (e.key === 'ArrowDown') move(0, 1);
    if (e.key === 'ArrowUp') doRotate();
    if (e.key === ' ') {
      e.preventDefault();
      hardDrop();
    }
  });

  const actionMap = {
    left: () => move(-1, 0),
    right: () => move(1, 0),
    down: () => move(0, 1),
    rotate: () => doRotate(),
    drop: () => hardDrop(),
  };

  document.querySelectorAll('[data-action]').forEach((btn) => {
    btn.addEventListener('pointerdown', (event) => {
      event.preventDefault();
      ensureAudioUnlocked();
      const action = btn.dataset.action;
      actionMap[action]?.();
      btn.setPointerCapture(event.pointerId);
    });
  });

  document.getElementById('restartBtn').addEventListener('click', () => {
    ensureAudioUnlocked();
    restart();
  });

  startBtn.addEventListener('click', () => {
    ensureAudioUnlocked();
    if (state.gameOver) restart();
    state.paused = false;
    pauseBtn.textContent = '暂停';
  });

  pauseBtn.addEventListener('click', () => {
    if (state.gameOver) return;
    state.paused = !state.paused;
    pauseBtn.textContent = state.paused ? '继续' : '暂停';
  });

  speedControl.addEventListener('input', () => {
    state.speedMultiplier = Number(speedControl.value) || 1;
    recalcSpeed();
    showFx(`速度 ${state.speedMultiplier.toFixed(1)}x`, 500);
  });
}

bindControls();
restart();
requestAnimationFrame(tick);
