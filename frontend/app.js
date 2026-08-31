const $ = (id) => document.getElementById(id);

function showMessage(el, text, isError = false) {
    el.textContent = text;
    el.classList.toggle("error", Boolean(text) && isError);
}

async function api(action, method = "GET", body = null) {
    const options = { method, headers: {} };
    if (body !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }
    const res = await fetch(`/?action=${action}`, options);
    const data = await res.json().catch(() => ({}));
    return { status: res.status, data };
}

async function checkSession() {
    const { data } = await api("me");
    if (data.ok) {
        enterApp(data.nama, data.username);
    } else {
        showAuth();
    }
}

function enterApp(nama, username) {
    $("session-info").textContent = `Sesi aktif: ${nama} (@${username})`;
    $("btn-logout").classList.remove("hidden");
    $("auth-panel").classList.add("hidden");
    $("app-panel").classList.remove("hidden");
    loadPuisi();
}

function showAuth() {
    $("session-info").textContent = "Belum login";
    $("btn-logout").classList.add("hidden");
    $("auth-panel").classList.remove("hidden");
    $("app-panel").classList.add("hidden");
    $("tabel-puisi").querySelector("tbody").replaceChildren();
}

async function login(e) {
    e.preventDefault();
    showMessage($("auth-message"), "");
    const { status, data } = await api("login", "POST", {
        username: $("login-username").value,
        password: $("login-password").value,
    });
    if (status === 200 && data.ok) {
        $("form-login").reset();
        enterApp(data.nama, data.username);
    } else {
        showMessage($("auth-message"), data.message || "Login gagal", true);
    }
}

async function register(e) {
    e.preventDefault();
    showMessage($("auth-message"), "");
    const { status, data } = await api("register", "POST", {
        username: $("reg-username").value,
        nama: $("reg-nama").value,
        password: $("reg-password").value,
    });
    if (status === 201 && data.ok) {
        $("form-register").reset();
        showMessage($("auth-message"), data.message + ". Silakan login.", false);
        switchTab("login");
    } else {
        showMessage($("auth-message"), data.message || "Register gagal", true);
    }
}

async function logout() {
    await api("logout", "POST");
    showAuth();
    showMessage($("auth-message"), "Anda telah logout.", false);
}

async function submitPuisi(e) {
    e.preventDefault();
    showMessage($("puisi-message"), "");
    const { status, data } = await api("submit_puisi", "POST", {
        judul: $("puisi-judul").value,
        kategori: $("puisi-kategori").value,
        keyword: $("puisi-keyword").value,
        isi: $("puisi-isi").value,
    });
    if (status === 201 && data.ok) {
        $("form-puisi").reset();
        showMessage($("puisi-message"), data.message, false);
        loadPuisi();
    } else {
        showMessage($("puisi-message"), data.message || "Gagal mengirim puisi", true);
        if (status === 401) showAuth();
    }
}

async function loadPuisi() {
    const { status, data } = await api("daftar_puisi");
    if (status === 200 && data.ok) {
        const tbody = $("tabel-puisi").querySelector("tbody");
        tbody.replaceChildren();
        for (const p of data.puisi) {
            const tr = document.createElement("tr");
            for (const key of ["tgl_submit", "judul", "kategori", "keyword", "isi"]) {
                const td = document.createElement("td");
                td.textContent = p[key] ?? "-";
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        }
        if (data.puisi.length === 0) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");
            td.colSpan = 5;
            td.textContent = "Belum ada puisi. Unggah puisi pertama Anda!";
            td.className = "empty";
            tr.appendChild(td);
            tbody.appendChild(tr);
        }
        return true;
    } else if (status === 401) {
        showAuth();
    }
    return false;
}

function flashMessage() {
    const message = $("puisi-message");
    showMessage(message, "Daftar puisi diperbarui.");
    message.classList.remove("flash");
    void message.offsetWidth;
    message.classList.add("flash");
    setTimeout(() => message.classList.remove("flash"), 900);
}

async function refreshPuisi() {
    const button = $("btn-refresh");
    button.disabled = true;
    button.textContent = "Memuat...";
    try {
        if (await loadPuisi()) flashMessage();
    } finally {
        button.disabled = false;
        button.textContent = "Muat Ulang";
    }
}

function switchTab(name) {
    const isLogin = name === "login";
    $("tab-login").classList.toggle("active", isLogin);
    $("tab-register").classList.toggle("active", !isLogin);
    $("form-login").classList.toggle("hidden", !isLogin);
    $("form-register").classList.toggle("hidden", isLogin);
}

$("tab-login").addEventListener("click", () => switchTab("login"));
$("tab-register").addEventListener("click", () => switchTab("register"));
$("form-login").addEventListener("submit", login);
$("form-register").addEventListener("submit", register);
$("btn-logout").addEventListener("click", logout);
$("form-puisi").addEventListener("submit", submitPuisi);
$("btn-refresh").addEventListener("click", refreshPuisi);

checkSession();
