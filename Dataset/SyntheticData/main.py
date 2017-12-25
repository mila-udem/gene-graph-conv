import os
import sys
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import random
from collections import deque
from tqdm import tqdm
import argparse
import h5py

def f(p):
	return np.random.binomial(1, p)

def sq2d_lattice_graph(x_size, y_size, value_fn):
	G = nx.Graph()
	#adding nodes
	for i in xrange(x_size):
		for j in xrange(y_size):
			val = value_fn()
			G.add_node((i,j), value=val)
			
	#adding edges
	for node in G.nodes():
		if node[0]>0:
			G.add_edge((node[0]-1, node[1]), node)
		if node[0]<(x_size-1):
			G.add_edge((node[0]+1, node[1]), node)
		if node[1]>0:
			G.add_edge((node[0], node[1]-1), node)
		if node[1]<(y_size-1):
			G.add_edge((node[0], node[1]+1), node)
	return G


def if_percolates(G, x_size):
	T = G.copy()
	for data_node in G.nodes.data():
		if data_node[1]['value'] == 0:
			T.remove_node(data_node[0])
		else:
			pass
	
	source = []
	ground = []
	M = T.copy()
	
	for node in T.nodes():
		if node[0] == 0:
			new_node = (-1, node[1])
			M.add_node(new_node, value = 2)
			M.add_edge(new_node, node)
			ground.append(new_node)
		if node[0] == (x_size-1):
			new_node = (x_size, node[1])
			M.add_node(new_node, value = 2)
			M.add_edge(new_node, node)
			source.append(new_node)
	
	if len(source)==0 or len(ground)==0:
		return M, False, None
	
	# detect path
	for s_node in ground:
		for u, v in nx.dfs_edges(M, s_node):
			if v in source:
				return M, True, nx.shortest_path(M, s_node, v)
	
	return M, False, None


def sq2d_lattice_percolation(size_x=10, size_y=10, prob=0.5):
	def fp(): return f(prob)
	
	#Generating square lattice graph
	G = sq2d_lattice_graph(size_x,size_y, fp)
	#Getting density of open nodes
	vals = dict(nx.get_node_attributes(G, 'value'))
	num_on = np.sum( list(vals.values()) )
	num_total = len(list(vals.values()))
	density = float(num_on)/float(num_total)
	#Checking percolation
	T, perc, path = if_percolates(G, 10)
	

	#correcting density
	if not path is None:
		for node in G.nodes:
			if density<0.5:
				break
			if G.nodes[node]['value'] == 1 and (not node in path):
				G.nodes[node]['value'] = 0
				num_on -= 1
				density = float(num_on)/float(num_total)
	else:
		for node in G.nodes:
			if density<0.5:
				break
			if G.nodes[node]['value'] == 1:
				G.nodes[node]['value'] = 0
				num_on -= 1
				density = float(num_on)/float(num_total)
	
	return G, T, perc, density

def sq2d_plot_graph(G):
	positionsG = {}
	for node in G.nodes():
		positionsG[node] = np.array([node[0],node[1]], dtype='float32')
	
	labelsG = dict(nx.get_node_attributes(G, 'value'))
	optionsG = {
		'node_size': 100,
		'width': 3,
		'with_labels':False
	}
	nx.draw_networkx(G, pos = positionsG, nodelist=list(labelsG.keys()), node_color=list(labelsG.values()), **optionsG)

if __name__=='__main__':

	parser = argparse.ArgumentParser(description='Percolation dataset')
	parser.add_argument('--dataset', help='Dataset filename')
	parser.add_argument('--test', type=int, help='Generate example')
	parser.add_argument('--N', type=int, default = 100, help='Number of examples')
	parser.add_argument('--size_x', type=int, default = 10, help='X dim size')
	parser.add_argument('--size_y', type=int, default = 10, help='Y dim size')
	parser.add_argument('--prob', type=float, default = 0.562, help='On/off probability')
	
	
	args = parser.parse_args()

	if not args.test is None:
		if args.dataset is None:
			G, T, perc, dens = sq2d_lattice_percolation(size_x=10, size_y=10, prob = 0.562)
			print 'Percolation = ', perc, 'Density = ', dens
			
			plt.subplot(121)
			sq2d_plot_graph(G)
			
			plt.subplot(122)
			sq2d_plot_graph(T)
			plt.show()
		else:
			fmy = h5py.File(args.dataset,"r")

			mat = np.array(fmy["graph_data"])
			G = nx.from_numpy_matrix(mat)
			nodes_attr = {}
			for i,node in enumerate(G.nodes()):
				nodes_attr[node] = fmy["expression_data"][args.test][i]
			nx.set_node_attributes(G, nodes_attr, 'value')
			
			plt.figure()
			labelsG = dict(nx.get_node_attributes(G, 'value'))
			nx.draw_spectral(G, nodelist=list(labelsG.keys()), node_color=list(labelsG.values()))
			plt.show()

			print 'Label = ', fmy["labels_data"][args.test]

			fmy.close()
	

	if (not args.dataset is None) and (args.test is None):
		if os.path.exists(args.dataset):
			os.remove(args.dataset)
		#Moving data to hdf5
		fmy = h5py.File(args.dataset,"w")

		#generate graph
		G, T, perc, dens = sq2d_lattice_percolation( args.size_x, args.size_y, args.prob)
		node_list = list(G.nodes())
		M = len(node_list)
		mat = nx.adjacency_matrix(G, nodelist=node_list).todense()
		# mat = nx.to_numpy_matrix(nx.adjacency_matrix(G), weight=None)
		
		graph_data = fmy.create_dataset("graph_data", (M,M), dtype=np.dtype('float32'))
		for i in xrange(M):
			graph_data[i] = mat[i,:]

		expression_data = fmy.create_dataset("expression_data", (args.N,M), dtype=np.dtype('float32'))
		labels_data = fmy.create_dataset("labels_data", (args.N,), dtype=np.dtype('float32'))
		
		for i in tqdm(xrange(args.N)):

			if i%2 == 0: #generate positive example
				perc = False
				while perc == False:
					G, T, perc, dens = sq2d_lattice_percolation( args.size_x, args.size_y, args.prob)
				attrs = nx.get_node_attributes(G, 'value')
				features = np.zeros((M,), dtype='float32')
				for j,node in enumerate(node_list):
					features[j] = attrs[node]
				expression_data[i] = features
				labels_data[i] = 1

			else: #generate negative example
				perc = True
				while perc == True:
					G, T, perc, dens = sq2d_lattice_percolation( args.size_x, args.size_y, args.prob)
				attrs = nx.get_node_attributes(G, 'value')
				features = np.zeros((M,), dtype='float32')
				for j,node in enumerate(node_list):
					features[j] = attrs[node]
				expression_data[i] = features
				labels_data[i] = 0

		fmy.flush()
		fmy.close()