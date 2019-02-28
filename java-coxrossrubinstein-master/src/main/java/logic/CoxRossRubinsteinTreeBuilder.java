package logic;

import model.tree.CoxRossRubinsteinTree;
import model.tree.CoxRossRubinsteinTreeNode;

public class CoxRossRubinsteinTreeBuilder extends
		TreeBuilder<CoxRossRubinsteinTree, CoxRossRubinsteinTreeNode> {

	public CoxRossRubinsteinTreeBuilder(double volatility, double timeStepLength,
			double interestRate) {
		tree = new CoxRossRubinsteinTree(volatility, timeStepLength, interestRate);
	}

}