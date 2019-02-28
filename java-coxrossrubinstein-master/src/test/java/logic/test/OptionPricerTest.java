package logic.test;

import static org.junit.Assert.assertTrue;
import logic.OptionPricer;
import logic.enums.OptionStyle;
import logic.enums.OptionType;

import org.junit.Test;

public class OptionPricerTest {
	
	@Test
	public void testEuropeanCall1() {
		OptionPricer o = new OptionPricer(OptionType.CALL, OptionStyle.EUROPEAN, 165, 220, 0.98, 0.5, 0.21, 2);
		double price = o.price();
		double expected = 116.35;
		double tolerance = 0.1;
		
		assertTrue(expected - tolerance <= price && price <= expected + tolerance);
	}
	
	@Test
	public void testEuropeanCall2() {
		OptionPricer o = new OptionPricer(OptionType.CALL, OptionStyle.EUROPEAN, 165, 100, 0.98, 0.5, 0.21, 2);
		double price = o.price();
		double expected = 31.06;
		double tolerance = 0.1;
		
		assertTrue(expected - tolerance <= price && price <= expected + tolerance);
	}
	
	@Test
	public void testEuropeanPut1() {
		OptionPricer o = new OptionPricer(OptionType.PUT, OptionStyle.EUROPEAN, 165, 100, 0.98, 0.5, 0.21, 2);
		double price = o.price();
		double expected = 67.43;
		double tolerance = 0.1;
		
		assertTrue(expected - tolerance <= price && price <= expected + tolerance);
	}
	
	@Test
	public void testAmericanCall1() {
		OptionPricer o = new OptionPricer(OptionType.CALL, OptionStyle.AMERICAN, 150, 200, 0.98, 0.5, 0.21, 2);
		double price = o.price();
		double expected = 105.77;
		double tolerance = 0.1;
		
		assertTrue(expected - tolerance <= price && price <= expected + tolerance);
	}
	
	@Test
	public void testAmericanPut1() {
		OptionPricer o = new OptionPricer(OptionType.PUT, OptionStyle.AMERICAN, 150, 200, 0.98, 0.5, 0.21, 2);
		double price = o.price();
		double expected = 29.74;
		double tolerance = 0.1;
		
		assertTrue(expected - tolerance <= price && price <= expected + tolerance);
	}

}