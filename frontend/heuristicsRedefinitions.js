// heuristicsRedefinitions.js
// ユーザー認証のためのヘルパー関数

function validateCredentials(username, password) {
    if (!username || !password) {
        throw new Error('ユーザー名とパスワードは必須です');
    }
    if (username.length < 3 || password.length < 6) {
        throw new Error('ユーザー名は3文字以上、パスワードは6文字以上で入力してください');
    }
    return true;
}

function generateToken(userId) {
    const payload = {
        userId,
        exp: Math.floor(Date.now() / 1000) + 3600, // 1時間有効
        role: 'user'
    };
    const secretKey = 'your-secret-key-here';
    
    // 以下は簡易的なトークン生成例(実際にはライブラリを使用するべきです)
    return btoa(JSON.stringify(payload));
}

// グローバルスコープで関数を公開
window.validateCredentials = validateCredentials;
window.generateToken = generateToken;