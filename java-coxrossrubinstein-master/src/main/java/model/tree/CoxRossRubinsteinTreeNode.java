package model.tree;

import logic.enums.PathType;
import model.tree.linked.LinkedTreeNode;

public class CoxRossRubinsteinTreeNode extends LinkedTreeNode<CoxRossRubinsteinTreeNode> {

	private double underlyingPrice;
	private double expectedValue;
	private double intrinsicValue;
	private double value;
	private double probability;
	private PathType pathType;

	public CoxRossRubinsteinTreeNode() {
		super();
	}

	public double getUnderlyingPrice() {
		return underlyingPrice;
	}

	public void setUnderlyingPrice(double underlyingPrice) {
		this.underlyingPrice = underlyingPrice;
	}

	public double getExpectedValue() {
		return expectedValue;
	}

	public void setExpectedValue(double expectedValue) {
		this.expectedValue = expectedValue;
	}

	public double getIntrinsicValue() {
		return intrinsicValue;
	}

	public void setIntrinsicValue(double intrinsicValue) {
		this.intrinsicValue = intrinsicValue;
	}

	public double getValue() {
		return value;
	}

	public void setValue(double value) {
		this.value = value;
	}

	public double getProbability() {
		return probability;
	}

	public void setProbability(double probability) {
		this.probability = probability;
	}

	public PathType getPathType() {
		return pathType;
	}

	public void setPathType(PathType pathType) {
		this.pathType = pathType;
	}

	public boolean isLeaf() {
		if (getLeftNode() == null && getRightNode() == null)
			return true;
		else
			return false;
	}
	
	public boolean hasSuccessor() {
		return !isLeaf();
	}
	
	@Override
	public String toString() {
		StringBuffer sb = new StringBuffer();
		sb.append("node [ ");
		sb.append("underlying price: " + getUnderlyingPrice() + " | ");
		sb.append("expected value: " + getExpectedValue() + " | ");
		sb.append("intrinsic value: " + getIntrinsicValue() + " | ");
		sb.append("value: " + getValue() + " | ");
		sb.append("probability: " + getProbability() + " | ");
		sb.append("path type: " + getPathType() + " ");
		sb.append("]");
		return sb.toString();
	}

}