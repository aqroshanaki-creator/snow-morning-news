/**
 * Snow Morning News - アプリケーションロジック ＆ パスワード保護
 */

// 合言葉 "ramen0705" のSHA-256ハッシュ値
const AUTH_HASH = "a9496edb7e76fc1a0f5001e5a45085e2ba9ccb2daee12f1d12e30eca79fa6995";
const AUTH_STORAGE_KEY = "snow_news_auth_token";

document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  initTheme();
  registerServiceWorker();

  // リフレッシュボタン
  document.getElementById('refresh-btn').addEventListener('click', () => {
    loadNewsData(true);
  });

  // 再ロックボタン（フッター）
  const lockFooterBtn = document.getElementById('lock-btn-footer');
  if (lockFooterBtn) {
    lockFooterBtn.addEventListener('click', () => {
      lockApp();
    });
  }
});

/**
 * 文字列のSHA-256ハッシュを計算する（Web Crypto API）
 */
async function sha256(message) {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

/**
 * 認証・ロック画面の初期化
 */
function initAuth() {
  const lockScreen = document.getElementById('lock-screen');
  const appContent = document.getElementById('app-content');
  const lockForm = document.getElementById('lock-form');
  const passwordInput = document.getElementById('password-input');
  const lockError = document.getElementById('lock-error');
  const lockCard = document.querySelector('.lock-card');

  // 保存済みの認証トークンを確認
  const savedToken = localStorage.getItem(AUTH_STORAGE_KEY);
  if (savedToken === AUTH_HASH) {
    // 認証済み：ロック画面を隠してメインコンテンツを表示
    unlockApp(false);
    return;
  }

  // 未認証：ロック画面を表示
  lockScreen.classList.remove('hidden');
  appContent.style.display = 'none';

  // パスワード送信イベント
  lockForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const inputVal = passwordInput.value.trim();
    if (!inputVal) return;

    const inputHash = await sha256(inputVal);
    if (inputHash === AUTH_HASH) {
      // 認証成功：端末に保存してロック解除
      localStorage.setItem(AUTH_STORAGE_KEY, AUTH_HASH);
      lockError.textContent = '';
      unlockApp(true);
    } else {
      // 認証失敗：エラー表示＆シェイク
      lockError.textContent = '合言葉が違います (＞＜)';
      lockCard.classList.remove('lock-shake');
      void lockCard.offsetWidth; // リフロー発生
      lockCard.classList.add('lock-shake');
      passwordInput.value = '';
      passwordInput.focus();
    }
  });
}

/**
 * ロックを解除してニュースを表示
 */
function unlockApp(animate = false) {
  const lockScreen = document.getElementById('lock-screen');
  const appContent = document.getElementById('app-content');

  appContent.style.display = 'block';
  if (animate) {
    lockScreen.classList.add('hidden');
    setTimeout(() => {
      lockScreen.style.display = 'none';
    }, 300);
  } else {
    lockScreen.style.display = 'none';
    lockScreen.classList.add('hidden');
  }

  // ニュースデータのロード
  loadNewsData();
}

/**
 * 再びロックする
 */
function lockApp() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
  const lockScreen = document.getElementById('lock-screen');
  const appContent = document.getElementById('app-content');
  const passwordInput = document.getElementById('password-input');
  const lockError = document.getElementById('lock-error');

  passwordInput.value = '';
  lockError.textContent = '';
  lockScreen.style.display = 'flex';
  void lockScreen.offsetWidth;
  lockScreen.classList.remove('hidden');
  appContent.style.display = 'none';
  passwordInput.focus();
}

/**
 * ニュースデータの読み込みとレンダリング
 */
async function loadNewsData(forceRefresh = false) {
  const quoteElem = document.getElementById('daily-quote');
  const dateElem = document.getElementById('update-date');
  const timeElem = document.getElementById('update-time');
  const sakumaList = document.getElementById('sakuma-news-list');
  const snowmanList = document.getElementById('snowman-news-list');
  const scheduleSection = document.getElementById('schedule-section');
  const scheduleList = document.getElementById('schedule-list');
  const xbuzzSection = document.getElementById('xbuzz-section');
  const xbuzzList = document.getElementById('xbuzz-list');

  try {
    // キャッシュバスターを付与して最新のdata.jsonを取得
    const cacheBuster = forceRefresh ? `?t=${Date.now()}` : '';
    const res = await fetch(`./data.json${cacheBuster}`);
    if (!res.ok) {
      throw new Error(`HTTP error: ${res.status}`);
    }
    const data = await res.json();

    // 更新日時
    if (data.updated_at) {
      const parts = data.updated_at.split(' ');
      dateElem.textContent = parts[0] || '本日';
      timeElem.textContent = parts.slice(1).join(' ') || '';
    } else {
      dateElem.textContent = '最新情報';
    }

    // 今日のひとこと
    quoteElem.textContent = data.daily_quote || '今日も佐久間くんとSnow Manの元気をチャージして、良い一日を！✨';

    // 佐久間大介ニュース
    renderNewsCards(sakumaList, data.sakuma_news || [], '佐久間大介さんの新着ニュースは現在ありません。');

    // Snow Manニュース
    renderNewsCards(snowmanList, data.snowman_news || [], 'Snow Manの新着ニュースは現在ありません。');

    // 出演予定
    if (data.schedules && data.schedules.length > 0) {
      scheduleSection.style.display = 'block';
      scheduleList.innerHTML = data.schedules.map(item => `
        <article class="schedule-card">
          <p class="schedule-note">${escapeHtml(item.note || item.title)}</p>
          <div class="schedule-meta">
            <span class="news-source">${escapeHtml(item.source || '情報')}</span>
            <a href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer">詳細をみる →</a>
          </div>
        </article>
      `).join('');
    } else {
      scheduleSection.style.display = 'none';
    }

    // X話題
    if (data.x_buzz && data.x_buzz.length > 0) {
      xbuzzSection.style.display = 'block';
      xbuzzList.innerHTML = data.x_buzz.map(item => `
        <article class="xbuzz-card">
          <p class="xbuzz-text">${escapeHtml(item.buzz || item.title)}</p>
          <div class="xbuzz-meta">
            <span class="news-source">${escapeHtml(item.source || 'SNS反響')}</span>
            <a href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer">記事へ →</a>
          </div>
        </article>
      `).join('');
    } else {
      xbuzzSection.style.display = 'none';
    }

  } catch (err) {
    console.warn('ニュース読み込みに失敗しました:', err);
    quoteElem.textContent = 'オフラインまたはデータ取得中です。しばらくお待ちください。';
    sakumaList.innerHTML = '<div class="empty-placeholder">データがありません。毎朝6時に自動更新されます。</div>';
    snowmanList.innerHTML = '<div class="empty-placeholder">データがありません。毎朝6時に自動更新されます。</div>';
  }
}

/**
 * 配信日時のフォーマット（JST: MM/DD HH:mm）
 */
function formatArticleDate(dateStr) {
  if (!dateStr) return '';
  // すでに MM/DD HH:mm 形式の場合
  if (/^\d{1,2}\/\d{1,2}\s+\d{1,2}:\d{2}$/.test(dateStr.trim())) {
    return dateStr.trim();
  }
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${m}/${day} ${h}:${min}`;
  } catch (e) {
    return dateStr;
  }
}

/**
 * ニュースカードのレンダリング
 */
function renderNewsCards(container, items, emptyMessage) {
  if (!items || items.length === 0) {
    container.innerHTML = `<div class="empty-placeholder">${escapeHtml(emptyMessage)}</div>`;
    return;
  }

  container.innerHTML = items.map(item => {
    const yesterdayBadge = item.is_yesterday ? '<span class="badge-yesterday">昨日のニュース</span>' : '';
    const formattedDate = formatArticleDate(item.published);
    const pubDateHtml = formattedDate ? `<span class="news-pub-date">🕒 ${escapeHtml(formattedDate)}</span>` : '';

    return `
      <article class="news-card">
        <div class="card-header-meta">
          <div class="source-meta-left">
            <span class="news-source">${escapeHtml(item.source || 'ニュース')}</span>
            ${pubDateHtml}
          </div>
          ${yesterdayBadge}
        </div>
        <h3 class="news-title">${escapeHtml(item.title)}</h3>
        <p class="news-summary">${escapeHtml(item.summary)}</p>
        <a href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer" class="news-card-link">
          記事を読む ↗
        </a>
      </article>
    `;
  }).join('');
}

/**
 * テーマ（ダーク／ライト）切り替えの初期化
 */
function initTheme() {
  const toggleBtn = document.getElementById('theme-toggle');
  const savedTheme = localStorage.getItem('snow_theme');

  if (savedTheme === 'dark') {
    document.body.classList.add('dark-mode');
  } else if (savedTheme === 'light') {
    document.body.classList.add('light-mode');
  }

  toggleBtn.addEventListener('click', () => {
    const isDark = document.body.classList.contains('dark-mode') || 
      (!document.body.classList.contains('light-mode') && window.matchMedia('(prefers-color-scheme: dark)').matches);

    if (isDark) {
      document.body.classList.remove('dark-mode');
      document.body.classList.add('light-mode');
      localStorage.setItem('snow_theme', 'light');
    } else {
      document.body.classList.remove('light-mode');
      document.body.classList.add('dark-mode');
      localStorage.setItem('snow_theme', 'dark');
    }
  });
}

/**
 * Service Worker の登録
 */
function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js')
        .then(reg => console.log('Service Worker 登録成功:', reg.scope))
        .catch(err => console.log('Service Worker 登録スキップ/エラー:', err));
    });
  }
}

/**
 * XSS対策用のエスケープ関数
 */
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
