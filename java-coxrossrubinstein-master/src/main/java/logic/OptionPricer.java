package logic;

import logic.enums.OptionStyle;
import logic.enums.OptionType;
import model.tree.CoxRossRubinsteinTree;
import model.tree.CoxRossRubinsteinTreeNode;
import algorithms.dfs.TreeDFS;

public class OptionPricer extends TreeDFS<CoxRossRubinsteinTree, CoxRossRubinsteinTreeNode> {

	private OptionType optionType;
	private OptionStyle optionStyle;
	private double strike;
	private double initialUnderlyingPrice;

	private CoxRossRubinsteinTree tree;

	public OptionPricer(final OptionType optionType,
			final OptionStyle optionStyle, final double strike,
			final double initialUnderlyingPrice, double volatility,
			double timeStepLength, double interestRate, int timeSteps) {
		super();

		this.initialUnderlyingPrice = initialUnderlyingPrice;
		this.optionType = optionType;
		this.optionStyle = optionStyle;
		this.strike = strike;

		CoxRossRubinsteinTreeBuilder ctb = new CoxRossRubinsteinTreeBuilder(volatility,
				timeStepLength, interestRate);
		try {
			ctb.createTree(timeSteps);
		} catch (IllegalAccessException e) {
			e.printStackTrace();
		}

		tree = ctb.getTree();
		tree.getCurrentNode().setUnderlyingPrice(initialUnderlyingPrice);
	}

	public double price() {

		// First calculate all intrinsic values
		dfs(tree, new CoxRossRubinsteinTreeSearchAction() {

			public CoxRossRubinsteinTreeNode perform(CoxRossRubinsteinTreeNode node) {
				node.setProbability(calcPropability(node));
				node.setUnderlyingPrice(calcUnderlyingPrice(node));
				node.setIntrinsicValue(calcIntrinsicValue(node));
				return node;
			}

			public double calcPropability(final CoxRossRubinsteinTreeNode node) {
				double prob;

				if (node.getParentNode() == null) {
					prob = 1;
				} else {
					prob = node.getParentNode().getProbability();

					switch (node.getPathType()) {
					case UP:
						prob = prob * tree.getP();
						break;
					case DOWN:
						prob = prob * tree.getQ();
						break;
					}
				}

				return prob;
			}

			public double calcUnderlyingPrice(final CoxRossRubinsteinTreeNode node) {
				double underlyingPrice;

				if (node.getParentNode() == null) {
					underlyingPrice = initialUnderlyingPrice;
				} else {
					underlyingPrice = node.getParentNode().getUnderlyingPrice();

					switch (node.getPathType()) {
					case UP:
						underlyingPrice = underlyingPrice * tree.getUp();
						break;
					case DOWN:
						underlyingPrice = underlyingPrice * tree.getDown();
						break;
					}
				}

				return underlyingPrice;
			}

			public double calcIntrinsicValue(final CoxRossRubinsteinTreeNode node) {
				double tmp = 0;
				switch (optionType) {
				case PUT:
					tmp = strike - node.getUnderlyingPrice();
					break;
				case CALL:
					tmp = node.getUnderlyingPrice() - strike;
					break;
				}
				return Math.max(0, tmp);
			}

		});

		// Calculate expected values and for American style options if it is feasible to exercise early
		dfsPostOrder(tree, new CoxRossRubinsteinTreeSearchAction() {

			public CoxRossRubinsteinTreeNode perform(CoxRossRubinsteinTreeNode node) {
				node.setExpectedValue(calcExpectedValue(node));
				node.setValue(calcValue(node));
				return node;
			}

			public double calcExpectedValue(final CoxRossRubinsteinTreeNode node) {
				if (node.isLeaf())
					return 0;

				if (node.getLeftNode().isLeaf())
					return (tree.getQ()
							* node.getLeftNode().getIntrinsicValue() + tree
							.getP() * node.getRightNode().getIntrinsicValue())
							/ (1 + tree.getInterestRatePerTimeStep());

				return (tree.getQ() * node.getLeftNode().getValue() + tree
						.getP() * node.getRightNode().getValue())
						/ (1 + tree.getInterestRatePerTimeStep());
			}

			public double calcValue(final CoxRossRubinsteinTreeNode node) {
				if (node.isLeaf())
					return 0;

				double tmp = 0;

				if (node.hasSuccessor())
					switch (optionStyle) {
					case AMERICAN:
						tmp = Math.max(node.getExpectedValue(),
								node.getIntrinsicValue());
						break;
					case EUROPEAN:
						tmp = node.getExpectedValue();
						break;
					}

				return tmp;
			}

		});

		tree.moveToRoot();
		return tree.getCurrentNode().getExpectedValue();
	}
}