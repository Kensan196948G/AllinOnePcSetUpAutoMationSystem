// auth.js - 認証関連の処理
// auth.js - 認証関連の処理

const API_BASE_URL = '/api';

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
    if (!token) {
        return true;
    }
    const payloadBase64 = token.split('.')[1];
    const decodedJson = atob(payloadBase64);
    const payload = JSON.parse(decodedJson);
    const exp = payload.exp;
    const now = Math.floor(Date.now() / 1000);
    return now >= exp;
}

// トークンの更新
async function refreshToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        throw new Error('リフレッシュトークンがありません');
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
        console.error('トークン更新エラー:', error);
        logout();
        throw error;
    }
}

// ログイン処理
async function login() {
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
        currentUser = username;
        showLoggedInUI(data.role);
    } catch (error) {
        alert(error.message);
    }
}

// ログアウト処理
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('userRole');
    currentUser = null;
    showLoggedOutUI();
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
            throw new Error(errorData.message || 'APIリクエストに失敗しました');
        }

        return response;
        
    } catch (error) {
        // トークン関連エラーの場合、ログアウト処理
        if (error.message.includes('トークン')) {
            console.error('認証エラー:', error);
            logout();
        }
        throw error;
    }
}

// グローバルスコープで関数を公開
window.login = login;
window.logout = logout;
window.fetchWithToken = fetchWithToken;
window.getToken = getToken;
window.isTokenExpired = isTokenExpired;
window.refreshToken = refreshToken;