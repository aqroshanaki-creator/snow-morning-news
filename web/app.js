/**
 * Snow Morning News - アプリケーションロジック
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadNewsData();
  registerServiceWorker();

  // リフレッシュボタン
  document.getElementById('refresh-btn').addEventListener('click', () => {
    loadNewsData(true);
  });
});

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
 * ニュースカードのレンダリング
 */
function renderNewsCards(container, items, emptyMessage) {
  if (!items || items.length === 0) {
    container.innerHTML = `<div class="empty-placeholder">${escapeHtml(emptyMessage)}</div>`;
    return;
  }

  container.innerHTML = items.map(item => {
    const yesterdayBadge = item.is_yesterday ? '<span class="badge-yesterday">昨日のニュース</span>' : '';
    return `
      <article class="news-card">
        <div class="card-header-meta">
          <span class="news-source">${escapeHtml(item.source || 'ニュース')}</span>
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

