package org.xper.allen.intan.stimulation;

import java.util.*;

/**
 * Parses an EStim parameter string into a map of parameter names to parsed values.
 *
 * Grammar:
 *   - Parameters separated by ". "
 *   - Each parameter: key=value
 *   - Value types:
 *     - Bare value:  100, NegativeFirst              -> String
 *     - Tuple:       (3.5,3.5)                       -> ParsedTuple
 *     - List:        ["A025","A030"]                  -> ParsedList
 *     - Split:       {(3.5,3.5);(5,5)}               -> ParsedSplit containing ParsedTuples
 *                    {NegativeFirst;PositiveFirst}    -> ParsedSplit containing Strings
 *                    {50;100}                         -> ParsedSplit containing Strings
 *
 * Example: channels=["A025","A030"]. a={(3.5,3.5);(5,5)}. pol=NegativeFirst
 */
public class EStimParamParser {

    public Map<String, Object> parse(String input) {
        Map<String, Object> result = new LinkedHashMap<String, Object>();

        String[] assignments = input.split("\\. ");
        for (String assignment : assignments) {
            assignment = assignment.trim();
            if (assignment.isEmpty()) {
                continue;
            }

            int eqIndex = assignment.indexOf('=');
            if (eqIndex < 0) {
                throw new IllegalArgumentException("Invalid assignment (no '='): " + assignment);
            }

            String key = assignment.substring(0, eqIndex).trim();
            String rawValue = assignment.substring(eqIndex + 1).trim();

            result.put(key, parseValue(rawValue));
        }

        return result;
    }

    private Object parseValue(String rawValue) {
        if (rawValue.startsWith("{") && rawValue.endsWith("}")) {
            return parseSplit(rawValue);
        } else if (rawValue.startsWith("(") && rawValue.endsWith(")")) {
            return parseTuple(rawValue);
        } else if (rawValue.startsWith("[") && rawValue.endsWith("]")) {
            return parseList(rawValue);
        } else {
            return rawValue;
        }
    }

    private ParsedSplit parseSplit(String rawValue) {
        String inner = rawValue.substring(1, rawValue.length() - 1);
        List<String> parts = splitOnSemicolons(inner);
        List<Object> values = new ArrayList<Object>();
        for (String part : parts) {
            String trimmed = part.trim();
            values.add(parseValue(trimmed));
        }
        return new ParsedSplit(values);
    }

    private ParsedTuple parseTuple(String rawValue) {
        String inner = rawValue.substring(1, rawValue.length() - 1);
        List<String> values = splitAndTrim(inner);
        return new ParsedTuple(values);
    }

    private ParsedList parseList(String rawValue) {
        String inner = rawValue.substring(1, rawValue.length() - 1);
        List<String> values = new ArrayList<String>();
        for (String item : splitAndTrim(inner)) {
            values.add(item.replace("\"", ""));
        }
        return new ParsedList(values);
    }

    /**
     * Splits on semicolons, but only at the top level (not inside brackets or parens).
     */
    private List<String> splitOnSemicolons(String input) {
        List<String> parts = new ArrayList<String>();
        int depth = 0;
        int start = 0;
        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);
            if (c == '(' || c == '[') {
                depth++;
            } else if (c == ')' || c == ']') {
                depth--;
            } else if (c == ';' && depth == 0) {
                parts.add(input.substring(start, i));
                start = i + 1;
            }
        }
        parts.add(input.substring(start));
        return parts;
    }

    private List<String> splitAndTrim(String csv) {
        List<String> result = new ArrayList<String>();
        for (String part : csv.split(",")) {
            String trimmed = part.trim();
            if (!trimmed.isEmpty()) {
                result.add(trimmed);
            }
        }
        return result;
    }
}