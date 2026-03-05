import random
import math
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

# =============================================================================
# CONFIGURAZIONE 
# =============================================================================
SUGGESTIONS = {
    "facile": {
        "desc": "Tutorial (Istantaneo)",
        "nodes": (6, 8),      "targets": (8, 12),   "density": (0.6, 0.9)
    },
    "difficile": {
        "desc": "Standard",
        "nodes": (12, 18),     "targets": (22, 28),  "density": (0.4, 0.6)
    }
}

class InstanceGenerator:
    """
    Generatore automatico di istanze.
    """

    def __init__(self, difficulty="difficile", n_nodes=None, n_targets=None, density=None, seed=None):
        if seed is not None:
            random.seed(seed)

        self.difficulty = difficulty.lower().strip()
        
        # Fallback se viene passato qualcosa di strano
        if self.difficulty not in SUGGESTIONS:
            self.difficulty = "difficile"
        
        ranges = SUGGESTIONS[self.difficulty]
        
        self.n_nodes = n_nodes if n_nodes is not None else random.randint(*ranges["nodes"])
        self.n_targets = n_targets if n_targets is not None else random.randint(*ranges["targets"])
        self.density = density if density is not None else random.uniform(*ranges["density"])

        self._set_physics_parameters()

        # --- PARAMETRI FISICI DRONE ---
        self.drone_speed = 5.0

        # --- LIVELLI DI SENSING (L) ---
        self.sensing_levels = {
             1: {"radius": 8.0, "energy_cost": 0.1},
             2: {"radius": 15.0, "energy_cost": 0.4},
             3: {"radius": 25.0, "energy_cost": 1.0}
        }

        self.instance = {}

    def _set_physics_parameters(self):
        """
        Imposta i moltiplicatori.
        Facile: Parametri molto permissivi.
        Difficile: Parametri più restrittivi
        """
        if self.difficulty == "facile":
            self.delta_mult = (2.0, 3.0)  
            self.batt_mult = 3.5         
        
        else: # Difficile
            self.delta_mult = (1.5, 2.0)  
            self.batt_mult = 3.5          

        print(f"\n--- Generazione Istanza: {self.difficulty.upper()} ---")
        print(f"   -> Nodi: {self.n_nodes} | Target: {self.n_targets} | Densità: {self.density:.2f}")

    # ==================================================
    # PIPELINE DI GENERAZIONE
    # ==================================================
    def generate(self):
        self._generate_nodes()            
        self._compute_distances()         
        self._generate_connected_graph()  
        self._generate_targets_feasible() 
        self._compute_coverage()          
        self._generate_target_parameters() 
        self._generate_global_parameters() 
        self._sanity_check()              
        print("✓ Istanza generata con successo!")
        return self.instance

    def _generate_nodes(self):
        self.instance["nodes"] = [
            {"id": i, "x": random.randint(0, 100), "y": random.randint(0, 100)}
            for i in range(self.n_nodes)
        ]

    def _compute_distances(self):
        nodes = self.instance["nodes"]
        self.dist = [[0.0]*self.n_nodes for _ in range(self.n_nodes)]
        for i in range(self.n_nodes):
            for j in range(self.n_nodes):
                dx = nodes[i]["x"] - nodes[j]["x"]
                dy = nodes[i]["y"] - nodes[j]["y"]
                self.dist[i][j] = math.hypot(dx, dy)

    def _generate_connected_graph(self):
        edges_undirected = set()
        nodes_list = list(range(self.n_nodes))
        random.shuffle(nodes_list)

        # Spanning tree
        for i in range(1, self.n_nodes):
            u = nodes_list[i]
            v = random.choice(nodes_list[:i])
            edges_undirected.add((min(u, v), max(u, v)))

        # Archi extra
        max_possible_edges = self.n_nodes * (self.n_nodes - 1) // 2
        desired_edges = int(self.density * max_possible_edges)
        
        all_pairs = [(i, j) for i in range(self.n_nodes) for j in range(i + 1, self.n_nodes)
                 if (i, j) not in edges_undirected]
        
        extra_edges_needed = max(0, desired_edges - len(edges_undirected))
        
        if all_pairs:
            for e in random.sample(all_pairs, min(extra_edges_needed, len(all_pairs))):
                edges_undirected.add(e)

        E = []
        t_ij = {}
        for i, j in edges_undirected:
            time = self.dist[i][j] / self.drone_speed 
            E.append((i, j)); E.append((j, i))
            t_ij[f"{i},{j}"] = time; t_ij[f"{j},{i}"] = time

        self.instance["edges_undirected"] = list(edges_undirected)
        self.instance["E"] = E
        self.instance["t_ij"] = t_ij

    def _generate_targets_feasible(self):
        targets = []
        attempts = 0
        while len(targets) < self.n_targets:
            attempts += 1
            if attempts > 20000: raise RuntimeError("Spazio troppo rado per inserire target validi.")
            x, y = random.randint(0, 100), random.randint(0, 100)
            
            feasible = False
            for node in self.instance["nodes"]:
                for lvl in self.sensing_levels.values():
                    if math.hypot(node["x"] - x, node["y"] - y) <= lvl["radius"]:
                        feasible = True
                        break
                if feasible: break

            if feasible:
                targets.append({"id": len(targets), "x": x, "y": y})
        self.instance["targets"] = targets

    def _compute_coverage(self):
        coverage = []
        for node in self.instance["nodes"]:
            node_cov = {"node_id": node["id"], "levels": []}
            for lvl, data in self.sensing_levels.items():
                targets_in_range = [
                    t["id"] for t in self.instance["targets"]
                    if math.hypot(node["x"] - t["x"], node["y"] - t["y"]) <= data["radius"]
                ]
                node_cov["levels"].append({
                    "level": lvl, "radius": data["radius"], "targets": targets_in_range
                })
            coverage.append(node_cov)
        self.instance["coverage"] = coverage

    def _estimate_cycle_time(self):
        visited = {0}
        total = 0
        while len(visited) < self.n_nodes:
            min_edge = float("inf")
            next_node = None
            for i in visited:
                for j in range(self.n_nodes):
                    if j not in visited and self.dist[i][j] < min_edge:
                        min_edge = self.dist[i][j]
                        next_node = j
            total += min_edge
            visited.add(next_node)
        return 2 * total / self.drone_speed

    def _generate_target_parameters(self):
        cycle_time = self._estimate_cycle_time()
        min_mult, max_mult = self.delta_mult
        delta_min = int(min_mult * cycle_time)
        delta_max = int(max_mult * cycle_time)
        delta_min = max(15, delta_min) 
        delta_max = max(25, delta_max)

        self.instance["target_parameters"] = {
            t["id"]: {"max_uncovered_time": random.randint(delta_min, delta_max)}
            for t in self.instance["targets"]
        }

    def _generate_global_parameters(self):
        cycle_time = self._estimate_cycle_time()
        battery_time = self.batt_mult * cycle_time
        
        self.instance["global_parameters"] = {
            "battery_time": battery_time,
            "drone_speed": self.drone_speed,
            "sensing_levels": self.sensing_levels
        }

    def _sanity_check(self):
        cycle_time = self._estimate_cycle_time()
        min_delta = min(p["max_uncovered_time"] for p in self.instance["target_parameters"].values())
        print(f"  -> Info: Tempo di ronda stimato: {cycle_time:.1f}m")
        print(f"  -> Info: Scadenza target più critica: {min_delta}m")

    def save(self, filename):
        with open(filename, "w") as f:
            json.dump(self.instance, f, indent=2)

    def visualize(self, save_filename="instance_plot.png"):
        nodes = self.instance["nodes"]
        edges = self.instance["edges_undirected"]
        targets = self.instance["targets"]

        plt.figure(figsize=(12,12)) 
        for i,j in edges:
            plt.plot([nodes[i]["x"], nodes[j]["x"]], [nodes[i]["y"], nodes[j]["y"]], color="gray", alpha=0.5, zorder=1)
        
        colors = {1: "green", 2: "orange", 3: "purple"}
        for node in nodes:
            for lvl, data in self.sensing_levels.items():
                circle = plt.Circle((node["x"], node["y"]), data["radius"], color=colors[lvl], fill=False, linestyle='--', alpha=0.15, zorder=2)
                plt.gca().add_patch(circle)

        for n in nodes:
            if n["id"] == 0:
                plt.scatter(n["x"], n["y"], c="#FFD700", s=250, zorder=10, edgecolors='black', linewidth=2)
                plt.text(n["x"]+1.8, n["y"]+1.8, f"START\n(N{n['id']})", fontsize=10, color="#8B6508", fontweight='bold', zorder=11,
                         bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
            else:
                plt.scatter(n["x"], n["y"], c="blue", s=100, zorder=5, edgecolors='white')
                plt.text(n["x"]+1.5, n["y"]+1.5, f"N{n['id']}", fontsize=10, color="blue", fontweight='bold', zorder=6)

        for t in targets:
            plt.scatter(t["x"], t["y"], c="red", marker="^", s=80, zorder=6, edgecolors='black')
            plt.text(t["x"]+1.5, t["y"]+1.5, f"T{t['id']}", fontsize=9, color="red", zorder=7)
        
        legend_start = mlines.Line2D([], [], color='#FFD700', marker='o', linestyle='None',
                                    markersize=12, markeredgecolor='black', markeredgewidth=2, label='Partenza (N0)')
        legend_node = mlines.Line2D([], [], color='blue', marker='o', linestyle='None',
                                    markersize=10, label='Nodo Standard')
        legend_target = mlines.Line2D([], [], color='red', marker='^', linestyle='None',
                                      markersize=10, label='Target')
        legend_edge = mlines.Line2D([], [], color='gray', linestyle='-', linewidth=1.5, label='Arco')

        plt.legend(handles=[legend_start, legend_node, legend_target, legend_edge], loc='upper right', fontsize=9, shadow=True)
        plt.title(f"Istanza {self.difficulty.capitalize()} ({self.n_nodes} Nodi, {self.n_targets} Target, {self.density:.2f} Densità)")
        plt.xlabel("X (unità x 100m)")
        plt.ylabel("Y (unità x 100m)")
        plt.axis("equal")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_filename, dpi=300)
        print(f"✓ Grafico salvato in {save_filename}")
        plt.show()

# =============================================================================
# ESECUZIONE INTERATTIVA
# =============================================================================
if __name__ == "__main__":
    print("\n=== GENERATORE ISTANZE DRONE ===")
    print("Scegli la difficoltà:")
    print("1 - Facile")
    print("2 - Difficile")
    
    scelta_diff = input("Inserisci 1 o 2 (default: Difficile): ").strip()
    
    # Mappatura: 1 -> facile, 2 -> difficile
    if scelta_diff == "1":
        diff = "facile"
    else:
        diff = "difficile"
    
    # Recupera i suggerimenti per la difficoltà scelta
    sugg = SUGGESTIONS[diff]
    
    print(f"\n--- Configurazione per Difficoltà: {diff.upper()} ---")
    print(f"Descrizione: {sugg['desc']}")
    print(f"Suggerimenti -> Nodi: {sugg['nodes']}, Target: {sugg['targets']}, Densità: {sugg['density']}")
    print("(Premi INVIO per usare un valore casuale nel range suggerito, oppure inserisci un numero)")

    # --- INPUT UTENTE CON DEFAULT ---
    def get_input(prompt, default_range, is_float=False):
        val = input(f"{prompt} [Suggerito {default_range}]: ").strip()
        if not val:
            return None # Lascia che la classe scelga random nel range
        try:
            return float(val) if is_float else int(val)
        except ValueError:
            print("Valore non valido, uso il default casuale.")
            return None

    # Chiede i parametri all'utente (opzionali)
    u_nodes = get_input("Numero di Nodi?", sugg['nodes'])
    u_targets = get_input("Numero di Target?", sugg['targets'])
    u_density = get_input("Densità Archi (0.0 - 1.0)?", sugg['density'], is_float=True)

    # --- GENERAZIONE ---
    gen = InstanceGenerator(difficulty=diff, n_nodes=u_nodes, n_targets=u_targets, density=u_density)
    gen.generate()
    
    gen.save("instance.json")
    gen.visualize("instance_plot.png")