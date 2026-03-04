package org.xper.allen.intan.stimulation;

import junit.framework.TestCase;

import java.util.Map;

public class EStimParamParserTest extends TestCase {

    private EStimParamParser parser;

    public void setUp() throws Exception {
        super.setUp();
        parser = new EStimParamParser();
    }

    public void testParseChannelsOnly() {
        Map<String, Object> result = parser.parse("channels=[\"A025\",\"A030\"]");

        assertTrue(result.get("channels") instanceof ParsedList);
        ParsedList channels = (ParsedList) result.get("channels");
        assertEquals(2, channels.size());
        assertEquals("A025", channels.get(0));
        assertEquals("A030", channels.get(1));
    }

    public void testParseBareValue() {
        Map<String, Object> result = parser.parse("dp=100");
        assertEquals("100", result.get("dp"));
    }

    public void testParseBareStringValue() {
        Map<String, Object> result = parser.parse("pol=NegativeFirst");
        assertEquals("NegativeFirst", result.get("pol"));
    }

    public void testParseTuple() {
        Map<String, Object> result = parser.parse("a=(3.5,3.5)");

        assertTrue(result.get("a") instanceof ParsedTuple);
        ParsedTuple tuple = (ParsedTuple) result.get("a");
        assertEquals(2, tuple.size());
        assertEquals("3.5", tuple.get(0));
        assertEquals("3.5", tuple.get(1));
    }

    public void testParseFullString() {
        String input = "channels=[\"A025\",\"A030\"]. a=(3.5,3.5). dp=100. pol=NegativeFirst";
        Map<String, Object> result = parser.parse(input);

        assertEquals(4, result.size());

        ParsedList channels = (ParsedList) result.get("channels");
        assertEquals(2, channels.size());

        ParsedTuple a = (ParsedTuple) result.get("a");
        assertEquals("3.5", a.get(0));

        assertEquals("100", result.get("dp"));
        assertEquals("NegativeFirst", result.get("pol"));
    }

    public void testParseSplitWithTuples() {
        Map<String, Object> result = parser.parse("a={(3.5,3.5);(5,5)}");

        assertTrue(result.get("a") instanceof ParsedSplit);
        ParsedSplit split = (ParsedSplit) result.get("a");
        assertEquals(2, split.size());

        ParsedTuple first = (ParsedTuple) split.get(0);
        assertEquals("3.5", first.get(0));
        assertEquals("3.5", first.get(1));

        ParsedTuple second = (ParsedTuple) split.get(1);
        assertEquals("5", second.get(0));
        assertEquals("5", second.get(1));
    }

    public void testParseSplitWithBareValues() {
        Map<String, Object> result = parser.parse("dp={50;100}");

        assertTrue(result.get("dp") instanceof ParsedSplit);
        ParsedSplit split = (ParsedSplit) result.get("dp");
        assertEquals(2, split.size());
        assertEquals("50", split.get(0));
        assertEquals("100", split.get(1));
    }

    public void testParseSplitWithStrings() {
        Map<String, Object> result = parser.parse("pol={NegativeFirst;PositiveFirst}");

        assertTrue(result.get("pol") instanceof ParsedSplit);
        ParsedSplit split = (ParsedSplit) result.get("pol");
        assertEquals(2, split.size());
        assertEquals("NegativeFirst", split.get(0));
        assertEquals("PositiveFirst", split.get(1));
    }

    public void testParseSplitWithLists() {
        Map<String, Object> result = parser.parse("channels={[\"A025\",\"A030\"];[\"A015\",\"A016\"]}");

        assertTrue(result.get("channels") instanceof ParsedSplit);
        ParsedSplit split = (ParsedSplit) result.get("channels");
        assertEquals(2, split.size());

        ParsedList first = (ParsedList) split.get(0);
        assertEquals("A025", first.get(0));
        assertEquals("A030", first.get(1));

        ParsedList second = (ParsedList) split.get(0);
        assertEquals("A025", second.get(0));
    }

    public void testParseMultipleSplits() {
        String input = "channels=[\"A025\",\"A030\"]. a={(3.5,3.5);(5,5)}. pol={NegativeFirst;PositiveFirst}";
        Map<String, Object> result = parser.parse(input);
        System.out.println(result);
        assertTrue(result.get("channels") instanceof ParsedList);
        assertTrue(result.get("a") instanceof ParsedSplit);
        assertTrue(result.get("pol") instanceof ParsedSplit);
    }

    public void testMissingEqualsThrows() {
        try {
            parser.parse("badparam");
            fail("Expected IllegalArgumentException");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }
}