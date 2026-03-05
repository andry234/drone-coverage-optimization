import gurobipy as gp
from gurobipy import GRB
import json
import math
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import matplotlib.animation as animation

# =============================================================================
# 1. FUNZIONE GRAFICO STATICO 
# =============================================================================
def plot_static(data, x_vars, w_vars, z_vars, V, T, t_ij, TIME_STEP, K, L):
    print("\n--- Generazione Grafico Statico... ---")
    
    nodes = {n["id"]: (n["x"], n["y"]) for n in data["nodes"]}
    targets = {t["id"]: (t["x"], t["y"]) for t in data["targets"]}

    fig, (ax_map, ax_text) = plt.subplots(1, 2, figsize=(16, 10), 
                                          gridspec_kw={'width_ratios': [2.5, 1]})

    # --- MAPPA (Sinistra) ---
    all_edges = set()
    for key in data["t_ij"]:
        u, v = map(int, key.split(","))
        if u != v: all_edges.add(tuple(sorted((u, v))))

    for u, v in all_edges:
        p1, p2 = nodes[u], nodes[v]
        ax_map.plot([p1[0], p2[0]], [p1[1], p2[1]], c='lightgray', lw=1.0, zorder=1)

    for tid, (tx, ty) in targets.items():
        ax_map.scatter(tx, ty, c='red', marker='^', s=80, zorder=2)
        ax_map.text(tx+1, ty+1, f"T{tid}", fontsize=9, color='red', zorder=4)

    for nid, (nx, ny) in nodes.items():
        col = '#FFD700' if nid == 0 else 'blue'
        ax_map.scatter(nx, ny, c=col, s=150, zorder=3, edgecolors='black')
        ax_map.text(nx, ny+1.8, f"N{nid}", fontsize=10, color='darkblue', fontweight='bold', zorder=5)

    # --- RICOSTRUZIONE PERCORSO COMPLETO ---
    current_path_arrows = []
    log_messages = []
    last_node = None
    
    for t in T:
        # Trova nodo attivo
        curr_node = None
        for i in V:
            if x_vars[i, t].X > 0.5:
                curr_node = i
                break
        
        if curr_node is None: 
            if last_node is not None: curr_node = last_node
            else: continue

        # Volo
        if last_node is not None and curr_node != last_node:
            current_path_arrows.append((nodes[last_node], nodes[curr_node]))
            time_str = f"Min {t*TIME_STEP:.0f}"
            log_messages.append(f"{time_str}: -> Volo N{last_node} > N{curr_node}")

        # Sensore
        sens_info = "OFF"
        for l in L:
            if w_vars[l, t].X > 0.5:
                sens_info = f"L{l}"
                break
        
        if sens_info != "OFF":
            cov = [f"T{k}" for k in K if z_vars[k, t].X > 0.5]
            cov_str = f" {{Copre: {','.join(cov)}}}" if cov else ""
            time_str = f"Min {t*TIME_STEP:.0f}"
            
            # Evita duplicati consecutivi nel log
            if not log_messages or "Stazionamento" not in log_messages[-1] or str(curr_node) not in log_messages[-1]:
                 log_messages.append(f"{time_str}: Stazionamento N{curr_node} ({sens_info}){cov_str}")
        
        last_node = curr_node

    # --- DISEGNO FRECCE SULLA MAPPA ---
    for start, end in current_path_arrows:
        ax_map.annotate("", xy=end, xytext=start,
                        arrowprops=dict(arrowstyle="->", color="red", 
                                        alpha=0.9, lw=2.0), zorder=6)

    # Titolo identico all'animazione
    n_nodes, n_targets, n_edges = len(nodes), len(targets), len(all_edges)
    max_edges = (n_nodes * (n_nodes - 1)) / 2
    density = n_edges / max_edges if max_edges > 0 else 0
    total_min = T[-1] * TIME_STEP
    
    ax_map.set_title(f"Grafo: {n_nodes} Nodi, {n_targets} Target, Densità {density:.2f} | Area: 10x10 km\n")
    ax_map.set_xlabel("X (unità x 100m)"); ax_map.set_ylabel("Y (unità x 100m)")
    ax_map.grid(True, alpha=0.3, linestyle='--')
    ax_map.axis('equal')

    # --- CRONOLOGIA TESTUALE (Destra) ---
    ax_text.axis('off')
    ax_text.text(0, 1.0, "CRONOLOGIA COMPLETA", fontsize=12, fontweight='bold', transform=ax_text.transAxes)
    
    # Stampa SOLO GLI ULTIMI 20 EVENTI se sono troppi, altrimenti esce dal foglio
    # Oppure riduciamo il font se sono tanti. Qui mostriamo gli ultimi per coerenza.
    visible_msgs = log_messages if len(log_messages) < 22 else log_messages[-22:]
    
    y_pos = 0.94
    for txt in visible_msgs:
        col = 'red' if "Volo" in txt else 'green'
        mark = '>' if "Volo" in txt else 'o'
        font_w = 'bold' if "Stazionamento" in txt else 'normal'
        
        ax_text.plot(0.05, y_pos, marker=mark, color=col, markersize=5, transform=ax_text.transAxes)
        # Font size adattivo
        f_size = 9 
        ax_text.text(0.12, y_pos, txt, fontsize=f_size, fontweight=font_w, transform=ax_text.transAxes, va='center')
        
        y_pos -= 0.045
    
    if len(log_messages) > 22:
        ax_text.text(0.1, 0.98, "(... Primi eventi nascosti ...)", fontsize=8, color='gray', fontstyle='italic', transform=ax_text.transAxes)

     # Simbolo Nodo (Cerchio Blu)
    legend_node = mlines.Line2D([], [], color='blue', marker='o', linestyle='None',
                                markersize=10, label='Nodo')
    
    # Simbolo Target (Triangolo Rosso)
    legend_target = mlines.Line2D([], [], color='red', marker='^', linestyle='None',
                                  markersize=10, label='Target (Punto di Interesse)')
    
    # Simbolo Volo (Freccia Nera)
    legend_flight = mlines.Line2D([], [], color='black', marker=r'$\rightarrow$', linestyle='-',
                                  linewidth=2, markersize=15, label='Volo (Spostamento)')
    
    # Simbolo Stazionamento (Cerchio Verde Vuoto)
    legend_hover = mlines.Line2D([], [], color='green', marker='o', linestyle='None',
                                 markersize=12, markerfacecolor='none', markeredgewidth=2,
                                 label='Stazionamento / Attesa')

    # Aggiunge la legenda al grafico in alto a destra (o posizione migliore automatica)
    plt.legend(handles=[legend_node, legend_target, legend_flight, legend_hover], 
               loc='best', frameon=True, shadow=True, fontsize=10)
    plt.tight_layout()
    plt.show()

# =============================================================================
# 2. FUNZIONE ANIMAZIONE (Drone che si muove + Raggi di copertura)
# =============================================================================
def plot_animated(data, x_vars, w_vars, z_vars, V, T, t_ij, TIME_STEP, K, L):
    print("\n--- Generazione Animazione... ---")
    nodes = {n["id"]: (n["x"], n["y"]) for n in data["nodes"]}
    targets = {t["id"]: (t["x"], t["y"]) for t in data["targets"]}
    sensing_radii = {int(l): float(info["radius"]) for l, info in data["global_parameters"]["sensing_levels"].items()}
    LEVEL_COLORS = {1: "#32CD32", 2: "#FFA500", 3: "#9370DB"} 

    fig, (ax_map, ax_text) = plt.subplots(1, 2, figsize=(16, 10), gridspec_kw={'width_ratios': [2.5, 1]})

    all_edges = set()
    for key in data["t_ij"]:
        u, v = map(int, key.split(","))
        if u != v: all_edges.add(tuple(sorted((u, v))))

    n_nodes, n_targets, n_edges = len(nodes), len(targets), len(all_edges)
    max_edges = (n_nodes * (n_nodes - 1)) / 2
    density = n_edges / max_edges if max_edges > 0 else 0

    frames_data = []
    current_path_arrows, log_messages = [], []
    last_node, last_radius = None, 0
    
    for t in T:
        curr_node = None
        for i in V:
            if x_vars[i, t].X > 0.5: curr_node = i; break
        if curr_node is None: 
            if last_node is not None: curr_node = last_node
            else: continue

        if last_node is not None and curr_node != last_node:
            current_path_arrows.append((nodes[last_node], nodes[curr_node]))
            log_messages.append(f"Min {t*TIME_STEP:.0f}: -> Volo N{last_node} > N{curr_node}")

        sens_info, active_radius, active_level = "OFF", 0.0, 0
        for l in L:
            if w_vars[l, t].X > 0.5: sens_info, active_radius, active_level = f"L{l}", sensing_radii[l], int(l); break
        
        if sens_info != "OFF":
            cov = [f"T{k}" for k in K if z_vars[k, t].X > 0.5]
            cov_str = f" {{Copre: {','.join(cov)}}}" if cov else ""
            if not log_messages or "Stazionamento" not in log_messages[-1] or str(curr_node) not in log_messages[-1]:
                 log_messages.append(f"Min {t*TIME_STEP:.0f}: Stazionamento N{curr_node} ({sens_info}){cov_str}")

        is_just_activated = (active_radius > 0) and (last_radius == 0 or curr_node != last_node)
        if is_just_activated:
            frames_data.append({'time': t*TIME_STEP, 'drone_pos': nodes[curr_node], 'path_arrows': list(current_path_arrows), 
                                'log': list(log_messages), 'node_id': curr_node, 'sensor_radius': 0.0, 'sensor_level': 0, 'sensor_label': "Posizionamento..."})

        frames_data.append({'time': t*TIME_STEP, 'drone_pos': nodes[curr_node], 'path_arrows': list(current_path_arrows), 
                            'log': list(log_messages), 'node_id': curr_node, 'sensor_radius': active_radius, 'sensor_level': active_level, 'sensor_label': sens_info})
        last_node, last_radius = curr_node, active_radius

    def init():
        ax_map.clear(); ax_text.clear()
        return []

    def update(frame_idx):
        ax_map.clear()
        for u, v in all_edges: ax_map.plot([nodes[u][0], nodes[v][0]], [nodes[u][1], nodes[v][1]], c='lightgray', lw=1.0, zorder=1)
        for tid, (tx, ty) in targets.items(): ax_map.scatter(tx, ty, c='red', marker='^', s=80, zorder=2); ax_map.text(tx+1, ty+1, f"T{tid}", fontsize=9, color='red', zorder=4)
        for nid, (nx, ny) in nodes.items(): ax_map.scatter(nx, ny, c='#FFD700' if nid==0 else 'blue', s=150, zorder=3, edgecolors='black'); ax_map.text(nx, ny+1.8, f"N{nid}", fontsize=10, color='darkblue', fontweight='bold', zorder=5)
        ax_map.set_xlabel("X (unità x 100m)"); ax_map.set_ylabel("Y (unità x 100m)"); ax_map.grid(True, alpha=0.3, linestyle='--')
        
        df = frames_data[frame_idx]
        status_txt = f"SENS: {df['sensor_label']}" if df['sensor_radius'] > 0 else "IN VOLO / IDLE"
        ax_map.set_title(f"Grafo: {n_nodes} Nodi, {n_targets} Target, Densità {density:.2f} | Area: 10x10 km\nTempo: {df['time']:.0f} min | Stato: {status_txt}", fontsize=12)
        
        for s, e in df['path_arrows']: ax_map.annotate("", xy=e, xytext=s, arrowprops=dict(arrowstyle="->", color="red", alpha=0.9, lw=2.0), zorder=6)
        ax_map.scatter(df['drone_pos'][0], df['drone_pos'][1], s=400, c='green', marker='o', alpha=0.8, zorder=8, edgecolors='white', linewidth=2)
        
        if df['sensor_radius'] > 0:
            c = LEVEL_COLORS.get(df['sensor_level'], 'green')
            ax_map.add_patch(mpatches.Circle(df['drone_pos'], df['sensor_radius'], color=c, alpha=0.2, zorder=5))
            ax_map.add_patch(mpatches.Circle(df['drone_pos'], df['sensor_radius'], color=c, fill=False, linewidth=2, linestyle='--', zorder=5))

        ax_text.clear(); ax_text.axis('off'); ax_text.text(0, 1.0, "CRONOLOGIA LIVE", fontsize=12, fontweight='bold', transform=ax_text.transAxes)
        msgs = df['log'][-15:]
        y = 0.94
        for t in msgs:
            ax_text.plot(0.05, y, marker='>' if "Volo" in t else 'o', color='red' if "Volo" in t else 'green', markersize=5, transform=ax_text.transAxes)
            ax_text.text(0.12, y, t, fontsize=9, fontweight='bold' if "Stazionamento" in t else 'normal', transform=ax_text.transAxes, va='center')
            y -= 0.05
        return []

    ani = animation.FuncAnimation(fig, update, frames=len(frames_data), init_func=init, interval=1000, blit=False, repeat=True)
    plt.tight_layout(); plt.show()
    ani.save('drone_mission.mp4', writer='ffmpeg')

# =============================================================================
# FUNZIONE PRINCIPALE: carica l'istanza, costruisce e risolve il modello 
# =============================================================================
def load_and_solve(filename="instance.json"):
    print(f"--- Caricamento istanza da {filename} ---")

    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("ERRORE: File non trovato.")
        return

    # -------------------------------------------------------------------------
    # TIME SCALING
    # Il tempo reale viene discretizzato in step di TIME_STEP minuti.
    # Esempio: TIME_STEP=5 → ogni unità del modello vale 5 minuti reali.
    # Valori più grandi riducono T_max e quindi le variabili del modello,
    # ma rendono l'approssimazione meno precisa.
    # -------------------------------------------------------------------------
    TIME_STEP = 5.0
    print(f"*** TIME SCALING: 1 Step = {TIME_STEP} s ***")

    # -------------------------------------------------------------------------
    # INSIEMI
    # -------------------------------------------------------------------------
    V = sorted([n["id"] for n in data["nodes"]])    
    K = sorted([t["id"] for t in data["targets"]])  
    sensing_data = data["global_parameters"]["sensing_levels"]
    L = sorted([int(k) for k in sensing_data.keys()])  

    # -------------------------------------------------------------------------
    # BATTERIA E ORIZZONTE TEMPORALE
    # battery_real: budget energetico totale nelle unità originali dell'istanza
    # T_max: numero massimo di step discreti nell'orizzonte (batteria / TIME_STEP)
    # B_total: budget batteria usato nel vincolo energetico (in unità originali)
    # alpha: costo marginale per ogni target coperto
    # -------------------------------------------------------------------------
    battery_real = data["global_parameters"]["battery_time"]
    T_max  = math.ceil(battery_real / TIME_STEP)
    T      = range(T_max + 1)
    B_total = battery_real  
    alpha  = 0.1  

    print(f"Orizzonte: {T_max} steps  |  Budget reale: {B_total:.1f}")

    # Archi
    t_ij   = {}
    E_list = []
    for key, val in data["t_ij"].items():
        u, v = map(int, key.split(","))
        t_ij[(u, v)] = max(1, math.ceil(val / TIME_STEP))
        E_list.append((u, v))

    for i in V:
        if (i, i) not in t_ij:
            t_ij[(i, i)] = 1  
            E_list.append((i, i))
    
    

    # -------------------------------------------------------------------------
    # COSTO ENERGETICO DEI LIVELLI DEL SENSORE
    # c_l[l]: energia consumata per step di utilizzo del livello l
    # Viene scalato per TIME_STEP per tornare alle unità originali della batteria
    # -------------------------------------------------------------------------
    c_l = {}
    for l_key, l_val in sensing_data.items():
        base_cost = l_val.get("energy_cost", 1.0)
        c_l[int(l_key)] = base_cost * TIME_STEP

    # -------------------------------------------------------------------------
    # COPERTURA: a_ikl[(i,l)] = insieme dei target coperti dal nodo i al livello l
    # Viene costruito solo per le coppie (i,l) con almeno un target copribile
    # -------------------------------------------------------------------------
    a_ikl = {}
    for item in data["coverage"]:
        node_idx = item["node_id"]
        for lvl_item in item["levels"]:
            l_idx  = int(lvl_item["level"])
            t_ids  = set(lvl_item["targets"])
            if t_ids:
                a_ikl[(node_idx, l_idx)] = t_ids

    # -------------------------------------------------------------------------
    # FINESTRE DI COPERTURA Delta_k (scalate in step discreti)
    # Delta_k[k]: numero massimo di step consecutivi senza coprire il target k
    # -------------------------------------------------------------------------
    Delta_k = {}
    for k_str, v in data["target_parameters"].items():
        real_delta = v["max_uncovered_time"]
        Delta_k[int(k_str)] = max(1, math.floor(real_delta / TIME_STEP))

    # =========================================================================
    # COSTRUZIONE DEL MODELLO (LOGICA INVARIATA)
    # =========================================================================
    print("--- Costruzione Modello ---")
    m = gp.Model("DroneSweepCoverage")
    m.setParam('TimeLimit', 180)
    m.setParam('MIPGap', 0.05)   
    m.setParam('OutputFlag', 1)    

    # -------------------------------------------------------------------------
    # VARIABILI DECISIONALI
    # x[i,t]   = 1 se il drone è nel nodo i al tempo t
    # y[i,j,t] = 1 se il drone inizia a percorrere l'arco (i,j) al tempo t
    # w[l,t]   = 1 se il livello di potenza l è attivo al tempo t
    # u[i,l,t] = x[i,t] AND w[l,t]  (prodotto linearizzato)
    # z[k,t]   = 1 se il target k è coperto al tempo t
    # s[k,t]   = penalità di scopertura del target k al tempo t (≥ 0)
    # -------------------------------------------------------------------------
    x = m.addVars(V, T, vtype=GRB.BINARY, name="x")

    y_keys = []
    for (i, j) in E_list:
        cost = t_ij[(i, j)]
        for t in T:
            if t + cost <= T_max:
                y_keys.append((i, j, t))
    y = m.addVars(y_keys, vtype=GRB.BINARY, name="y")

    w = m.addVars(L, T, vtype=GRB.BINARY, name="w")

    u_keys = [(i, l, t) for (i, l) in a_ikl.keys() for t in T]
    u = m.addVars(u_keys, vtype=GRB.BINARY, name="u")

    z = m.addVars(K, T, vtype=GRB.BINARY, name="z")
    s = m.addVars(K, T, vtype=GRB.CONTINUOUS, lb=0.0, name="s")

    # =========================================================================
    # VINCOLI
    # =========================================================================

    # --- 1. Al più un nodo occupato per timestep ---
    # Durante il transito (tra partenza e arrivo) il drone non è in nessun nodo
    m.addConstrs((gp.quicksum(x[i, t] for i in V) <= 1 for t in T), name="SinglePos")
    
    # --- 2. Al più un livello di potenza attivo per timestep ---
    m.addConstrs((gp.quicksum(w[l, t] for l in L) <= 1 for t in T), name="SingleLvl")

    # --- 3. Vincolo di uscita (rilassato con <=) ---
    # Se il drone è nel nodo i, può partire (sum=1) oppure restare/spegnersi (sum=0)
    for i in V:
        for t in T:
            arcs_out = [y[i, j, t] for j in V if (i, j, t) in y]
            if arcs_out:
                m.addConstr(gp.quicksum(arcs_out) <= x[i, t], name=f"FlowOut_{i}_{t}")

    # --- 4. Vincolo di arrivo ---
    # Il drone è nel nodo j al tempo t SE E SOLO SE è arrivato da un arco (i,j)
    # che è partito al tempo t - t_ij[(i,j)].
    for j in V:
        for t in T:
            if t == 0: continue
            arcs_in = []
            for i in V:
                if (i, j) in t_ij:
                    prev_t = t - t_ij[(i, j)]
                    if (i, j, prev_t) in y:
                        arcs_in.append(y[i, j, prev_t])
            
            # Se arcs_in è vuoto, quicksum fa 0, forzando x[j,t] = 0 
            m.addConstr(x[j, t] == gp.quicksum(arcs_in), name=f"FlowIn_{j}_{t}")

    # --- 5. Linearizzazione u[i,l,t] = x[i,t] AND w[l,t] ---
    # I primi due vincoli garantiscono u ≤ min(x, w).
    for (i, l, t) in u_keys:
        m.addConstr(u[i, l, t] <= x[i, t])
        m.addConstr(u[i, l, t] <= w[l, t])
        m.addConstr(u[i, l, t] >= x[i, t] + w[l, t] - 1)

    # --- 6. Copertura target ---
    # z[k,t] = 1 solo se esiste almeno una coppia (i,l) attiva che copre k
    for k in K:
        for t in T:
            relevant_u = [u[i, l, t] for (i, l) in a_ikl if k in a_ikl[(i, l)]]
            if relevant_u:
                m.addConstr(z[k, t] <= gp.quicksum(relevant_u), name=f"Cov_{k}_{t}")
            else:
                m.addConstr(z[k, t] == 0) 

    # --- 7. Vincolo energetico ---
    # Il consumo totale non può superare il budget B_total:
    #   - movimento: t_ij * TIME_STEP per ogni arco percorso
    #   - sensing: c_l[l] per ogni step con livello l attivo
    #   - marginale: alpha per ogni (target, timestep) coperto
    HOVER_COST = 0.01
    energy_move = gp.quicksum(
        (t_ij[(i, j)] * TIME_STEP * (1.0 if i != j else HOVER_COST)) * y[i, j, t]
        for (i, j, t) in y_keys
    )
    energy_sense = gp.quicksum(c_l[l] * w[l, t] for l in L for t in T)
    energy_alpha = gp.quicksum(alpha * z[k, t] for k in K for t in T)
    m.addConstr(energy_move + energy_sense + energy_alpha <= B_total, name="BudgetBattery")

    # --- 8. Penalità di scopertura ---
    # Se il target k non è stato coperto in nessuno dei Delta_k step precedenti,
    # la variabile s[k,t] deve essere ≥ 1 (penalità attiva).
    # Se è stato coperto almeno una volta, la somma è ≥ 1 e s può restare 0.
    for k in K:
        delta = Delta_k[k]
        for t in T:
            t_start = max(0, t - delta + 1)
            z_sum = gp.quicksum(z[k, tau] for tau in range(t_start, t + 1))
            m.addConstr(s[k, t] >= 1 - z_sum, name=f"Pen_{k}_{t}")

    # --- 9. Condizione iniziale: il drone parte dal nodo 0 ---
    m.addConstr(x[0, 0] == 1, name="Start0")

    # Obiettivo
    m.setObjective(gp.quicksum(s[k, t] for k in K for t in T), GRB.MINIMIZE)

    print("Avvio ottimizzazione...")
    m.optimize()

    # =========================================================================
    # OUTPUT 
    # =========================================================================
    if m.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
        print(f"\n=== SOLUZIONE TROVATA: obiettivo = {m.objVal:.2f} ===")

        val_move = 0.0
        val_sense = 0.0
        val_alpha = 0.0

        print("\n--- CRONOLOGIA ---")
        for t in T:
            curr_nodes = [i for i in V if x[i, t].X > 0.5]
            if not curr_nodes: continue
            curr_node = curr_nodes[0]

            action_desc = ""
            is_active = False
            for j in V:
                if (curr_node, j, t) in y and y[curr_node, j, t].X > 0.5:
                    is_active = True
                    steps = t_ij[(curr_node, j)]
                    duration = steps * TIME_STEP
                    if curr_node == j:
                        costo_reale = duration * 0.01  
                        val_move += costo_reale
                        action_desc = "(ATTESA)"
                    else:
                        val_move += duration
                        action_desc = f"-> Volo verso {j} ({duration:.0f}m)"
                    break

            if not is_active:
                action_desc = "** FINE MISSIONE **" 

            active_lvls = [l for l in L if w[l, t].X > 0.5]
            if active_lvls:
                lvl = active_lvls[0]
                sens_str = f"SENS:L{lvl}"
                val_sense += c_l[lvl]
            else:
                sens_str = "SENS:OFF"

            # --- AGGIUNTA OUTPUT: Quali target sono coperti ---
            covered_targets = []
            for k_id in K:
                if z[k_id, t].X > 0.5:
                    covered_targets.append(f"T{k_id}")
            
            if covered_targets:
                val_alpha += alpha * len(covered_targets)
                cov_str = f"Copre: {', '.join(covered_targets)}"
            else:
                cov_str = ""

            real_time = t * TIME_STEP
            print(f"Step {t:03d} ({real_time:6.1f}m) | Nodo {curr_node} {sens_str} | {action_desc} {cov_str}")

        total_cons = val_move + val_sense + val_alpha
        print("\n" + "="*45)
        print("          REPORT ENERGETICO REALE")
        print("="*45)
        print(f"BUDGET              : {B_total:.2f}")
        print(f"CONSUMATO           : {total_cons:.2f} ({(total_cons/B_total)*100:.1f}%)")
        print("-"*45)
        print(f"1. Spostamento                 : {val_move:.2f}")
        print(f"2. Consumo livelli sensore     : {val_sense:.2f}")
        print(f"3. Copertura dei target        : {val_alpha:.2f}")
        print("="*45)

        while True:
            print("\n" + "="*40)
            print("SCELTA VISUALIZZAZIONE:")
            print("1 - Grafico Statico")
            print("2 - Animazione Dinamica (Drone in movimento + Sensori)")
            print("0 - Esci")
            choice = input("Inserisci scelta (1/2/0): ").strip()

            if choice == '1':
                # Chiamata al grafico statico
                plot_static(data, x, w, z, V, T, t_ij, TIME_STEP, K, L)
                print("Visualizzo grafico statico...") # Rimpiazza con la chiamata vera
                # plot_static(...) 
                break
            elif choice == '2':
                # Chiamata all'animazione
                plot_animated(data, x, w, z, V, T, t_ij, TIME_STEP, K, L)
                print("Avvio animazione...")
                # plot_animated(...)
                break
            elif choice == '0':
                print("Uscita.")
                break
            else:
                print("Scelta non valida.")

    else:
        print("Nessuna soluzione trovata.")

if __name__ == "__main__":
    load_and_solve("instance.json")