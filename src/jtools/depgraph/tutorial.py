# visual aspects to include:
# * bottom/top shifted
# * root/leaves top or bottom

# below is the networkx tutorial from
# https://networkx.org/documentation/stable/tutorial.html

import networkx as nx

g = nx.Graph()

g.add_node(1)
g.add_nodes_from([2, 3])

node_list = [(4, {"color": "red"}), (5, {"color": "green"})]
g.add_nodes_from(node_list)

h = nx.path_graph(10)
g.add_nodes_from(h)
g.add_node(h)

g.add_edge(1, 2)
edge = (2, 3)
g.add_edge(*edge)
edges_list = [(1, 2), (3, 4)]
g.add_edges_from(edges_list)
g.add_edges_from(h.edges)

g.clear()

g.add_edges_from([(1, 2), (1, 3)])
g.add_node(1)
g.add_edge(1, 2)
g.add_node("spam")
g.add_nodes_from("spam")
g.add_edge(3, "m")

print(g.number_of_nodes())
print(g.number_of_edges())
