package model.tree;

import model.tree.linked.LinkedTreeNodeFactory;

public class CoxRossRubinsteinTreeNodeFactory extends LinkedTreeNodeFactory<CoxRossRubinsteinTreeNode> {
	
	@Override
	public CoxRossRubinsteinTreeNode getNode() {
		return new CoxRossRubinsteinTreeNode();
	}
	
}