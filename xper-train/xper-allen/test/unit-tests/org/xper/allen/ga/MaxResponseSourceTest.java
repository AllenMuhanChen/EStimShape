//package org.xper.allen.ga;
//
//import org.junit.Before;
//import org.junit.Test;
//import org.xper.allen.util.MultiGaDbUtil;
//
//import java.util.Arrays;
//import java.util.List;
//
//import static org.junit.Assert.assertEquals;
//
//public class MaxResponseSourceTest {
//
//    private MaxResponseSource maxResponseSource;
//
//    @Before
//    public void setUp() throws Exception {
//        maxResponseSource = new MaxResponseSource();
//
//        maxResponseSource.setMinimumMaxResponse(4.0);
//        maxResponseSource.setSpikeRateSource(new CanopyWidthSourceTest.CanopyWidthSourceTestSpikeRateSource());
//    }
//
//    @Test
//    public void returns_min_if_resp_under_min() throws Exception {
//        maxResponseSource.setDbUtil(new MockUnderMinDbUtil());
//
//        double maxResponse = maxResponseSource.getValue(null);
//
//        assertEquals(maxResponse, 4.0, .001);
//    }
//
//    @Test
//    public void returns_max_if_resp_over_min() throws Exception {
//        maxResponseSource.setDbUtil(new MockOverMinDbUtil());
//
//        double maxResponse = maxResponseSource.getValue(null);
//
//        assertEquals(maxResponse, 5.0, .001);
//    }
//
//    private static class MockUnderMinDbUtil extends MultiGaDbUtil {
//        @Override
//        public List<Long> readAllStimIdsForGa(String gaName) {
//            return Arrays.asList(1L, 2L, 3L);
//        }
//    }
//
//    private static class MockOverMinDbUtil extends MultiGaDbUtil {
//        @Override
//        public List<Long> readAllStimIdsForGa(String gaName) {
//            return Arrays.asList(1L, 2L, 5L);
//        }
//    }
//}