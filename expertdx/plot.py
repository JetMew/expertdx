import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from expertdx.diagnostics import DiagnosticState


color_map = {
    'unknown': 'skyblue',
    'normal': 'lightgray',
    'minor': 'salmon',
    'major': 'salmon',
    'critical': 'salmon',
    'fixed': 'green'
}


def plot_causal_graph(causal_graph: DiagnosticState, file_path, select_name=None):
    nodes = causal_graph.diagnostic_items
    edges = causal_graph.causal_relationships

    fig, ax = plt.subplots(figsize=(6, 2))
    G = nx.DiGraph()

    for node in nodes:
        G.add_node(node.name, **node.to_dict(add_fixed=True))

    for edge in edges:
        cause_name = edge["cause"]
        effect_name = edge["effect"]
        if cause_name not in G.nodes:
            print(f"invalid cause_name: {cause_name}")
        if effect_name not in G.nodes:
            print(f"invalid effect_name: {effect_name}")
        G.add_edge(cause_name, effect_name, **edge)

    pos = nx.circular_layout(G)
    colors = []
    for node, data in G.nodes(data=True):
        if data['fixed'] is True:
            colors.append(color_map['fixed'])
        else:
            colors.append(color_map[data['severity']])
    labels = {node: f"{data['name']}\n({data['product']})" for node, data in G.nodes(data=True)}

    special_nodes = list()
    special_indexes = list()

    if select_name is not None:
        if isinstance(select_name, str):
            select_names = [select_name, ]
        elif isinstance(select_name, list):
            select_names = select_name
        else:
            raise ValueError
        for select_name in select_names:
            special_index = next((i for i, x in enumerate(G.nodes(data=True)) if x[1]['name'] == select_name), -1)
            special_node = list(G.nodes())[special_index]

            special_nodes.append(special_node)
            special_indexes.append(special_index)

    for u, v in G.edges():
        start = pos[u]
        end = pos[v]
        ax = plt.gca()
        arrow = FancyArrowPatch(start, end, arrowstyle='->',
                                mutation_scale=5,
                                shrinkA=16,
                                shrinkB=15,
                                connectionstyle="arc3,rad=0.05",
                                )
        ax.add_patch(arrow)

    nx.draw_networkx_nodes(G, pos, nodelist=[node for i, node in enumerate(G.nodes()) if i not in special_indexes],
                           node_color=[color for i, color in enumerate(colors) if i not in special_indexes], alpha=0.3,
                           node_size=1000)

    if special_nodes:
        nx.draw_networkx_nodes(G, pos, nodelist=special_nodes, node_color=[colors[i] for i in special_indexes],
                               alpha=.75, node_size=1000)

    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, font_family="SimHei")

    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    ax.set_xlim(x_min - 0.1 * (x_max - x_min), x_max + 0.1 * (x_max - x_min))
    ax.set_ylim(y_min - 0.1 * (y_max - y_min), y_max + 0.1 * (y_max - y_min))

    title = plt.title(file_path.split('/')[-1].split('.')[0].replace('_', ": ").upper(), fontsize=10)
    title.set_position((.5, 1.05))
    fig.subplots_adjust(top=0.9)

    plt.savefig(file_path, format='png', dpi=300, bbox_inches='tight')
