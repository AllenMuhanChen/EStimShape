function [xs_left, ys_left, xs_right, ys_right] = Parse_behmsgeye(trialInit_tstamp, trialStop_tstamp)
%Given an input of two tstamps, will find targetOn and targetOff and parse
%out the x-y eye data from each eye between targetOn and targetOff. 
global conn;
%% Get tstamp of "TargetOff"/"TargetOn" between inputs
targetOn_tstamp = TStampBetween(trialInit_tstamp, trialStop_tstamp, "TargetOff");
targetOff_tstamp = TStampBetween(trialInit_tstamp, trialStop_tstamp, "TargetOn");
%% Read begmsgeye between TargetOn and TargetOff
disp("Starting MySQL Query")
sqlQuery = "SELECT msg FROM behmsgeye WHERE tstamp<"+num2str(targetOn_tstamp)+" AND tstamp>"+num2str(targetOff_tstamp);
behmsgeye_msgs = fetch(conn,sqlQuery);
disp("Finished MySQL Query")

%% parse behmsgeye.msg xml
%initialize storage vars
disp("Starting behmsgeye.msg xml parsing")
numMsgs = height(behmsgeye_msgs);
timeStamps = zeros(1,numMsgs);
ids = cell(1,numMsgs);
xs = zeros(1,numMsgs);
ys = zeros(1,numMsgs);

for i = 1:numMsgs
    %disp("parsing msg#: " + i)
    behmsgeye_msg = string(behmsgeye_msgs.msg(i));
    behmsgeye_msg_struct = ParseXML_behmsgeye(behmsgeye_msg);
    
    timeStamps(i) = behmsgeye_msg_struct.timestamp;
    ids{i} = behmsgeye_msg_struct.id;
    xs(i) = behmsgeye_msg_struct.degree(1);
    ys(i) = behmsgeye_msg_struct.degree(2);
  % commented code below is to be used with ParseXML().   
%     %timestamp
%     isTimeStamp = cellfun(@(x) strcmp(x,'timestamp'),{behmsgeye_msg_struct().Children.Name});
%     timeStamps(i) = str2double(behmsgeye_msg_struct.Children(isTimeStamp).Children.Data);
%     
%     %ids
%     isId = cellfun(@(x) strcmp(x,'id'),{behmsgeye_msg_struct().Children.Name});
%     ids{i} = behmsgeye_msg_struct.Children(isId).Children.Data;
%    
%     %x-y
%         %degree 
%     isDegree = cellfun(@(x) strcmp(x,'degree'),{behmsgeye_msg_struct().Children.Name});
%     degree_struct = behmsgeye_msg_struct.Children(isDegree);
%             %x
%     isX = cellfun(@(x) strcmp(x,'x'),{degree_struct.Children.Name});
%     xs(i) = str2double(degree_struct.Children(isX).Children.Data);
%             %y
%     isY = cellfun(@(x) strcmp(x,'y'),{degree_struct.Children.Name});
%     ys(i) = str2double(degree_struct.Children(isY).Children.Data);
%     
end
%% Separating left vs right eye data
isLeft = cellfun(@(x) strcmp(x,'leftIscan'),ids);
xs_left = xs(isLeft);
ys_left = ys(isLeft);
isRight = cellfun(@(x) strcmp(x,'rightIscan'),ids);
xs_right = xs(isRight);
ys_right = ys(isRight);
end