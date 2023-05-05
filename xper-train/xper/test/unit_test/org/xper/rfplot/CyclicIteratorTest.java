package org.xper.rfplot;

import org.junit.Test;
import org.xper.rfplot.gui.CyclicIterator;

import java.util.List;
import java.util.LinkedList;
import java.util.Set;

import static org.junit.Assert.assertEquals;

public class CyclicIteratorTest {
    @Test
    public void test_forwards(){
        List list = new LinkedList<>();
        list.add("1");
        list.add("2");
        list.add("3");

        CyclicIterator<String> iterator = new CyclicIterator(list);
        String first = iterator.first();
        String second = iterator.next();
        String third = iterator.next();
        String fourth = iterator.next();

        assertEquals(first, "1");
        assertEquals(second, "2");
        assertEquals(third, "3");
        assertEquals(fourth, "1");

    }
    @Test
    public void test_backwards(){
        List list = new LinkedList<>();
        list.add("1");
        list.add("2");
        list.add("3");

        CyclicIterator<String> iterator = new CyclicIterator(list);
        String first = iterator.first();
        String second = iterator.previous();
        String third = iterator.previous();
        String fourth = iterator.previous();

        assertEquals(first, "1");
        assertEquals(second, "3");
        assertEquals(third, "2");
        assertEquals(fourth, "1");

    }

}
