function [x,y, targetEyeWindowSize, stimObjDataId] = Parse_TargetOn(tstamp)
%Given a single tstamp of a "TargetOn" event, will parse behmsg.msg for
%targetPos.x targetPos.y and targetEyeWindowSize. 
global conn;
%% Fetching data from database and converting to string
sqlQuery = "SELECT msg FROM behmsg WHERE tstamp=" + num2str(tstamp);
behmsg = fetch(conn,sqlQuery);
behmsg = table2array(behmsg); string(behmsg);

%% Parsing XML
behmsg_struct = parseXML(behmsg);

%targetPos
isTargetPos = cellfun(@(x) strcmp(x,'targetPos'), {behmsg_struct.Children.Name});
targetPos_struct = behmsg_struct.Children(isTargetPos);
    %x
isX = cellfun(@(x) strcmp(x,'x'),{targetPos_struct.Children.Name});
x = str2double(targetPos_struct.Children(isX).Children.Data);
    %y
isY = cellfun(@(x) strcmp(x,'y'),{targetPos_struct.Children.Name});
y = str2double(targetPos_struct.Children(isY).Children.Data);

%targetEyeWindowSize
isTargetEyeWindowSize = cellfun(@(x) strcmp(x,'targetEyeWindowSize'), {behmsg_struct.Children.Name});
targetEyeWindowSize = str2double(behmsg_struct.Children(isTargetEyeWindowSize).Children.Data);

%stimObjDataId
isStimObjDataId = cellfun(@(x) strcmp(x,'stimObjDataId'), {behmsg_struct.Children.Name});
stimObjDataId = str2double(behmsg_struct.Children(isStimObjDataId).Children.Data);
end

