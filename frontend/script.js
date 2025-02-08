// モジュールスコープ変数
let currentUser = null;  // ログインユーザー名

// 状態管理用変数
const state = {
    currentComputerList: [],
    activeRequestId: null,
    statusPollingInterval: null
};

// DOM要素のキャッシュ
const domElements = {
    loginForm: document.getElementById('loginForm'),
    newRequestForm: document.getElementById('newRequestForm'),
    requestList: document.getElementById('requestList'),
    logoutBtn: document.getElementById('logoutBtn'),
    userInfo: document.getElementById('userInfo'),
    mainNav: document.getElementById('mainNav')
};

// ログイン処理
async function login(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    try {
        const response = await fetch(`${API_BASE_URL}/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
        });

        if (!response.ok) {
            throw new Error('ログインに失敗しました');
        }

        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('userRole', data.role);
        localStorage.setItem('username', username);
        currentUser = username;
        showLoggedInUI(data.role);
    } catch (error) {
        alert(error.message);
    }
}


// UI表示状態を管理
function showLoggedInUI(role) {
    const loginForm = document.getElementById('loginForm');
    const newRequestForm = document.getElementById('newRequestForm');
    const logoutBtn = document.getElementById('logoutBtn');
    const userInfo = document.getElementById('userInfo');
    const mainNav = document.getElementById('mainNav');
    
    if (loginForm) loginForm.classList.add('hidden');
    if (newRequestForm) newRequestForm.classList.remove('hidden');
    if (logoutBtn) logoutBtn.classList.remove('hidden');
    if (userInfo) {
        userInfo.textContent = `ログイン中: ${currentUser}`;
        userInfo.classList.remove('hidden');
    }
    if (mainNav) mainNav.classList.remove('hidden');
    
    // 管理者専用機能の制御
    const adminElements = document.querySelectorAll('.admin-only');
    adminElements.forEach(element => {
        if (role === 'admin') {
            element.classList.remove('hidden');
        } else {
            element.classList.add('hidden');
        }
    });
}

function showLoggedOutUI() {
    const loginForm = document.getElementById('loginForm');
    const newRequestForm = document.getElementById('newRequestForm');
    const requestList = document.getElementById('requestList');
    const logoutBtn = document.getElementById('logoutBtn');
    const userInfo = document.getElementById('userInfo');
    const mainNav = document.getElementById('mainNav');
    
    if (loginForm) loginForm.classList.remove('hidden');
    if (newRequestForm) newRequestForm.classList.add('hidden');
    if (requestList) requestList.classList.add('hidden');
    if (logoutBtn) logoutBtn.classList.add('hidden');
    if (userInfo) userInfo.classList.add('hidden');
    if (mainNav) mainNav.classList.add('hidden');
}
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('userRole');
    localStorage.removeItem('username');
    currentUser = null;
    showLoggedOutUI();
}
// トークンを取得
function getToken() {
    return localStorage.getItem('token');
}

// リフレッシュトークンを取得
function getRefreshToken() {
    return localStorage.getItem('refreshToken');
}

// トークンの有効期限をチェック
function isTokenExpired(token) {
    try {
        if (!token) return true;
        
        const payloadBase64 = token.split('.')[1];
        if (!payloadBase64) return true;
        
        const decodedJson = atob(payloadBase64);
        const payload = JSON.parse(decodedJson);
        
        // 追加の検証
        if (!payload.exp || typeof payload.exp !== 'number') return true;
        
        const now = Math.floor(Date.now() / 1000);
        const bufferTime = 60; // 有効期限の1分前から再発行を促す
        return now + bufferTime >= payload.exp;
    } catch (error) {
        console.error('トークン検証エラー:', error);
        return true;
    }
}

// トークンの更新
async function refreshToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        logout();
        throw new Error('セッションが無効になりました。再度ログインしてください。');
    }
    try {
        const response = await fetch(`${API_BASE_URL}/refresh-token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) {
            throw new Error('トークンの更新に失敗しました');
        }
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('refreshToken', data.refresh_token);
        return data.access_token;
    } catch (error) {
        console.error('[Token Refresh Error]:', {
            message: error.message,
            stack: error.stack
        });
        logout();
        throw new Error('トークンの更新に失敗しました。再度ログインしてください。');
    }
}

// 改善版APIリクエストラッパー
async function fetchWithToken(url, options = {}) {
    try {
        let token = getToken();
        
        // トークンの有効性チェックとリフレッシュ
        if (isTokenExpired(token)) {
            token = await refreshToken();
        }
        
        // リクエストヘッダーの構築
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...options.headers
        };
        
        // APIリクエストの実行
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        // エラーレスポンスのハンドリング
        if (!response.ok) {
            const errorData = await response.json();
            const errorMessage = errorData.message || 'APIリクエストに失敗しました';
            if (errorMessage.includes('トークン')) {
                console.error('認証エラー:', errorMessage);
                logout();
            }
            throw new Error(errorMessage);
        }
        return response;
    } catch (error) {
        throw error;
    }
}

// ページ読み込み時の処理
document.addEventListener('DOMContentLoaded', () => {
    // ログインフォームのイベントリスナー
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', login);
    }

    // ログアウトボタンのイベントリスナー
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    // CSVインポート関連のイベントリスナー
    const importCsvBtn = document.getElementById('importCsvBtn');
    if (importCsvBtn) {
        importCsvBtn.addEventListener('click', importCSV);
    }

    const downloadSampleCsvBtn = document.getElementById('downloadSampleCsvBtn');
    if (downloadSampleCsvBtn) {
        downloadSampleCsvBtn.addEventListener('click', downloadSampleCSV);
    }

    // ステップ間の移動のイベントリスナー
    const validateAndProceedBtn = document.getElementById('validateAndProceedBtn');
    if (validateAndProceedBtn) {
        validateAndProceedBtn.addEventListener('click', validateAndProceed);
    }

    const backToStep1Btn = document.getElementById('backToStep1Btn');
    if (backToStep1Btn) {
        backToStep1Btn.addEventListener('click', backToStep1);
    }

    const submitSetupBtn = document.getElementById('submitSetupBtn');
    if (submitSetupBtn) {
        submitSetupBtn.addEventListener('click', submitSetupRequest);
    }

    // モーダルのイベントリスナー
    const closeModalBtn = document.getElementById('closeModalBtn');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }

    // 認証状態の確認
    const token = getToken();
    const userRole = localStorage.getItem('userRole');
    if (token && userRole) {
        currentUser = localStorage.getItem('username');
        showLoggedInUI(userRole);
    } else {
        showLoggedOutUI();
    }
});

// ユーザー情報を取得
async function fetchUserInfo() {
    try {
        const response = await fetchWithToken(`${API_BASE_URL}/users/me`);
        const user = await response.json();
        currentUser = user.username;
        localStorage.setItem('username', user.username);
        localStorage.setItem('userRole', user.role);
        showLoggedInUI(user.role);
    } catch (error) {
        console.error('Error fetching user info:', error);
        showLoggedOutUI();
    }
}

// API呼び出し時のユーザーロールチェック
function checkUserRole(requiredRole) {
    const userRole = localStorage.getItem('userRole');
    if (requiredRole === 'admin' && userRole !== 'admin') {
        throw new Error('管理者権限が必要です');
    }
}

// 管理者専用ページへのアクセス制御
function showAdminPage() {
    try {
        checkUserRole('admin');
        // 管理者専用ページの表示処理
        console.log('管理者専用ページを表示');
    } catch (error) {
        alert(error.message);
    }
}

// デフォルト設定
const defaultSettings = {
    os: {
        setup_desktop_icons: true,
        move_vpn_icon: true,
        disable_ipv6: true,
        disable_defender: true,
        unpin_mail_store: true,
        setup_edge_defaults: true,
        set_edge_as_default: true,
        setup_default_mail: true,
        setup_default_pdf: true
    },
    office: {
        install_office: true,
        setup_office_auth: true,
        configure_office_apps: true
    },
    apps: {
        install_dvd_software: true,
        install_carbon_black: true,
        install_forticlient_vpn: true,
        install_ares_standard: true,
        install_apex_one: true,
        install_virus_buster: true
    },
    system: {
        update_office: true,
        update_windows: true,
        cleanup_system: true,
        restart_system: true
    }
};

// PC別の設定を保持するオブジェクト
let pcSettings = {};

// サンプルCSVのダウンロード
async function downloadSampleCSV() {
    try {
        const response = await fetch(`${API_BASE_URL}/sample-csv`);
        if (!response.ok) {
            throw new Error('サンプルファイルのダウンロードに失敗しました。');
        }

        // レスポンスをBlobとして取得
        const blob = await response.blob();
        
        // ダウンロードリンクを作成
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '登録ユーザ情報サンプル.csv';
        
        // リンクをクリックしてダウンロードを開始
        document.body.appendChild(a);
        a.click();
        
        // クリーンアップ
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        alert(error.message);
    }
}

// DOMが読み込まれたら実行
document.addEventListener('DOMContentLoaded', () => {
    // 初期状態でモーダルを非表示にする
    const modal = document.getElementById('statusModal');
    if (modal) {
        modal.classList.add('hidden');
    }

    // 一括選択チェックボックスのイベントリスナーを設定
    document.querySelectorAll('.select-all').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const group = e.target.dataset.group;
            const isChecked = e.target.checked;
            const container = e.target.closest('.option-group');
            
            // グループ内のすべてのチェックボックスを取得(一括選択チェックボックスを除く)
            const checkboxes = container.querySelectorAll('input[type="checkbox"]:not(.select-all)');
            
            // 各チェックボックスの状態を更新
            checkboxes.forEach(item => {
                item.checked = isChecked;
            });
        });
    });

    // 個別のチェックボックスの状態変更を監視
    document.querySelectorAll('.option-group').forEach(group => {
        const checkboxes = group.querySelectorAll('input[type="checkbox"]:not(.select-all)');
        const selectAll = group.querySelector('.select-all');

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                // グループ内のすべてのチェックボックスがチェックされているか確認
                const allChecked = Array.from(checkboxes).every(cb => cb.checked);
                selectAll.checked = allChecked;
            });
        });
    });

    // ナビゲーションボタンのイベントリスナー
    document.getElementById('newRequestBtn').addEventListener('click', showNewRequestForm);
    document.getElementById('requestListBtn').addEventListener('click', showRequestList);
    
    // フィルターのイベントリスナー
    document.getElementById('statusFilter').addEventListener('change', filterRequests);
    document.getElementById('requesterFilter').addEventListener('input', filterRequests);

    // モーダルの外側をクリックしたときに閉じる
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target.id === 'statusModal') {
                closeModal();
            }
        });

        // モーダルコンテンツのクリックイベントの伝播を停止
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }

        // モーダルの閉じるボタンのイベントリスナー
        const closeBtn = modal.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                closeModal();
            });
        }
    }
});

// 新規申請フォームの表示
function showNewRequestForm() {
    document.getElementById('newRequestForm').classList.remove('hidden');
    document.getElementById('requestList').classList.add('hidden');
    document.getElementById('newRequestBtn').classList.add('active');
    document.getElementById('requestListBtn').classList.remove('active');
}

// 申請一覧の表示
function showRequestList() {
    document.getElementById('newRequestForm').classList.add('hidden');
    document.getElementById('requestList').classList.remove('hidden');
    document.getElementById('newRequestBtn').classList.remove('active');
    document.getElementById('requestListBtn').classList.add('active');
    loadRequestList();
}

async function importCSV() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    const nextBtn = document.querySelector('.next-btn');
    const preview = document.getElementById('csvPreview');
    
    if (!file) {
        alert('CSVファイルを選択してください。');
        return;
    }

    console.log('CSVファイルを処理開始:', file.name);
    preview.innerHTML = '<div class="loading">CSVファイルを処理中...</div>';

    const formData = new FormData();
    formData.append('file', file);

    try {
        console.log('APIリクエスト送信:', `${API_BASE_URL}/setup/upload-csv`);
        const token = getToken();
        const response = await fetch(`${API_BASE_URL}/setup/upload-csv`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        console.log('APIレスポンス:', response.status);
        const responseText = await response.text();
        console.log('レスポンス内容:', responseText);

        if (!response.ok) {
            let errorMessage;
            try {
                const errorData = JSON.parse(responseText);
                errorMessage = errorData.detail;
            } catch {
                errorMessage = responseText;
            }
            
            preview.innerHTML = `
                <h3>CSVインポート結果</h3>
                <div class="import-status error">
                    <p>❌ インポートに失敗しました</p>
                    <p>エラー内容: ${errorMessage}</p>
                    <p>確認事項:</p>
                    <ul>
                        <li>CSVファイルの形式が正しいか確認してください</li>
                        <li>10行目以降にデータが存在するか確認してください</li>
                        <li>ログインタイプは「AD」「既存ローカル」「新規ローカル」のいずれかを指定してください</li>
                    </ul>
                </div>
            `;
            throw new Error(errorMessage);
        }

        const data = JSON.parse(responseText);
        console.log('パース済みデータ:', data);
        currentComputerList = data.computers;
        
        if (currentComputerList && currentComputerList.length > 0) {
            console.log('コンピュータリスト:', currentComputerList);
            displayComputerList(currentComputerList);
            nextBtn.classList.remove('hidden');
        } else {
            preview.innerHTML = `
                <h3>CSVインポート結果</h3>
                <div class="import-status error">
                    <p>❌ データが見つかりません</p>
                    <p>CSVファイルにデータが含まれていないか、6行目以降にデータが存在しません。</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('CSVインポートエラー:', error);
        if (!preview.innerHTML.includes('import-status')) {
            preview.innerHTML = `
                <h3>CSVインポート結果</h3>
                <div class="import-status error">
                    <p>❌ 予期せぬエラーが発生しました</p>
                    <p>エラー内容: ${error.message}</p>
                </div>
            `;
        }
    }
}

// 次のステップに進む
async function validateAndProceed() {
    if (currentComputerList.length === 0) {
        alert('先にCSVファイルをインポートしてください。');
        return;
    }
    
    // 選択されたPCの数を確認
    const selectedPCs = currentComputerList.filter(pc => pcSettings[pc.computer_name].selected);
    if (selectedPCs.length === 0) {
        alert('少なくとも1台のPCを選択してください。');
        return;
    }

    showStep2();
}

// コンピュータリストの表示
// コンピュータリストの表示
function displayComputerList(computers) {
    const preview = document.getElementById('csvPreview');
    if (!computers || computers.length === 0) {
        preview.innerHTML = '<div class="error">有効なデータが見つかりません。</div>';
        return;
    }

    // 各PCの初期設定を作成
    computers.forEach(pc => {
        if (!pcSettings[pc.computer_name]) {
            pcSettings[pc.computer_name] = {
                selected: true,
                hasCustomSettings: false,
                settings: JSON.parse(JSON.stringify(defaultSettings))
            };
        }
    });

    preview.innerHTML = `
        <h3>CSVインポート結果</h3>
        <div class="import-status success">
            <p>✅ 正常にインポートされました</p>
            <p>読み込まれたPC数: ${computers.length}台</p>
        </div>
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>選択</th>
                        <th>ホスト名</th>
                        <th>IPアドレス</th>
                        <th>ログイン種別</th>
                        <th>ADユーザ</th>
                        <th>ADパスワード</th>
                        <th>既存ローカルユーザ</th>
                        <th>既存ローカルユーザパスワード</th>
                        <th>フルネーム</th>
                        <th>新規ローカルユーザー名</th>
                        <th>新規ローカルユーザーパスワード</th>
                        <th>Administrator権限</th>
                    </tr>
                </thead>
                <tbody>
                    ${computers.map(pc => `
                        <tr>
                            <td>
                                <input type="checkbox" class="pc-select" data-pc-name="${pc.computer_name}"
                                    ${pcSettings[pc.computer_name].selected ? 'checked' : ''}>
                            </td>
                            <td><strong>${pc.computer_name}</strong></td>
                            <td>${pc.ip_address}</td>
                            <td><span class="login-type">${getLoginTypeText(pc.login_type)}</span></td>
                            <td>${pc.ad_username || '-'}</td>
                            <td>${pc.ad_password ? '********' : '-'}</td>
                            <td>${pc.local_existing_username || '-'}</td>
                            <td data-column="既存ローカルユーザパスワード">${pc.local_existing_password ? '********' : '-'}</td>
                            <td>${pc.full_name || '-'}</td>
                            <td data-column="新規ローカルユーザー名">${pc.local_new_username || '-'}</td>
                            <td data-column="新規ローカルユーザーパスワード">${pc.local_new_password ? '********' : '-'}</td>
                            <td><span class="admin-badge ${pc.admin_privilege ? 'yes' : 'no'}">${pc.admin_privilege ? 'Yes' : 'No'}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    // 次のステップボタンを表示
    const nextBtn = document.querySelector('.next-btn');
    if (nextBtn) {
        nextBtn.classList.remove('hidden');
    }

    // PCの選択状態の変更を監視
    document.querySelectorAll('.pc-select').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const pcName = e.target.dataset.pcName;
            pcSettings[pcName].selected = e.target.checked;
        });
    });
}
// ログイン種別の日本語表示
function getLoginTypeText(loginType) {
    const typeMap = {
        'AD': 'Active Directory',
        'LocalExisting': '既存ローカル',
        'LocalNew': '新規ローカル'
    };
    return typeMap[loginType] || loginType;
}

// ステップ2の表示
function showStep2() {
    document.getElementById('step1').classList.add('hidden');
    document.getElementById('step2').classList.remove('hidden');

    // PC一覧と設定セクションを表示
    const step2 = document.getElementById('step2');
    step2.innerHTML = `
        <h3>セットアップ対象PC</h3>
        <div class="pc-list">
            ${currentComputerList.map(pc => `
                <div class="pc-card ${pcSettings[pc.computer_name]?.hasCustomSettings ? 'has-custom-settings' : ''}" data-pc-name="${pc.computer_name}">
                    <div class="pc-card-header">
                        <label class="pc-select-label">
                            <input type="checkbox" class="pc-select" data-pc-name="${pc.computer_name}"
                                ${pcSettings[pc.computer_name]?.selected ? 'checked' : ''}>
                            <span class="pc-name">${pc.computer_name}</span>
                        </label>
                    </div>
                    <div class="pc-info">
                        <p>IPアドレス: ${pc.ip_address}</p>
                        <p>ログイン種別: ${getLoginTypeText(pc.login_type)}</p>
                    </div>
                    <div class="pc-settings-controls">
                        <button class="pc-settings-btn" onclick="showPCSettings('${pc.computer_name}')">個別設定</button>
                        ${pcSettings[pc.computer_name]?.hasCustomSettings ? `
                            <button class="view-settings-btn" onclick="viewPCSettings('${pc.computer_name}')">設定内容を確認</button>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
        <h3 class="common-settings-label">共通設定(個別設定がないPCに適用)</h3>
        <div class="setup-options">
            <div class="option-group">
                <div class="option-header">
                    <h4>OS設定</h4>
                    <label class="select-all-label">
                        <input type="checkbox" class="select-all" data-group="os">
                        一括選択
                    </label>
                </div>
                ${generateSettingsHTML(defaultSettings.os, 'os')}
            </div>
            <div class="option-group">
                <div class="option-header">
                    <h4>Microsoft 365</h4>
                    <label class="select-all-label">
                        <input type="checkbox" class="select-all" data-group="office">
                        一括選択
                    </label>
                </div>
                ${generateSettingsHTML(defaultSettings.office, 'office')}
            </div>
        </div>
        <div class="setup-options">
            <div class="option-group">
                <div class="option-header">
                    <h4>アプリケーションインストール</h4>
                    <label class="select-all-label">
                        <input type="checkbox" class="select-all" data-group="apps">
                        一括選択
                    </label>
                </div>
                ${generateSettingsHTML(defaultSettings.apps, 'apps')}
            </div>
            <div class="option-group">
                <div class="option-header">
                    <h4>システム更新</h4>
                    <label class="select-all-label">
                        <input type="checkbox" class="select-all" data-group="system">
                        一括選択
                    </label>
                </div>
                ${generateSettingsHTML(defaultSettings.system, 'system')}
            </div>
        </div>
        <div class="button-group">
            <button onclick="backToStep1()" class="back-btn">戻る</button>
            <button onclick="submitSetupRequest()" class="submit-btn">申請</button>
        </div>
    `;

    // イベントリスナーの設定
    setupEventListeners();
}

// 設定項目のHTML生成
function generateSettingsHTML(settings, group) {
    return Object.entries(settings).map(([key, value]) => `
        <label>
            <input type="checkbox"
                class="setting-checkbox"
                data-setting="${key}"
                data-group="${group}"
                ${value ? 'checked' : ''}>
            ${getSettingLabel(key)}
        </label>
    `).join('');
}

// イベントリスナーの設定
function setupEventListeners() {
    // PCの選択状態の変更を監視
    document.querySelectorAll('.pc-select').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const pcName = e.target.dataset.pcName;
            pcSettings[pcName].selected = e.target.checked;
        });
    });

    // 共通設定の一括選択チェックボックスの変更を監視
    document.querySelectorAll('.select-all').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const group = e.target.dataset.group;
            const isChecked = e.target.checked;
            const container = e.target.closest('.option-group');
            
            container.querySelectorAll(`input[type="checkbox"][data-group="${group}"]:not(.select-all)`).forEach(item => {
                item.checked = isChecked;
                const setting = item.dataset.setting;
                defaultSettings[group][setting] = isChecked;
            });
        });
    });

    // 共通設定の個別チェックボックスの変更を監視
    document.querySelectorAll('.setting-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const group = e.target.dataset.group;
            const setting = e.target.dataset.setting;
            defaultSettings[group][setting] = e.target.checked;
            
            // グループ内のすべてのチェックボックスの状態を確認
            const container = e.target.closest('.option-group');
            const checkboxes = container.querySelectorAll(`.setting-checkbox[data-group="${group}"]`);
            const selectAll = container.querySelector(`.select-all[data-group="${group}"]`);
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            selectAll.checked = allChecked;
        });
    });
}

// PC設定の表示
function viewPCSettings(pcName) {
    const settings = pcSettings[pcName];
    if (!settings) return;

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'pcSettingsViewModal';
    
    modal.innerHTML = `
        <div class="modal-content">
            <button onclick="closeViewPCSettings()" class="close-btn">&times;</button>
            <h2>${pcName}の設定内容</h2>
            <div class="settings-view-container">
                ${generateSettingsViewHTML(settings.settings)}
            </div>
            <div class="button-group">
                <button onclick="showPCSettings('${pcName}')" class="edit-btn">編集</button>
                <button onclick="closeViewPCSettings()" class="close-view-btn">閉じる</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

// 設定内容のHTML生成
function generateSettingsViewHTML(settings) {
    return Object.entries(settings).map(([group, groupSettings]) => `
        <div class="settings-group">
            <h3>${getGroupLabel(group)}</h3>
            <ul class="settings-list">
                ${Object.entries(groupSettings)
                    .filter(([_, value]) => value)
                    .map(([key, _]) => `
                        <li>${getSettingLabel(key)}</li>
                    `).join('')}
            </ul>
        </div>
    `).join('');
}

// グループラベルの取得
function getGroupLabel(group) {
    const labels = {
        os: 'OS設定',
        office: 'Microsoft 365',
        apps: 'アプリケーションインストール',
        system: 'システム更新'
    };
    return labels[group] || group;
}

// PC設定モーダルを閉じる
function closeViewPCSettings() {
    const modal = document.getElementById('pcSettingsViewModal');
    if (modal) {
        modal.remove();
    }
}

// ステップ1に戻る
function backToStep1() {
    document.getElementById('step2').classList.add('hidden');
    document.getElementById('step1').classList.remove('hidden');
}

// セットアップリクエストの送信
async function submitSetupRequest() {
    // 選択されたPCのみを抽出
    const selectedComputers = currentComputerList.filter(pc =>
        pcSettings[pc.computer_name] && pcSettings[pc.computer_name].selected
    );

    if (selectedComputers.length === 0) {
        alert('セットアップするPCが選択されていません。');
        return;
    }

    // 共通設定を取得(ステップ2の画面で設定された内容)
    const commonSettings = {};
    document.querySelectorAll('.setup-options input[type="checkbox"]').forEach(checkbox => {
        commonSettings[checkbox.name] = checkbox.checked;
    });

    // 各PCの設定を準備
    const computersWithSettings = selectedComputers.map(pc => ({
        ...pc,
        settings: pcSettings[pc.computer_name]?.settings || {
            os: commonSettings,
            office: commonSettings,
            apps: commonSettings,
            system: commonSettings
        }
    }));

    const formData = new FormData();
    formData.append('requester', currentUser);
    formData.append('computers_json', JSON.stringify(computersWithSettings));
    formData.append('options_json', JSON.stringify(commonSettings));

    try {
        const response = await fetchWithToken(`${API_BASE_URL}/setup/create`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'セットアップリクエストの作成に失敗しました。');
        }

        const data = await response.json();
        alert('セットアップリクエストを作成しました。\n申請ID: ' + data.request_id);
        showRequestList();
    } catch (error) {
        alert(error.message);
    }
}

// 申請一覧の読み込みと表示
async function loadRequestList() {
    try {
        const statusFilter = document.getElementById('statusFilter').value;
        const requesterFilter = document.getElementById('requesterFilter').value;

        let url = `${API_BASE_URL}/setup/list`;
        if (statusFilter) url += `?status=${statusFilter}`;
        if (requesterFilter) url += `${statusFilter ? '&' : '?'}requester=${requesterFilter}`;

        const response = await fetchWithToken(url);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '申請一覧の取得に失敗しました。');
        }

        const data = await response.json();
        displayRequestList(data.requests);
    } catch (error) {
        alert(error.message);
    }
}

// 申請一覧の表示
function displayRequestList(requests) {
    const container = document.getElementById('requestListContent');
    const userRole = localStorage.getItem('userRole');
    container.innerHTML = requests.map(request => `
        <div class="request-card">
            <div class="request-header">
                <span class="request-id">申請ID: ${request.request_id}</span>
                <span class="status-badge status-${request.status}">${getStatusText(request.status)}</span>
            </div>
            <div class="request-body">
                <p>申請者: ${request.requester}</p>
                <p>対象PC数: ${request.computers.length}</p>
                <p>申請日時: ${new Date(request.created_at).toLocaleString()}</p>
                ${userRole === 'admin' && request.status === 'pending' ? `
                    <button onclick="approveRequest('${request.request_id}')">承認</button>
                    <button onclick="rejectRequest('${request.request_id}')">却下</button>
                ` : ''}
                <button onclick="showStatus('${request.request_id}')">詳細</button>
            </div>
        </div>
    `).join('');
}

// ステータステキストの取得
function getStatusText(status) {
    const statusMap = {
        pending: '承認待ち',
        approved: '承認済み',
        rejected: '却下',
        in_progress: '実行中',
        completed: '完了',
        failed: '失敗',
        warning: '警告',
        skipped: 'スキップ',
        partially_failed: '一部失敗',
        rollback: 'ロールバック中',
        rollback_failed: 'ロールバック失敗'
    };
    return statusMap[status] || status;
}

// ステータスに応じたスタイルクラスを取得
function getStatusClass(status) {
    const classMap = {
        pending: 'status-pending',
        approved: 'status-approved',
        rejected: 'status-rejected',
        in_progress: 'status-in-progress',
        completed: 'status-completed',
        failed: 'status-failed',
        warning: 'status-warning',
        skipped: 'status-skipped',
        partially_failed: 'status-partially-failed',
        rollback: 'status-rollback',
        rollback_failed: 'status-rollback-failed'
    };
    return classMap[status.toLowerCase()] || '';
}

// エラーの重要度に応じたスタイルクラスを取得
function getSeverityClass(severity) {
    const classMap = {
        info: 'severity-info',
        warning: 'severity-warning',
        error: 'severity-error',
        critical: 'severity-critical'
    };
    return classMap[severity.toLowerCase()] || '';
}

// セットアップリクエストの承認
async function approveRequest(requestId) {
    try {
        checkUserRole('admin');
        if (!confirm('このセットアップリクエストを承認しますか?')) return;

        const response = await fetchWithToken(`${API_BASE_URL}/setup/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                request_id: requestId,
                approver: currentUser,
                approved: true
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '承認処理に失敗しました。');
        }

        loadRequestList();
    } catch (error) {
        alert(error.message);
    }
}

// セットアップリクエストの却下
async function rejectRequest(requestId) {
    try {
        checkUserRole('admin');
        const reason = prompt('却下理由を入力してください:');
        if (reason === null) return;

        const response = await fetchWithToken(`${API_BASE_URL}/setup/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                request_id: requestId,
                approver: currentUser,
                approved: false,
                rejection_reason: reason
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '却下処理に失敗しました。');
        }

        loadRequestList();
    } catch (error) {
        alert(error.message);
    }
}

// ステータス詳細の表示
async function showStatus(requestId) {
    try {
        const response = await fetchWithToken(`${API_BASE_URL}/setup/${requestId}/status`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'ステータス情報の取得に失敗しました。');
        }

        const data = await response.json();
        displayStatusModal(data, requestId);
    } catch (error) {
        alert(error.message);
    }
}

// ステータスモーダルの表示
function displayStatusModal(statusData, requestId) {
    if (!statusData || !requestId) return;

    const modal = document.getElementById('statusModal');
    const progressContainer = document.getElementById('progressContainer');
    const logContainer = document.getElementById('logContainer');

    // 全体の進捗状況
    const totalTime = statusData.actual_time ? Math.floor(statusData.actual_time / 60) : 0;
    progressContainer.innerHTML = `
        <h3>全体の進捗: ${Math.round(statusData.progress)}%</h3>
        <div class="progress-bar">
            <div class="progress-bar-fill" style="width: ${statusData.progress}%"></div>
        </div>
        <p class="time-info">経過時間: ${totalTime}分</p>
        <h3>PC別の進捗状況</h3>
        ${Object.entries(statusData.computer_progress || {}).map(([pc, progress]) => `
            <div class="pc-progress">
                <div class="pc-progress-header">
                    <p>${pc}</p>
                    <p class="progress-percentage">${Math.round(progress)}%</p>
                </div>
                <div class="progress-bar">
                    <div class="progress-bar-fill" style="width: ${progress}%"></div>
                </div>
            </div>
        `).join('')}
    `;

    // ログ表示
    logContainer.innerHTML = `
        <h3>実行ログ</h3>
        <div class="log-entries">
            ${(statusData.logs || []).map(log => {
                const duration = log.duration ? `(所要時間: ${log.duration}秒)` : '';
                const statusClass = getStatusClass(log.status);
                return `
                    <div class="log-entry ${statusClass}">
                        <div class="log-header">
                            <span class="log-timestamp">${new Date(log.timestamp).toLocaleString()}</span>
                            <span class="log-duration">${duration}</span>
                        </div>
                        <div class="log-content">
                            <span class="log-computer">${log.computer_name}</span>
                            <span class="log-task">${log.task_name}</span>
                            <span class="log-status status-badge status-${log.status.toLowerCase()}">${getStatusText(log.status)}</span>
                        </div>
                        <div class="log-message">${log.message}</div>
                        ${log.status === 'Failed' ? `
                            <div class="error-details">
                                <p class="error-title">エラー詳細:</p>
                                <pre class="error-message">${log.message}</pre>
                                ${log.resolution_steps ? `
                                    <p class="resolution-title">推奨される対処方法:</p>
                                    <ul class="resolution-steps">
                                        ${log.resolution_steps.map(step => `<li>${step}</li>`).join('')}
                                    </ul>
                                ` : ''}
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('')}
        </div>
    `;

    modal.classList.remove('hidden');
    activeRequestId = requestId;
    startStatusPolling();
}

// ステータスの定期更新
function startStatusPolling() {
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
    }
    statusPollingInterval = setInterval(() => {
        if (activeRequestId) showStatus(activeRequestId);
    }, 5000);
}

// モーダルを閉じる
function closeModal() {
    const modal = document.getElementById('statusModal');
    modal.classList.add('hidden');
    
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
        statusPollingInterval = null;
    }
    
    activeRequestId = null;
}

// PC別設定モーダルの表示
function showPCSettings(pcName) {
    const settings = pcSettings[pcName];
    if (!settings) return;

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'pcSettingsModal';
    
    modal.innerHTML = `
        <div class="modal-content">
            <button onclick="closePCSettings()" class="close-btn">&times;</button>
            <h2>${pcName}の個別設定</h2>
            <div class="pc-settings-container">
                <div class="option-group">
                    <div class="option-header">
                        <h3>OS設定</h3>
                        <label class="select-all-label">
                            <input type="checkbox" class="select-all" data-group="os" data-pc="${pcName}">
                            一括選択
                        </label>
                    </div>
                    ${generateSettingsHTML(settings.settings.os, 'os', pcName)}
                </div>

                <div class="option-group">
                    <div class="option-header">
                        <h3>Microsoft 365</h3>
                        <label class="select-all-label">
                            <input type="checkbox" class="select-all" data-group="office" data-pc="${pcName}">
                            一括選択
                        </label>
                    </div>
                    ${generateSettingsHTML(settings.settings.office, 'office', pcName)}
                </div>

                <div class="option-group">
                    <div class="option-header">
                        <h3>アプリケーションインストール</h3>
                        <label class="select-all-label">
                            <input type="checkbox" class="select-all" data-group="apps" data-pc="${pcName}">
                            一括選択
                        </label>
                    </div>
                    ${generateSettingsHTML(settings.settings.apps, 'apps', pcName)}
                </div>

                <div class="option-group">
                    <div class="option-header">
                        <h3>システム更新</h3>
                        <label class="select-all-label">
                            <input type="checkbox" class="select-all" data-group="system" data-pc="${pcName}">
                            一括選択
                        </label>
                    </div>
                    ${generateSettingsHTML(settings.settings.system, 'system', pcName)}
                </div>
            </div>
            <div class="button-group">
                <button onclick="savePCSettings('${pcName}')" class="save-btn">保存</button>
                <button onclick="closePCSettings()" class="cancel-btn">キャンセル</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    setupPCSettingsEventListeners(pcName);
}

// 設定項目のHTML生成
function generateSettingsHTML(settings, group, pcName) {
    return Object.entries(settings).map(([key, value]) => `
        <label>
            <input type="checkbox"
                class="setting-checkbox"
                data-setting="${key}"
                data-group="${group}"
                data-pc="${pcName}"
                ${value ? 'checked' : ''}>
            ${getSettingLabel(key)}
        </label>
    `).join('');
}

// 設定項目のラベル取得
function getSettingLabel(key) {
    const labels = {
        // OS設定
        setup_desktop_icons: 'デスクトップアイコンの表示設定',
        move_vpn_icon: 'インジケーター内のFortiClientVPNを横へ移動',
        disable_ipv6: 'IPv6の無効化',
        disable_defender: 'Windows Defenderファイアウォールの無効化',
        unpin_mail_store: 'Mail、Storeのピン留めを外す',
        setup_edge_defaults: 'Edgeのデフォルトサイト設定',
        set_edge_as_default: 'Edgeの既定のブラウザ設定',
        setup_default_mail: '既定のプログラム設定(メール、Webブラウザ)',
        setup_default_pdf: '既定のプログラム設定(.pdf、.pdx)',
        // Microsoft 365
        install_office: 'インストール(ODT使用)',
        setup_office_auth: '認証設定',
        configure_office_apps: 'アプリケーション設定',
        // アプリケーションインストール
        install_dvd_software: 'DVDソフトウェア',
        install_carbon_black: 'Carbon Black',
        install_forticlient_vpn: 'FortiClient VPN',
        install_ares_standard: 'ARES Standard',
        install_apex_one: 'TrendMicro ApexOne',
        install_virus_buster: 'TrendMicro ウィルスバスターCloud',
        // システム更新
        update_office: 'Microsoft 365 アップデート',
        update_windows: 'Windows Update',
        cleanup_system: 'システムクリーンアップ&ディスククリーンアップ',
        restart_system: '再起動'
    };
    return labels[key] || key;
}

// PC設定モーダルのイベントリスナー設定
function setupPCSettingsEventListeners(pcName) {
    const modal = document.getElementById('pcSettingsModal');
    
    // 一括選択チェックボックスのイベントリスナー
    modal.querySelectorAll('.select-all').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const group = e.target.dataset.group;
            const isChecked = e.target.checked;
            const container = e.target.closest('.option-group');
            
            container.querySelectorAll(`input[type="checkbox"][data-group="${group}"][data-pc="${pcName}"]:not(.select-all)`).forEach(item => {
                item.checked = isChecked;
                updatePCSetting(pcName, group, item.dataset.setting, isChecked);
            });
        });
    });

    // 個別のチェックボックスのイベントリスナー
    modal.querySelectorAll('.setting-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const group = e.target.dataset.group;
            const setting = e.target.dataset.setting;
            updatePCSetting(pcName, group, setting, e.target.checked);
            
            // グループ内のすべてのチェックボックスの状態を確認
            const container = e.target.closest('.option-group');
            const checkboxes = container.querySelectorAll(`.setting-checkbox[data-group="${group}"][data-pc="${pcName}"]`);
            const selectAll = container.querySelector(`.select-all[data-group="${group}"]`);
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            selectAll.checked = allChecked;
        });
    });
}

// PC設定の更新
function updatePCSetting(pcName, group, setting, value) {
    if (pcSettings[pcName] && pcSettings[pcName].settings[group]) {
        pcSettings[pcName].settings[group][setting] = value;
    }
}

// PC設定モーダルを閉じる
function closePCSettings() {
    const modal = document.getElementById('pcSettingsModal');
    if (modal) {
        modal.remove();
    }
}

// PC設定の保存
function savePCSettings(pcName) {
    pcSettings[pcName].hasCustomSettings = true;
    updatePCCardDisplay(pcName);
    closePCSettings();
}

// PC一覧の表示を更新
function updatePCCardDisplay(pcName) {
    const pcCard = document.querySelector(`.pc-card[data-pc-name="${pcName}"]`);
    if (pcCard) {
        pcCard.classList.add('has-custom-settings');
        const customSettingsInfo = pcCard.querySelector('.custom-settings-info');
        if (customSettingsInfo) {
            customSettingsInfo.innerHTML = `
                <p class="settings-status">✓ 個別設定済み</p>
                <button class="view-settings-btn" onclick="viewPCSettings('${pcName}')">設定内容を確認</button>
            `;
        } else {
            const newCustomSettingsInfo = document.createElement('div');
            newCustomSettingsInfo.className = 'custom-settings-info';
            newCustomSettingsInfo.innerHTML = `
                <p class="settings-status">✓ 個別設定済み</p>
                <button class="view-settings-btn" onclick="viewPCSettings('${pcName}')">設定内容を確認</button>
            `;
            pcCard.appendChild(newCustomSettingsInfo);
        }
    }
}

// フィルター適用
function filterRequests() {
    loadRequestList();
}