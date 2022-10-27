function volt = getVoltForTstampRange(conn,tstamp)
    p.DataReturnFormat = 'structure';
    setdbprefs(p)

    scanId = 'leftIscan';
    whereclause = ['SELECT extractvalue(msg, ''/EyeDeviceMessage/volt/x'') as ''vx'', '...
                'extractvalue(msg, ''/EyeDeviceMessage/volt/y'') as ''vy'' '...
                'FROM BehMsgEye '...
                'WHERE extractvalue(msg, ''/EyeDeviceMessage/id'') = ''' scanId ''' '...
                'AND tstamp BETWEEN ' num2str(tstamp(1)) ' AND ' num2str(tstamp(2)) ];

    a1 = fetch(conn,whereclause);
    
    if isempty(a1)
        volt = nan(1,4); return;
    end
    volt(:,1) = str2double(a1.vx);
    volt(:,2) = str2double(a1.vy);
    
    scanId = 'rightIscan';
    whereclause = ['SELECT extractvalue(msg, ''/EyeDeviceMessage/volt/x'') as ''vx'', '...
                'extractvalue(msg, ''/EyeDeviceMessage/volt/y'') as ''vy'' '...
                'FROM BehMsgEye '...
                'WHERE extractvalue(msg, ''/EyeDeviceMessage/id'') = ''' scanId ''' '...
                'AND tstamp BETWEEN ' num2str(tstamp(1)) ' AND ' num2str(tstamp(2)) ];
            
    a2 = fetch(conn,whereclause);
    
    if size(a2.vx,1) > size(volt,1)
        a2(end,:) = [];
        %a2.vy(:,end) = [];
    elseif size(a2.vx,1) < size(volt,1)
        a2.vx{end+1} = nan;
        a2.vy{end+1} = nan;
    end
    volt(:,3) = str2double(a2.vx);
    volt(:,4) = str2double(a2.vy);
end

