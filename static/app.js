let idToken = localStorage.getItem('id_token') || null;
let accessToken = localStorage.getItem('access_token') || null;

document.addEventListener('DOMContentLoaded', () => {
    if (idToken && accessToken) {
        updateUIWithProfile(idToken);
    }
});

// View Toggle Controls
document.getElementById('showRegisterBtn').addEventListener('click', () => {
    document.getElementById('loginCard').style.display = 'none';
    document.getElementById('registerCard').style.display = 'block';
});

document.getElementById('showLoginBtn').addEventListener('click', () => {
    document.getElementById('registerCard').style.display = 'none';
    document.getElementById('loginCard').style.display = 'block';
});

// 1. HANDLE REGISTER
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const msgDiv = document.getElementById('registerMsg');
    msgDiv.className = '';
    msgDiv.textContent = '';

    const payload = {
        full_name: document.getElementById('regFullName').value,
        email: document.getElementById('regEmail').value,
        username: document.getElementById('regUsername').value,
        password: document.getElementById('regPassword').value
    };

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Registration failed');

        msgDiv.className = 'success';
        msgDiv.textContent = 'Registration successful! Switching to login...';

        setTimeout(() => {
            document.getElementById('registerCard').style.display = 'none';
            document.getElementById('loginCard').style.display = 'block';
            msgDiv.textContent = '';
            document.getElementById('registerForm').reset();
        }, 1200);

    } catch (err) {
        msgDiv.className = 'error';
        msgDiv.textContent = err.message;
    }
});

// 2. HANDLE LOGIN
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const msgDiv = document.getElementById('loginMsg');
    msgDiv.className = '';
    msgDiv.textContent = '';

    const formData = new URLSearchParams();
    formData.append('username', document.getElementById('loginUsername').value);
    formData.append('password', document.getElementById('loginPassword').value);

    try {
        const response = await fetch('/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Invalid login');

        localStorage.setItem('id_token', data.id_token);
        localStorage.setItem('access_token', data.access_token);

        idToken = data.id_token;
        accessToken = data.access_token;

        document.getElementById('loginForm').reset();
        updateUIWithProfile(idToken);

    } catch (err) {
        msgDiv.className = 'error';
        msgDiv.textContent = err.message;
    }
});

// 3. HANDLE LOGOUT
document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('id_token');
    localStorage.removeItem('access_token');

    idToken = null;
    accessToken = null;

    document.getElementById('profileCard').style.display = 'none';
    document.getElementById('loginCard').style.display = 'block';
    document.getElementById('apiResult').textContent = 'Enter a prompt above and click "Run LangGraph Agent"...';
});

// 4. RUN LANGGRAPH AGENT
document.getElementById('runAgentBtn').addEventListener('click', async () => {
    if (!accessToken) return alert("Please log in first!");

    const promptText = document.getElementById('agentPrompt').value.trim();
    if (!promptText) return alert("Please enter a prompt!");

    const resultBox = document.getElementById('apiResult');
    resultBox.textContent = "Agent thinking...";

    try {
        const response = await fetch('/api/agent', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt: promptText })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to query agent');

        resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
        resultBox.textContent = `Error: ${err.message}`;
    }
});

// Helper: Decode JWT
function parseJwt(token) {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
}

// Helper: Show profile view
function updateUIWithProfile(tokenStr) {
    try {
        const payload = parseJwt(tokenStr);
        document.getElementById('userName').textContent = payload.name;
        document.getElementById('userEmail').textContent = payload.email;
        document.getElementById('userId').textContent = payload.sub;

        document.getElementById('loginCard').style.display = 'none';
        document.getElementById('registerCard').style.display = 'none';
        document.getElementById('profileCard').style.display = 'block';
    } catch (e) {
        console.error("Token parse error:", e);
    }
}
