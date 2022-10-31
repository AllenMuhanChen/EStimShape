function mainScriptAllen
    clear all;
    close all;
    conn = getDbConnAllen;
    minute = (1/24/60);
    format long g
    startTime = posixtime(datetime('now','TimeZone','America/New_York') - 5*minute) * 1000000
    [tstamps,pos] = getTrialTstamps(conn,startTime);
    volt = cell(size(tstamps,1),1);
    r = []; l = []; t = []; b = []; c = [];
    sig = nan(size(tstamps,1),4);

    for ii=1:size(tstamps,1)-1
        volt{ii} = getVoltForTstampRange(conn,tstamps(ii,:));
        sig(ii,:) = mean(volt{ii});
        switch(find(pos(ii,:)))
            case 1; c = [c;sig(ii,:)]; %#ok<*AGROW>
            case 2; r = [r;sig(ii,:)];
            case 3; l = [l;sig(ii,:)];
            case 4; t = [t;sig(ii,:)];
            case 5; b = [b;sig(ii,:)];
        end
    end

    figure('pos',[400,1078,1073,420],'color','k');
    plotEyeCoords(c,l,r,t,b,'left',subplot(121)); 
    plotEyeCoords(c,l,r,t,b,'right',subplot(122));

%     save(['cal/gizmo_' num2str(getPosixTimeNow) '.mat'],'c','l','r','t','b')
% 
%     databaseName = 'ram_180616_3dma';
%     serverAddress = '172.30.6.27';
%     conn3d = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);
%     setdbprefs('DataReturnFormat','cellarray');
%     eyeData = fetch(conn,'SELECT a.name,arr_ind,a.tstamp,val FROM SystemVar a INNER JOIN (SELECT name, MAX(tstamp) tstamp FROM SystemVar GROUP BY name) b ON a.tstamp = b.tstamp AND a.name = b.name WHERE b.name=''xper_right_iscan_mapping_algorithm_parameter'' OR b.name=''xper_left_iscan_mapping_algorithm_parameter'' OR b.name=''xper_right_iscan_eye_zero'' OR b.name=''xper_left_iscan_eye_zero''');
%     try
%         insertIntoSqlTable(eyeData,{'name','arr_ind','tstamp','val'},'SystemVar',conn3d);
%         disp('Inserted eye coordinates in 3D database.');
%     catch
%         disp('Eye coordinates already exist in 3D database.');
%     end
% 
%     exec(conn,'TRUNCATE behmsg');
%     exec(conn,'TRUNCATE behmsgeye');
%     close(conn);
%     close(conn3d);
%     
%     screen2png(['cal/gizmo_' num2str(getPosixTimeNow) '.png'])
end

% if input('Accept left iscan estimates? (1/0): ')
%     insertEyeParams(c,r,l,t,b,'left',conn)
% end
% if input('Accept right iscan estimates? (1/0): ')
%     insertEyeParams(c,r,l,t,b,'right',conn)
% end

% filename = cellstr(datetime('now','format','yyMMdd_HHmm'));
% save(['testdata/eyeCalib_' filename{1} '.mat'],'c','r','l','t','b');
