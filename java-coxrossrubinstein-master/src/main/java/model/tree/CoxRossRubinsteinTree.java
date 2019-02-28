package model.tree;

import logic.enums.PathType;
import model.tree.linked.LinkedTree;

public class CoxRossRubinsteinTree extends LinkedTree<CoxRossRubinsteinTree, CoxRossRubinsteinTreeNode> {

	private double volatility;
	private double interestRatePerTimeStep;

	private double timeStepLength;

	private double up;
	private double down;
	
	private double p;
	private double q;

	public CoxRossRubinsteinTree(double volatility, double timeStepLength,
			double interestRate) {
		super();

		this.volatility = volatility;
		this.timeStepLength = timeStepLength;
		this.interestRatePerTimeStep = Math.pow(1 + interestRate,
				timeStepLength) - 1;

		this.up = Math.exp(this.volatility * Math.sqrt(this.timeStepLength));
		this.down = 1 / up;

		this.p = (1 + interestRatePerTimeStep - down) / (up - down);
		this.q = 1 - p;
	}

	public boolean setLeftNode(CoxRossRubinsteinTreeNode node) {
		node.setPathType(PathType.DOWN);
		return super.setLeftNode(node);
	}

	public boolean setRightNode(CoxRossRubinsteinTreeNode node) {
		node.setPathType(PathType.UP);
		return super.setRightNode(node);
	}
	
	public double getUp() {
		return up;
	}

	public void setUp(double up) {
		this.up = up;
	}

	public double getDown() {
		return down;
	}

	public void setDown(double down) {
		this.down = down;
	}

	public double getP() {
		return p;
	}

	public void setP(double p) {
		this.p = p;
	}

	public double getQ() {
		return q;
	}

	public void setQ(double q) {
		this.q = q;
	}
	
	public double getInterestRatePerTimeStep() {
		return interestRatePerTimeStep;
	}
	
	@SuppressWarnings("unchecked")
	@Override
	public CoxRossRubinsteinTreeNodeFactory getFactory() {
		return new CoxRossRubinsteinTreeNodeFactory();
	}

}