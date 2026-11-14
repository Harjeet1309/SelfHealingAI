from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import os

from .middleware import MetricsMiddleware
from .routes import router, products

app = FastAPI(title="LUXE AI - Autonomous Boutique")
app.add_middleware(MetricsMiddleware)
app.include_router(router)

app.mount("/static", StaticFiles(directory="/app/app/static", html=True), name="static")

# --- LUXE DESIGN SYSTEM ---

def get_luxury_css(state):
    status_color = "#00e676" if state["status"] == "HEALTHY" else ("#ff9100" if state["status"] == "DEGRADED" else "#ff3d00")
    status_bg = "rgba(0, 230, 118, 0.1)" if state["status"] == "HEALTHY" else ("rgba(255, 145, 0, 0.1)" if state["status"] == "DEGRADED" else "rgba(255, 61, 0, 0.1)")
    
    return f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg: #0c0c0c;
            --accent: #d4af37;
            --text: #ffffff;
            --secondary-text: #888;
            --card-bg: #141414;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: var(--bg); color: var(--text); font-family: 'Outfit', sans-serif; min-height: 100vh; }}
        h1, h2, h3 {{ font-family: 'Playfair Display', serif; letter-spacing: 0.5px; }}

        nav {{
            height: 90px;
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 6%; border-bottom: 1px solid rgba(255,255,255,0.05);
            background: rgba(12, 12, 12, 0.8); backdrop-filter: blur(20px);
            position: sticky; top: 0; z-index: 1000;
        }}

        .logo {{ font-size: 1.8rem; font-weight: 800; text-decoration: none; color: white; display: flex; align-items: center; gap: 10px; }}
        .logo .dot {{ width: 8px; height: 8px; background: var(--accent); border-radius: 50%; }}

        .nav-links {{ display: flex; gap: 30px; }}
        .nav-links a {{ color: var(--secondary-text); text-decoration: none; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 2px; font-weight: 600; transition: 0.3s; }}
        .nav-links a:hover, .nav-links a.active {{ color: var(--accent); }}

        .status-badge {{
            padding: 6px 16px; border-radius: 20px; font-size: 0.7rem; font-weight: 700;
            display: flex; align-items: center; gap: 8px;
            background: {status_bg}; border: 1px solid {status_color}33; color: {status_color};
            text-transform: uppercase; letter-spacing: 1px;
        }}

        .container {{ padding: 60px 6%; max-width: 1600px; margin: 0 auto; }}

        .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; }}
        @media (max-width: 1200px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}

        .item-card {{ background: var(--card-bg); border-radius: 4px; overflow: hidden; transition: 0.5s; cursor: pointer; border: 1px solid rgba(255,255,255,0.02); }}
        .item-card:hover {{ transform: translateY(-8px); border-color: var(--accent); }}
        .item-img-container {{ width: 100%; aspect-ratio: 3/4; overflow: hidden; }}
        .item-img {{ width: 100%; height: 100%; object-fit: cover; filter: grayscale(0.2); transition: 0.6s; }}
        .item-card:hover .item-img {{ filter: grayscale(0); transform: scale(1.05); }}

        .btn {{ 
            background: transparent; border: 1px solid rgba(212, 175, 55, 0.4); 
            color: var(--accent); padding: 12px 25px; font-size: 0.75rem; text-transform: uppercase; 
            letter-spacing: 2px; font-weight: 700; cursor: pointer; transition: 0.3s; text-decoration: none; display: inline-block; 
        }}
        .btn:hover {{ background: var(--accent); color: black; }}

        .healing-overlay {{
            position: fixed; inset: 0; background: #0c0c0c; z-index: 10000;
            display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
        }}

        /* Performance Stats Styling */
        .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; margin-bottom: 50px; }}
        .stat-card {{ background: var(--card-bg); padding: 30px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); text-align: center; }}
        .stat-value {{ font-size: 3rem; font-weight: 800; color: var(--accent); margin-bottom: 10px; }}
        .stat-label {{ color: var(--secondary-text); text-transform: uppercase; letter-spacing: 1px; font-size: 0.8rem; }}
        
        .chart-container {{ background: var(--card-bg); padding: 40px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: space-around; }}
        canvas {{ max-width: 400px !important; max-height: 400px !important; }}
    </style>
    """

def get_base_layout(content, state, active_tab="home", page_faults=None):
    """
    page_faults: list of fault codes relevant to THIS page.
    If given, the healing overlay only shows when the active fault
    matches one of those codes. This prevents the 500 overlay from
    showing on the /cart page when a checkout fault (500) is active.
    e.g. cart page passes page_faults=[503]
         checkout page passes page_faults=[500]
         payment page passes page_faults=[504]
    """
    overlay = ""
    active_code = state.get("code")
    show_overlay = (
        state["status"] == "FAULT" and
        (page_faults is None or active_code in page_faults)
    )
    if show_overlay:
        overlay = f"""
        <div class="healing-overlay">
            <h1 style="font-size: 8rem; color: #ff3d00;">{state["code"]}</h1>
            <p style="font-size: 1.5rem; letter-spacing: 3px; color: #aaa;">CRITICAL DISRUPTION IDENTIFIED</p>
            <div style="width: 300px; height: 1px; background: rgba(255,255,255,0.1); margin: 40px 0; overflow: hidden; position: relative;">
                <div style="width: 40%; height: 100%; background: var(--accent); position: absolute; left: -40%; animation: move 2s infinite;"></div>
            </div>
            <p style="color: var(--accent); text-transform: uppercase; letter-spacing: 4px; font-size: 0.7rem;">AI_ENGINE: SELF-HEALING IN PROGRESS</p>
        </div>
        <script>setTimeout(() => location.reload(), 4000);</script>
        <style>@keyframes move {{ 0% {{ left: -40%; }} 100% {{ left: 100%; }} }}</style>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>LUXE AI | Autonomous Boutique</title>
        {get_luxury_css(state)}
    </head>
    <body>
        <nav>
            <a href="/" class="logo"><div class="dot"></div> LUXE AI</a>
            <div class="nav-links">
                <a href="/" class="{'active' if active_tab == 'home' else ''}">Boutique</a>
                <a href="/dashboard" class="{'active' if active_tab == 'dashboard' else ''}">Dashboard</a>
            </div>
            <div class="status-badge"><span>{state["message"]}</span></div>
        </nav>
        {overlay if state["status"] == "FAULT" else ""}
        <div class="container">{content}</div>
        <script>
            function showFaultOverlay(code) {{
                const ov = document.createElement('div');
                ov.style.cssText = 'position:fixed;inset:0;background:#0c0c0c;z-index:10000;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;';
                ov.innerHTML = `
                    <h1 style="font-size:8rem;color:#ff3d00;margin:0;font-family:monospace;">${{code}}</h1>
                    <p style="font-size:1.5rem;letter-spacing:3px;color:#aaa;margin:20px 0;">CRITICAL DISRUPTION IDENTIFIED</p>
                    <div style="width:300px;height:1px;background:rgba(255,255,255,0.1);margin:30px 0;overflow:hidden;position:relative;">
                        <div id="scan" style="width:40%;height:100%;background:#d4af37;position:absolute;left:-40%;"></div>
                    </div>
                    <p style="color:#d4af37;text-transform:uppercase;letter-spacing:4px;font-size:0.7rem;">AI_ENGINE: SELF-HEALING IN PROGRESS</p>
                    <p style="color:#555;font-size:0.65rem;margin-top:20px;">Auto-recovering in <span id="ct">5</span>s...</p>
                `;
                document.body.appendChild(ov);
                // Animate scan line
                let pos = -40;
                const scan = ov.querySelector('#scan');
                const anim = setInterval(() => {{ pos += 3; if(pos > 100) pos = -40; scan.style.left = pos + '%'; }}, 16);
                // Countdown
                let t = 5;
                const ct = ov.querySelector('#ct');
                const cd = setInterval(() => {{ t--; if(ct) ct.innerText = t; if(t <= 0) {{ clearInterval(cd); clearInterval(anim); location.reload(); }} }}, 1000);
            }}

            async function triggerAction(endpoint, nextUrl, btn) {{
                if (btn) btn.classList.add('loading');
                try {{
                    const res = await fetch(endpoint, {{ method: 'POST' }});
                    if (res.ok) {{
                        window.location.href = nextUrl || location.href;
                    }} else {{
                        showFaultOverlay(res.status);
                    }}
                }} catch (e) {{
                    showFaultOverlay('503');
                }}
                if (btn) btn.classList.remove('loading');
            }}
        </script>
        <style>
            @keyframes shake {{
                0%, 100% {{ transform: translateX(0); }}
                25% {{ transform: translateX(-5px); }}
                75% {{ transform: translateX(5px); }}
            }}
            .shake {{ animation: shake 0.2s ease-in-out; }}
            .btn.loading {{ opacity: 0.5; pointer-events: none; }}
        </style>
    </body>
    </html>
    """

# --- PAGE ROUTERS ---

@app.get("/", response_class=HTMLResponse)
async def store_view():
    from .routes import get_ui_status
    state = get_ui_status()
    product_html = "".join([f"""
        <div class="item-card">
            <div class="item-img-container"><img src="{p['image']}" class="item-img" /></div>
            <div class="item-info">
                <div class="item-title">{p['name']}</div>
                <div class="item-price">${p['price']:,}</div>
                <button class="btn" style="margin-top: 15px; width: 100%;" onclick="triggerAction('/cart/add', '/cart', this)">Acquire Item</button>
            </div>
        </div>
    """ for p in products])
    content = f'<h1 style="font-size: 4rem; text-align:center; margin-bottom: 60px;">THE ATELIER</h1><p style="text-align:center; color:#888; margin-top:-40px; margin-bottom:40px;">System behavior dictates manual signal generation on error.</p><div class="grid">{product_html}</div>'
    # Store page: only show overlay for 503 cart/overload faults
    return get_base_layout(content, state, "home", page_faults=[503])

@app.get("/cart", response_class=HTMLResponse)
async def cart_view():
    from .routes import get_ui_status
    state = get_ui_status()
    p = products[0]
    content = f"""
    <h1 style="font-size: 3rem; text-align:center; margin-bottom: 50px;">YOUR BAG</h1>
    <div style="background:var(--card-bg); padding:40px; border-radius:8px; border:1px solid rgba(255,255,255,0.05); max-width: 800px; margin: 0 auto;">
        <div style="display:flex; gap:30px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:30px; margin-bottom:30px;">
            <img src="{p['image']}" style="width:120px; aspect-ratio:3/4; object-fit:cover;" />
            <div style="flex:1">
                <h3>{p['name']}</h3>
                <p style="color:var(--accent); font-size:1.5rem; margin-top:15px;">${p['price']:,}</p>
            </div>
        </div>
        <div style="text-align:right"><button class="btn" onclick="window.location.href='/checkout-page'">Proceed to Review</button></div>
    </div>
    """
    # Cart page: only show overlay for 503 cart/overload faults
    return get_base_layout(content, state, "home", page_faults=[503])

@app.get("/checkout-page", response_class=HTMLResponse)
async def checkout_review():
    from .routes import get_ui_status
    state = get_ui_status()
    content = f"""
    <h1 style="font-size: 3rem; text-align:center; margin-bottom: 50px;">REVIEW</h1>
    <div style="background:var(--card-bg); padding:40px; border-radius:8px; border:1px solid rgba(255,255,255,0.05); max-width: 800px; margin: 0 auto;">
        <div style="display:flex; justify-content:space-between; margin-bottom:40px">
            <div><h3>Total Value</h3><p style="color:var(--secondary-text)">Neo-Veridia Delivery</p></div>
            <div style="font-size:2.5rem; color:var(--accent); font-weight:700;">${products[0]['price']:,}</div>
        </div>
        <button class="btn" style="width:100%" onclick="triggerAction('/checkout', '/payment-page', this)">Complete Acquisition</button>
    </div>
    """
    # Checkout-review page: only show overlay for 500 checkout faults
    return get_base_layout(content, state, "home", page_faults=[500])

@app.get("/payment-page", response_class=HTMLResponse)
async def payment_view():
    from .routes import get_ui_status
    state = get_ui_status()
    content = f"""
    <h1 style="font-size: 3rem; text-align:center; margin-bottom: 50px;">NEURAL GATEWAY</h1>
    <div style="background:var(--card-bg); padding:60px; border-radius:8px; border:1px solid rgba(255,255,255,0.05); max-width: 600px; margin: 0 auto; text-align:center;">
        <h2 style="color:var(--accent); margin-bottom:20px;">AUTHORIZING</h2>
        <div style="font-size:4rem; margin-bottom:40px;">${products[0]['price']:,}</div>
        <button class="btn" style="width:100%" onclick="triggerAction('/payment', '/', this)">Verify Biometrics</button>
    </div>
    """
    # Payment page: only show overlay for 504 payment/timeout faults
    return get_base_layout(content, state, "home", page_faults=[504])

@app.get("/dashboard-old", response_class=HTMLResponse)
async def dashboard_old_view():
    from .routes import get_ui_status, get_ai_stats
    state = get_ui_status()
    stats = await get_ai_stats()

    # Base values for initial load
    precision         = stats.get("precision", 1.0)
    recall            = stats.get("recall", 0.0)
    f1                = stats.get("f1_score", 0.0)
    total_detections  = stats.get("total_detections", 0)
    rv                = stats.get("restarts_verified", 0)
    ru                = stats.get("restarts_unverified", 0)
    suppressed        = stats.get("remediations_suppressed", 0)

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 40px;">
        <h1 style="font-size: 2.8rem; letter-spacing:-1px;">S.Y.S. MONITOR <span style="font-size: 0.8rem; color: var(--accent); vertical-align: middle; margin-left:10px; letter-spacing: 4px; background: rgba(212, 175, 55, 0.1); padding: 4px 10px; border-radius: 4px;">AI-ENHANCED NOC</span></h1>
        <div style="text-align:right">
            <div style="color:var(--secondary-text); font-size:0.6rem; letter-spacing:3px; margin-bottom:5px; text-transform:uppercase;">Network Health Index</div>
            <div style="font-size:1.4rem; font-weight:800; color:#00e676;" id="health-index">99.8%</div>
        </div>
    </div>

    <!-- NOC GAUGES ROW -->
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:20px; margin-bottom:30px;">
        <div class="stat-card" style="display:flex; flex-direction:column; align-items:center; padding: 20px;">
            <div class="stat-label" style="font-size:0.6rem;">Success Rate</div>
            <div class="stat-value" style="font-size:2rem;" id="v-success">100%</div>
            <div style="width:100%; height:4px; background:rgba(255,255,255,0.05); border-radius:2px; margin-top:10px;">
                <div style="width:100%; height:100%; background:#00e676; border-radius:2px;" id="b-success"></div>
            </div>
        </div>
        <div class="stat-card" style="display:flex; flex-direction:column; align-items:center; padding: 20px;">
            <div class="stat-label" style="font-size:0.6rem;">AI Confidence</div>
            <div class="stat-value" style="font-size:2rem;" id="v-conf">--</div>
            <div style="width:100%; height:4px; background:rgba(255,255,255,0.05); border-radius:2px; margin-top:10px;">
                <div style="width:75%; height:100%; background:var(--accent); border-radius:2px;" id="b-conf"></div>
            </div>
        </div>
        <div class="stat-card" style="display:flex; flex-direction:column; align-items:center; padding: 20px;">
            <div class="stat-label" style="font-size:0.6rem;">Active Latency</div>
            <div class="stat-value" style="font-size:2rem;" id="v-lat">0.02s</div>
            <div style="width:100%; height:4px; background:rgba(255,255,255,0.05); border-radius:2px; margin-top:10px;">
                <div style="width:5%; height:100%; background:#6366f1; border-radius:2px;" id="b-lat"></div>
            </div>
        </div>
        <div class="stat-card" style="display:flex; flex-direction:column; align-items:center; padding: 20px;">
            <div class="stat-label" style="font-size:0.6rem;">Learning Buffer</div>
            <div class="stat-value" style="font-size:2rem;" id="v-buf">0</div>
            <div style="width:100%; height:4px; background:rgba(255,255,255,0.05); border-radius:2px; margin-top:10px;">
                <div style="width:0%; height:100%; background:#ff9100; border-radius:2px;" id="b-buf"></div>
            </div>
        </div>
    </div>

    <!-- TELEMETRY PULSE & ANOMALY BREAKDOWN -->
    <div style="display:grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom:20px;">
        <div class="chart-container" style="flex-direction:column; align-items:flex-start; padding: 30px; position: relative; overflow: hidden;">
            <div style="position:absolute; top:0; left:0; width:100%; height:2px; background: linear-gradient(90deg, transparent, var(--accent), transparent); animation: scan 3s infinite;"></div>
            <h3 style="margin-bottom:20px; font-size:0.9rem; letter-spacing:2px; color:rgba(255,255,255,0.5);">SYSTEM PULSE (LATENCY vs AI ANXIETY)</h3>
            <canvas id="pulseChart" style="width:100% !important; height: 300px !important;"></canvas>
        </div>
        
        <div class="chart-container" style="flex-direction:column; padding: 30px;">
            <h3 style="margin-bottom:20px; font-size:0.9rem; letter-spacing:2px; color:rgba(255,255,255,0.5);">FAILURE CLASSIFICATION</h3>
            <canvas id="errorChart" style="max-height:200px !important;"></canvas>
            <div style="margin-top:20px; width:100%;">
                <div style="display:flex; justify-content:space-between; font-size:0.7rem; margin-bottom:8px;">
                    <span style="color:var(--secondary-text);">Precision (Fidelity)</span>
                    <span style="color:#00e676;">{precision*100:.1f}%</span>
                </div>
                <div style="width:100%; height:2px; background:rgba(255,255,255,0.05);">
                    <div style="width:{precision*100}%; height:100%; background:#00e676;"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- LOGS & INFRASTRUCTURE -->
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div class="stat-card" style="text-align:left; background: rgba(255,255,255,0.02); height: 300px; display:flex; flex-direction:column;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 15px;">
                <h3 style="font-size:0.8rem; letter-spacing:2px;">ACTION LEDGER</h3>
                <span id="log-status" style="font-size:0.6rem; color:#00e676;">● SYNCHRONIZED</span>
            </div>
            <div id="log-stream" style="flex:1; font-family:'Courier New', monospace; font-size:0.7rem; color:var(--secondary-text); overflow-y:auto; line-height:1.6; border-top: 1px solid rgba(255,255,255,0.05); padding-top:15px;">
                Initializing secure link...
            </div>
        </div>

        <div class="stat-card" style="text-align:left; background: rgba(255,255,255,0.02); height: 300px; display:flex; flex-direction:column; padding: 40px;">
            <h3 style="font-size:0.8rem; letter-spacing:2px; margin-bottom:30px;">INFRASTRUCTURE TELEMETRY</h3>
            
            <div style="margin-bottom:25px;">
                <div style="display:flex; justify-content:space-between; font-size:0.7rem; margin-bottom:8px; text-transform:uppercase;">
                    <span>CPU Utlization</span>
                    <span id="v-cpu">0%</span>
                </div>
                <div style="width:100%; height:6px; background:rgba(255,255,255,0.05); border-radius:3px;">
                    <div id="b-cpu" style="width:0%; height:100%; background:var(--accent); border-radius:3px; transition:0.5s;"></div>
                </div>
            </div>

            <div style="margin-bottom:25px;">
                <div style="display:flex; justify-content:space-between; font-size:0.7rem; margin-bottom:8px; text-transform:uppercase;">
                    <span>Memory Allocation</span>
                    <span id="v-mem">0MB</span>
                </div>
                <div style="width:100%; height:6px; background:rgba(255,255,255,0.05); border-radius:3px;">
                    <div id="b-mem" style="width:0%; height:100%; background:#6366f1; border-radius:3px; transition:0.5s;"></div>
                </div>
            </div>

            <div style="background: rgba(212, 175, 55, 0.05); border: 1px dashed rgba(212, 175, 55, 0.2); padding: 15px; border-radius: 4px; margin-top: auto;">
                <div style="font-size:0.6rem; color:var(--accent); letter-spacing:1px; font-weight:700; margin-bottom:5px;">AI DIAGNOSIS STATUS</div>
                <div id="v-diag" style="font-size:0.75rem; color:white;">Monitoring golden signals for variances. System stable.</div>
            </div>
        </div>
    </div>

    <style>
        @keyframes scan {{
            0% {{ left: -100%; }}
            100% {{ left: 100%; }}
        }}
    </style>

    <script>
        // --- CHARTS INITIALIZATION ---
        const pulseCtx = document.getElementById('pulseChart').getContext('2d');
        const MAX_DATA_POINTS = 30;
        const pulseChart = new Chart(pulseCtx, {{
            type: 'line',
            data: {{
                labels: Array(MAX_DATA_POINTS).fill(''),
                datasets: [
                    {{
                        label: 'Latency (s)',
                        data: Array(MAX_DATA_POINTS).fill(0),
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 0
                    }},
                    {{
                        label: 'AI MSE (Anxiety)',
                        data: Array(MAX_DATA_POINTS).fill(0),
                        borderColor: '#d4af37',
                        borderDash: [5, 5],
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 0
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#555', font: {{ size: 8 }} }} }},
                    x: {{ display: false }}
                }}
            }}
        }});

        const errorCtx = document.getElementById('errorChart').getContext('2d');
        const errorChart = new Chart(errorCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['500', '503D', '503O', '504', '429'],
                datasets: [{{
                    data: [{stats['error_counts']['500_CRASH']}, {stats['error_counts']['503_DEADLOCK']}, {stats['error_counts']['503_OVERLOAD']}, {stats['error_counts']['504_TIMEOUT']}, {stats['error_counts']['429_SECURITY']}],
                    backgroundColor: ['#ff3d00', '#d4af37', '#ff9100', '#6366f1', '#00e676'],
                    borderColor: '#141414',
                    borderWidth: 4
                }}]
            }},
            options: {{ cutout: '85%', plugins: {{ legend: {{ display: false }} }} }}
        }});

        // --- REAL-TIME UPDATES ---
        async function updateDashboard() {{
            try {{
                // 1. Fetch Telemetry
                const tRes = await fetch('/ai/telemetry');
                const t = await tRes.json();
                
                // 2. Update Gauges
                document.getElementById('v-success').innerText = t.error_rate > 0.1 ? 'DEGRADED' : '100%';
                document.getElementById('health-index').innerText = t.error_rate > 0.1 ? '82.4%' : '99.8%';
                document.getElementById('health-index').style.color = t.error_rate > 0.1 ? '#ff3d00' : '#00e676';
                
                document.getElementById('v-lat').innerText = t.p95_latency.toFixed(2) + 's';
                document.getElementById('b-lat').style.width = Math.min(t.p95_latency * 20, 100) + '%';
                
                document.getElementById('v-buf').innerText = t.online_buffer;
                document.getElementById('b-buf').style.width = (t.online_buffer / 500 * 100) + '%';
                
                const conf = t.mse_score < t.threshold ? (95 + Math.random()*4).toFixed(1) : (40 + Math.random()*20).toFixed(1);
                document.getElementById('v-conf').innerText = conf + '%';
                document.getElementById('b-conf').style.width = conf + '%';
                
                // 3. Update Infra Bars
                document.getElementById('v-cpu').innerText = t.cpu_percent.toFixed(0) + '%';
                document.getElementById('b-cpu').style.width = t.cpu_percent + '%';
                document.getElementById('v-mem').innerText = t.memory_mb.toFixed(0) + 'MB';
                document.getElementById('b-mem').style.width = Math.min(t.memory_mb / 5, 100) + '%';
                
                // 4. Update Charts
                pulseChart.data.datasets[0].data.push(t.p95_latency);
                pulseChart.data.datasets[1].data.push(t.mse_score);
                pulseChart.data.datasets[0].data.shift();
                pulseChart.data.datasets[1].data.shift();
                pulseChart.update('none');
                
                // 5. Update Diagnosis
                if (t.mse_score > t.threshold) {{
                    document.getElementById('v-diag').innerText = "ANOMALY DETECTED: Variance in Golden Signals exceeding safety threshold.";
                    document.getElementById('v-diag').style.color = "#ff3d00";
                }} else {{
                    document.getElementById('v-diag').innerText = "System Stable. AI monitoring active.";
                    document.getElementById('v-diag').style.color = "white";
                }}

            }} catch(e) {{ console.error("Telemetry link lost", e); }}
        }}

        async function updateLogs() {{
            try {{
                const res = await fetch('/ai/logs');
                const logs = await res.json();
                const container = document.getElementById('log-stream');
                if (logs.length > 0) {{
                    container.innerHTML = logs.map(l => {{
                        // Enhanced parsing for error types and emojis
                        let color = 'rgba(255,255,255,0.4)';
                        let bgColor = 'transparent';
                        let borderLeft = 'none';
                        
                        // Detect error type and set styling
                        if (l.includes('🔴 ERROR DETECTED') || l.includes('ERROR DETECTED')) {{
                            color = '#ff3d00';
                            bgColor = 'rgba(255, 61, 0, 0.1)';
                            borderLeft = '3px solid #ff3d00';
                        }} else if (l.includes('⚡ REMEDIATION') || l.includes('REMEDIATION')) {{
                            color = '#d4af37';
                            bgColor = 'rgba(212, 175, 55, 0.1)';
                            borderLeft = '3px solid #d4af37';
                        }} else if (l.includes('✅ RECOVERY') || l.includes('RECOVERY') || l.includes('Health VERIFIED')) {{
                            color = '#00e676';
                            bgColor = 'rgba(0, 230, 118, 0.1)';
                            borderLeft = '3px solid #00e676';
                        }} else if (l.includes('ACTION')) {{
                            color = '#d4af37';
                        }} else if (l.includes('DIAGNOSIS')) {{
                            color = '#00e676';
                        }} else if (l.includes('ERROR') || l.includes('WARNING')) {{
                            color = '#ff9100';
                        }}
                        
                        // Extract and highlight error type labels like [500 CRASH], [503 DEADLOCK/OVERLOAD]
                        let displayText = l;
                        const errorTypeMatch = l.match(/\\[(\\d{{3}}[^\\]]+)\\]/);
                        if (errorTypeMatch) {{
                            const errorType = errorTypeMatch[1];
                            displayText = l.replace(
                                `[${{errorType}}]`,
                                `<span style="background: rgba(212, 175, 55, 0.2); padding: 2px 6px; border-radius: 3px; font-weight: 700; color: var(--accent);">[${{errorType}}]</span>`
                            );
                        }}
                        
                        const style = `color:${{color}}; margin-bottom:8px; padding:8px; background:${{bgColor}}; border-left:${{borderLeft}}; border-radius:3px; line-height:1.4;`;
                        return `<div style="${{style}}">${{displayText}}</div>`;
                    }}).join('');
                    container.scrollTop = container.scrollHeight;
                }}
            }} catch(e) {{ }}
        }}

        setInterval(updateDashboard, 2000);
        setInterval(updateLogs, 5000);
        updateDashboard();
        updateLogs();
    </script>
    """
    return get_base_layout(content, state, "dashboard")

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_analytical():
    """Serve the analytical dashboard with injection buttons"""
    with open("/app/app/static/index.html", "r") as f:
        return HTMLResponse(content=f.read())