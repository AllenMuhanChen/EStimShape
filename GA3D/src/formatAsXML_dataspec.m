function returnXML = formatAsXML_dataspec(id)
    returnXML = ['<Data>' char(10) ...
        char(9) '<trialType>GA</trialType>' char(10) ...
        char(9) '<lineage>' num2str(id.linNum) '</lineage>' char(10) ...
        char(9) '<birthGen>' num2str(id.genNum) '</birthGen>' char(10) ...
        char(9) '<parentId>' formatAsXML_parentId(id.parentId) '</parentId>' char(10) ...
        char(9) '<stimObjId>' num2str(id.tstamp) '</stimObjId>' char(10) ...
        char(9) '<descriptiveId>' id.descId '</descriptiveId>' char(10) ...
        char(9) '<sampleFrequency>0.0</sampleFrequency>' char(10) ...
        char(9) '<taskDoneIds/>' char(10) ...
        char(9) '<trialStageData/>' char(10) ...
        char(9) '<spikesPerSec/>' char(10) ...
        char(9) '<avgFR>0.0</avgFR>' char(10) ...
        char(9) '<stdFR>0.0</stdFR>' char(10) ...
        '</Data>'];    
end

function xml = formatAsXML_parentId(parentId)
    if isempty(parentId)
        xml = '-1'; 
    elseif iscell(parentId)
        xml = [char(10) char(9) char(9) '<string>' parentId{1}{1} '</string>' char(10) ...
            char(9) char(9) '<string>' parentId{2}{1} '</string>' char(10) char(9)];
    else
        xml = [char(10) char(9) char(9) '<string>' parentId '</string>' char(10) char(9)];
    end
end