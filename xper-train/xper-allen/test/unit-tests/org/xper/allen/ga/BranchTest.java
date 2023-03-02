package org.xper.allen.ga;

import org.junit.Before;
import org.junit.Test;

import java.util.LinkedList;
import java.util.List;
import java.util.function.Consumer;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class BranchTest {

    private Branch<Long> founder;

    @Before
    public void setUp() throws Exception {
        founder = new Branch<>(1L);
    }

    @Test
    public void addsChildToCurrentBranch(){
        Branch<Long> child = new Branch<>(2L);
        founder.addChild(child);

        System.out.println(founder);
        assertTrue(founder.getChildren().contains(child));
    }

    @Test
    public void addsChildToSpecifiedBranch(){
        Branch<Long> child1 = new Branch<>(2L);
        Branch<Long> child2 = new Branch<>(3L);
        founder.addChild(child1);
        founder.addChild(child2);

        Branch<Long> testBranch = new Branch<>(4L);
        founder.addChildTo(2L, testBranch);

        System.out.println(founder);
        assertTrue(child1.getChildren().contains(testBranch));
        assertTrue(child2.getChildren().isEmpty());
    }

    @Test
    public void can_parse_tree(){
        Branch<Long> child1 = new Branch<>(2L);
        Branch<Long> child2 = new Branch<>(3L);
        founder.addChild(child1);
        founder.addChild(child2);

        Branch<Long> testBranch = new Branch<>(4L);
        founder.addChildTo(2L, testBranch);
        List<Long> childrenIds = new LinkedList<>();
        founder.forEach(new Consumer<Branch<Long>>() {
            @Override
            public void accept(Branch<Long> branch) {
                System.out.println(branch.getIdentifier());
                childrenIds.add(branch.getIdentifier());
            }
        });

        assertTrue(childrenIds.contains(1L));
        assertTrue(childrenIds.contains(2L));
        assertTrue(childrenIds.contains(3L));
        assertTrue(childrenIds.contains(4L));
    }

    @Test
    public void to_xml_and_back(){
        Branch<Long> child1 = new Branch<>(2L);
        Branch<Long> child2 = new Branch<>(3L);
        founder.addChild(child1);
        founder.addChild(child2);
        Branch<Long> child3 = new Branch<>(4L);
        founder.addChildTo(2L, child3);

        String xml = founder.toXml();
        System.out.println(xml);
        Branch fromXML = Branch.fromXml(xml);
        System.out.println(fromXML);

        assertEquals(founder, fromXML);
    }


}